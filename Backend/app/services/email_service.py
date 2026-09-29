"""
Envoi d'emails (lot 4) : un service, deux modes.

**Configuré** (``SMTP_HOST`` renseigné) : l'email part réellement via SMTP,
asynchrone (``aiosmtplib``), avec un délai d'expiration court — un serveur
de courrier lent ne doit pas geler une requête du secrétariat.

**Non configuré** (``SMTP_HOST`` vide) : **mode SIMULATION**. Aucun email ne
part, mais l'appel se comporte exactement comme un envoi réel : même retour,
même trace. Deux raisons :

1. un institut peut utiliser le module de relances sans compte SMTP — les
   relances s'enregistrent, le PDF se télécharge, et l'application **dit**
   que l'email n'est pas parti, elle ne le prétend pas ;
2. les tests automatisés ne dépendent jamais d'un serveur extérieur.

La trace de chaque envoi est rendue à l'appelant (``EmailEnvoye``) : c'est
elle qui alimente l'historique des relances, jamais une supposition.
"""

from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import List, Optional

import aiosmtplib

from app.core.config import settings


@dataclass
class EmailEnvoye:
    """Le résultat d'un envoi, vrai ou simulé : ce que l'historique conserve."""

    destinataire: str
    sujet: str
    #: ``envoye`` (parti), ``simule`` (SMTP non configuré) ou ``echec``.
    statut: str
    #: Le détail technique en cas d'échec : ce que l'exploitation lira.
    detail: Optional[str] = None
    pieces_jointes: List[str] = field(default_factory=list)

    @property
    def parti(self) -> bool:
        """Vrai si l'email est parti OU a été simulé : dans les deux cas,
        l'application a fait ce qu'elle devait. Seul ``echec`` déçoit."""
        return self.statut in ("envoye", "simule")


def smtp_configure() -> bool:
    """Le serveur de courrier est-il configuré ?"""
    return bool(settings.SMTP_HOST.strip())


def composer_email(
    *,
    destinataire: str,
    sujet: str,
    corps_texte: str,
    corps_html: Optional[str] = None,
    pieces_jointes: Optional[List[tuple]] = None,
) -> EmailMessage:
    """Construit le message MIME : texte obligatoire, HTML optionnel, PDF en pièce jointe.

    Les pièces jointes sont des tuples ``(nom_fichier, octets,
    type_mime)`` — le PDF de relance arrive ici tel qu'il sera imprimé.
    """
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = destinataire
    message["Subject"] = sujet
    message.set_content(corps_texte)
    if corps_html:
        message.add_alternative(corps_html, subtype="html")
    for nom, contenu, type_mime in pieces_jointes or []:
        maintype, subtype = type_mime.split("/", 1)
        message.add_attachment(contenu, maintype=maintype, subtype=subtype, filename=nom)
    return message


async def envoyer_email(
    *,
    destinataire: str,
    sujet: str,
    corps_texte: str,
    corps_html: Optional[str] = None,
    pieces_jointes: Optional[List[tuple]] = None,
) -> EmailEnvoye:
    """Envoie (ou simule) un email, sans jamais lever : le résultat dit tout.

    Un échec SMTP n'est pas une erreur applicative — le serveur de courrier
    peut être en panne sans que l'enregistrement de la relance doive échouer.
    L'appelant décide quoi faire du statut ``echec`` (avertir l'utilisateur,
    retenter plus tard) ; ici, on n'interrompt jamais le parcours métier.
    """
    if not smtp_configure():
        return EmailEnvoye(
            destinataire=destinataire,
            sujet=sujet,
            statut="simule",
            detail="SMTP non configuré : envoi simulé (SMTP_HOST vide).",
            pieces_jointes=[nom for nom, _, _ in pieces_jointes or []],
        )

    message = composer_email(
        destinataire=destinataire,
        sujet=sujet,
        corps_texte=corps_texte,
        corps_html=corps_html,
        pieces_jointes=pieces_jointes,
    )
    try:
        reponse = await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            start_tls=settings.SMTP_STARTTLS,
            timeout=settings.EMAIL_SEND_TIMEOUT_SECONDS,
        )
        return EmailEnvoye(
            destinataire=destinataire,
            sujet=sujet,
            statut="envoye",
            detail=str(reponse) if reponse else None,
            pieces_jointes=[nom for nom, _, _ in pieces_jointes or []],
        )
    except Exception as exc:  # aiosmtplib lève SMTP*Exception, socket, timeout...
        return EmailEnvoye(
            destinataire=destinataire,
            sujet=sujet,
            statut="echec",
            detail=f"{type(exc).__name__}: {exc}",
            pieces_jointes=[nom for nom, _, _ in pieces_jointes or []],
        )
