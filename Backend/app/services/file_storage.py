"""Stockage local sécurisé des pièces d'admission.

Les octets ne sont jamais envoyés dans PostgreSQL. Le service écrit les fichiers
dans un dossier de runtime configurable sous le backend et retourne uniquement un
chemin relatif à persister dans la base.
"""

from __future__ import annotations

import os
import re
import tempfile
import uuid
from datetime import date
from pathlib import Path, PurePosixPath

from fastapi import UploadFile

from app.core.config import settings


CHUNK_SIZE = 1024 * 1024
_ALLOWED_EXTENSIONS = {
    ".pdf": {"application/pdf"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".webp": {"image/webp"},
    ".doc": {"application/msword"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    },
}
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


class StorageError(ValueError):
    """Erreur métier de stockage exposable à l'endpoint d'admission."""


def storage_root() -> Path:
    """Retourne la racine de stockage et la crée si nécessaire."""
    configured = Path(settings.ADMISSIONS_STORAGE_DIR)
    root = configured if configured.is_absolute() else Path(__file__).resolve().parents[2] / configured
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def safe_original_filename(filename: str | None) -> str:
    """Conserve un nom lisible sans jamais lui faire influence sur le chemin."""
    if not filename:
        raise StorageError("Le nom du fichier est obligatoire.")

    # Un nom client ne doit jamais fournir de séparateur de chemin.
    basename = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    basename = _SAFE_NAME_RE.sub("_", basename).strip("._")
    if not basename:
        raise StorageError("Le nom du fichier est invalide.")
    return basename[:255]


def _extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def _validate_content_type(filename: str, content_type: str | None) -> str:
    extension = _extension(filename)
    allowed_mimes = _ALLOWED_EXTENSIONS.get(extension)
    if not allowed_mimes:
        raise StorageError(
            "Type de fichier non autorisé. Formats acceptés : PDF, JPG, PNG, WEBP, DOC et DOCX."
        )

    normalized = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized not in allowed_mimes:
        raise StorageError("Le type MIME du fichier ne correspond pas à son extension.")
    return normalized


def _has_valid_signature(extension: str, prefix: bytes) -> bool:
    """Vérifie une signature minimale avant d'accepter le fichier."""
    if extension == ".pdf":
        return b"%PDF-" in prefix[:1024]
    if extension in {".jpg", ".jpeg"}:
        return prefix.startswith(b"\xff\xd8\xff")
    if extension == ".png":
        return prefix.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == ".webp":
        return len(prefix) >= 12 and prefix[:4] == b"RIFF" and prefix[8:12] == b"WEBP"
    if extension == ".doc":
        return prefix.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
    if extension == ".docx":
        return prefix.startswith(b"PK\x03\x04")
    return False


def _relative_destination(candidature_id: str, piece_id: str, extension: str) -> PurePosixPath:
    # Tous les segments sont générés par le serveur, jamais repris du client.
    return PurePosixPath(
        str(date.today().year),
        candidature_id,
        piece_id,
        f"{uuid.uuid4().hex}{extension}",
    )


def _resolve_stored_path(relative_path: str) -> Path:
    """Résout un chemin DB sous la racine, en rejetant toute traversée."""
    if not relative_path or "\\" in relative_path:
        raise StorageError("Chemin de stockage invalide.")

    relative = PurePosixPath(relative_path)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise StorageError("Chemin de stockage invalide.")

    root = storage_root()
    candidate = (root / Path(*relative.parts)).resolve()
    if not candidate.is_relative_to(root):
        raise StorageError("Chemin de stockage invalide.")
    return candidate


def resolve_stored_path(relative_path: str) -> Path:
    """API interne pour vérifier et résoudre un chemin de pièce."""
    return _resolve_stored_path(relative_path)


async def store_admission_upload(
    upload: UploadFile,
    *,
    candidature_id: str,
    piece_id: str,
) -> tuple[str, str, str, int]:
    """Stocke un upload et retourne chemin relatif, nom, MIME et taille.

    Le fichier est d'abord écrit dans un fichier temporaire puis renommé
    atomiquement. En cas d'erreur, aucun fichier partiel n'est laissé sur disque.
    """
    original_name = safe_original_filename(upload.filename)
    extension = _extension(original_name)
    mime_type = _validate_content_type(original_name, upload.content_type)
    root = storage_root()
    relative = _relative_destination(candidature_id, piece_id, extension)
    destination = _resolve_stored_path(relative.as_posix())
    destination.parent.mkdir(parents=True, exist_ok=True)

    temporary_path: Path | None = None
    total_size = 0
    prefix = b""
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=destination.parent, prefix=".upload-", suffix=".tmp", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            while True:
                chunk = await upload.read(CHUNK_SIZE)
                if not chunk:
                    break
                if len(prefix) < 1024:
                    prefix += chunk[: 1024 - len(prefix)]
                total_size += len(chunk)
                if total_size > settings.ADMISSIONS_MAX_UPLOAD_BYTES:
                    raise StorageError(
                        f"Fichier trop volumineux. Limite : {settings.ADMISSIONS_MAX_UPLOAD_BYTES} octets."
                    )
                temporary.write(chunk)
            temporary.flush()
            os.fsync(temporary.fileno())

        if total_size == 0:
            raise StorageError("Le fichier envoyé est vide.")
        if not _has_valid_signature(extension, prefix):
            raise StorageError("Le contenu du fichier ne correspond pas à son extension.")

        os.replace(temporary_path, destination)
        temporary_path = None
        return relative.as_posix(), original_name, mime_type, total_size
    finally:
        try:
            await upload.close()
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)


def delete_stored_file(relative_path: str | None) -> None:
    """Supprime un fichier stocké sans jamais sortir de la racine configurée."""
    if not relative_path:
        return
    try:
        path = _resolve_stored_path(relative_path)
    except StorageError:
        # Une entrée DB historique invalide ne doit pas empêcher une autre
        # suppression; le chemin n'est jamais touché hors de la racine.
        return
    if path.is_file():
        path.unlink(missing_ok=True)


def media_type_for(filename: str | None) -> str:
    """Déduit un type de téléchargement sans faire confiance au client."""
    if not filename:
        return "application/octet-stream"
    extension = _extension(filename)
    for candidate_extension, mimes in _ALLOWED_EXTENSIONS.items():
        if candidate_extension == extension:
            return next(iter(mimes))
    return "application/octet-stream"
