"""Branding institutionnel : stockage et validation du logo.

Le logo est un **fichier**. Il vit donc hors PostgreSQL, dans
``storage/etablissement``, exactement comme les pieces d'admission et les PDF
emis. La base ne conserve que le chemin relatif, dans
``etablissements.logo_url``.

La validation porte sur les **octets**, pas sur ce que le navigateur annonce.
Un ``Content-Type: image/png`` ne prouve rien : on reconnait la signature
reelle du fichier, et on refuse tout le reste. Un logo est rendu par
ReportLab puis servi au navigateur : un SVG contenant un script, ou un PDF
deguise, n'a rien a faire dans un document officiel.
"""

from __future__ import annotations

import io
import secrets
from pathlib import Path
from typing import Optional, Tuple

from app.core.config import settings

#: Taille maximale. Un logo d'etablissement tient largement dans 512 Ko ; au
#: dela, c'est une erreur de selection, pas un logo.
LOGO_MAX_OCTETS = 512 * 1024

#: Formats acceptes, deduits de la signature des octets.  Le nom de la cle
#: est l'extension reelle du fichier stocke : on ne fait jamais confiance a
#: l'extension d'origine.
FORMATS: dict[str, Tuple[bytes, ...]] = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpeg": (b"\xff\xd8\xff",),
}

#: Types servis par l'endpoint de lecture.
TYPES_MIME: dict[str, str] = {"png": "image/png", "jpeg": "image/jpeg"}


class LogoInvalide(ValueError):
    """Le fichier transmis n'est pas un logo exploitable."""


# ---------------------------------------------------------------------------
# Stockage
# ---------------------------------------------------------------------------
def racine_branding() -> Path:
    """Racine de stockage du branding, creee a la demande."""

    configure = Path(settings.BRANDING_STORAGE_DIR)
    racine = (
        configure
        if configure.is_absolute()
        else Path(__file__).resolve().parents[2] / configure
    )
    racine.mkdir(parents=True, exist_ok=True)
    return racine.resolve()


def _resoudre(chemin_relatif: str) -> Optional[Path]:
    """Resout un chemin relatif sous la racine, ou ``None`` si invalide.

    La verification de prefixe est indispensable : sans elle, un
    ``logo_url`` forge (ou une base de donnee compromise) permettrait de faire
    lire n'importe quel fichier du serveur.
    """

    racine = racine_branding()
    cible = (racine / chemin_relatif).resolve()
    if not cible.is_relative_to(racine):
        return None
    if not cible.is_file():
        return None
    return cible


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def reconnaitre_format(contenu: bytes) -> Optional[str]:
    """Identifie le format d'un logo a partir de ses octets.

    Compare les prefixes reels. Un PNG commence toujours par sa signature
    complete ; un JPEG par son marqueur de debut — suivi de ``FF D9``, ce que
    le controle de taille laisse passer pour un fichier arbitraire, d'ou la
    verification par prefixe et non par searching.
    """

    for extension, signatures in FORMATS.items():
        for signature in signatures:
            if contenu.startswith(signature):
                return extension
    return None


#: Dimensions acceptees. Sous 32 px de large, un logo est illisible ; au-dela
#: de 4000 px, ce n'est pas un logo mais une photo, et le rendu PDF
#: exploserait en memoire.
LOGO_LARGEUR_MIN = 32
LOGO_LARGEUR_MAX = 4000


def dimensions_decodees(contenu: bytes) -> "tuple[int, int]":
    """Demande au decodeur de ReportLab la taille reelle de l'image.

    C'est la meme bibliotheque qui rendra le logo dans le document officiel :
    un fichier qu'elle refuse ne peut pas etre un logo exploitable.
    """

    from reportlab.lib.utils import ImageReader

    try:
        largeur, hauteur = ImageReader(io.BytesIO(contenu)).getSize()
    except Exception as exc:
        raise LogoInvalide(
            "Le fichier n'est pas une image lisible. Utilisez un PNG ou un "
            "JPEG reellement ouvrable, exporte depuis un outil d'image."
        ) from exc
    return int(largeur), int(hauteur)


def valider_logo(contenu: bytes) -> "tuple[str, int, int]":
    """Valide un logo et retourne ``(format, largeur, hauteur)``.

    Trois controles successifs, du plus fort au plus faible :

    1. la **decodabilite**, mesuree par le moteur de rendu ;
    2. le **format**, reconnu sur les octets, jamais d'apres le nom transmis ;
    3. les **dimensions**, pour rejeter un logo illisible ou une photo.
    """

    if not contenu:
        raise LogoInvalide("Le fichier est vide.")
    if len(contenu) > LOGO_MAX_OCTETS:
        raise LogoInvalide(
            f"Le logo depasse {LOGO_MAX_OCTETS // 1024} Ko "
            f"({len(contenu) // 1024} Ko recues)."
        )

    largeur, hauteur = dimensions_decodees(contenu)

    extension = reconnaitre_format(contenu)
    if extension is None:
        raise LogoInvalide(
            "Format non reconnu. Utilisez un fichier PNG ou JPEG : "
            "le format est verifie sur les octets, pas sur le nom du fichier."
        )

    if not (LOGO_LARGEUR_MIN <= largeur <= LOGO_LARGEUR_MAX) or not hauteur:
        raise LogoInvalide(
            f"Dimensions inadaptees ({largeur}x{hauteur} px). Un logo doit "
            f"faire au moins {LOGO_LARGEUR_MIN} px de large et au plus "
            f"{LOGO_LARGEUR_MAX} px."
        )
    return extension, largeur, hauteur


# ---------------------------------------------------------------------------
# Ecriture / lecture
# ---------------------------------------------------------------------------
def ecrire_logo(contenu: bytes, extension: str) -> str:
    """Ecrit le logo et retourne son chemin relatif.

    Le nom est genere, jamais repris de l'upload : un nom fourni par le
    client n'est pas un nom sur lequel on peut fonder une ecriture.
    """

    racine = racine_branding()
    nom = f"logo-{secrets.token_hex(8)}.{extension}"
    chemin = racine / nom
    chemin.write_bytes(contenu)
    return nom


def lire_logo(chemin_relatif: str) -> Optional[Tuple[bytes, str]]:
    """Relit un logo. Retourne ``(octets, type_mime)`` ou ``None``.

    ``None`` signifie « absent » : le fichier a ete supprime du disque. Un
    etablissement sans logo est un etablissement qui fonctionne, pas une
    erreur.
    """

    cible = _resoudre(chemin_relatif)
    if cible is None:
        return None
    extension = cible.suffix.lstrip(".").lower()
    type_mime = TYPES_MIME.get(extension)
    if type_mime is None:
        return None
    return cible.read_bytes(), type_mime


def supprimer_logo(chemin_relatif: str) -> bool:
    """Supprime le fichier du logo. Retourne ``True`` s'il existait."""

    cible = _resoudre(chemin_relatif)
    if cible is None:
        return False
    cible.unlink()
    return True
