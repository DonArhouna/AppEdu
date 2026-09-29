"""Limiteur de débit en mémoire, pour les endpoints d'authentification.

Un compteur glissant par clé (IP + email tenté), conservé dans le processus.
Le parti pris est assumé et documenté :

- **en mémoire** : aucune infrastructure à provisionner. La contrepartie — le
  compteur vit et meurt avec le processus, et une grappe multi-processus
  compte N fois — est acceptable pour un déploiement on-premise mono-instance,
  qui est le cas nominal d'EduManagePro ;
- **la fenêtre ne compte que les échecs** : un NAT d'école derrière lequel se
  connectent trente élèves légitimes ne doit pas se verrouiller lui-même à
  chaque rentrée. Le compteur d'échecs **par compte** (verrouillage) complète
  le taux **par adresse** : l'un limite le débit, l'autre punit la cible ;
- la clé melange IP et email : une même adresse qui martèle un compte est
  bloquée vite, une adresse distribuée qui vise un compte l'est par le
  verrouillage du compte.

Une clé oubliée coûte une entrée de dictionnaire ; le ménage passe à chaque
appel et n'est ni un cron ni une tâche de fond.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, List, Tuple

from app.core.config import settings

#: (fenetre_secondes, [horodatages des echecs]) — un dictionnaire de series.
_echecs: Dict[str, List[float]] = defaultdict(list)


def _nettoyer(cle: str, fenetre: int, maintenant: float) -> List[float]:
    vivants = [
        horodatage
        for horodatage in _echecs.get(cle, [])
        if maintenant - horodatage < fenetre
    ]
    if vivants:
        _echecs[cle] = vivants
    else:
        _echecs.pop(cle, None)
    return vivants


def depasser(cle: str) -> Tuple[bool, int]:
    """La fenêtre est-elle dépassée pour cette clé ? Rend ``(dépassé, retry_s)``.

    Compte les échecs **enregistrés** de la fenêtre glissante ; ne compte pas
    la tentative en cours — c'est ``compter`` qui le fait, après la réponse.
    """
    fenetre = settings.LOGIN_RATE_WINDOW_SECONDS
    vivants = _nettoyer(cle, fenetre, time.monotonic())
    if len(vivants) >= settings.LOGIN_RATE_MAX_ATTEMPTS:
        plus_ancien = min(vivants)
        retry = int(fenetre - (time.monotonic() - plus_ancien)) + 1
        return True, max(1, retry)
    return False, 0


def compter(cle: str) -> None:
    """Enregistre un échec pour la clé. À appeler APRÈS la réponse d'échec."""
    _echecs[cle].append(time.monotonic())


def liberer(cle: str) -> None:
    """Efface la série : une connexion réussie rend sa clé à la fenêtre."""
    _echecs.pop(cle, None)


def cle_login(ip: str | None, email: str) -> str:
    """La clé du couple (adresse, email tenté), insensible à la casse."""
    return f"{(ip or '?').lower()}|{email.lower()}"


__all__ = ["cle_login", "compter", "depasser", "liberer"]
