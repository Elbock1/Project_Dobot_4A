"""
app/core/etat.py
Statut partagé et gestion du verrou de session de pilotage en français.
Garantit qu'un seul utilisateur contrôle le robot à la fois pour éviter les collisions d'ordres.
"""

import time
import threading
from typing import Optional, Dict, Any


class GestionnaireSession:
    """Gère l'attribution exclusive du contrôle (verrou de session avec délai d'expiration)."""

    def __init__(self, delai_expiration_secondes: float = 60.0):
        self.verrou = threading.Lock()
        self.delai_expiration = delai_expiration_secondes
        self.id_session_active: Optional[str] = None
        self.derniere_activite: float = 0.0

    # Propriétés de compatibilité
    @property
    def lock(self) -> threading.Lock:
        return self.verrou

    @property
    def timeout(self) -> float:
        return self.delai_expiration

    @timeout.setter
    def timeout(self, valeur: float):
        self.delai_expiration = float(valeur)

    @property
    def active_session_id(self) -> Optional[str]:
        return self.id_session_active

    @active_session_id.setter
    def active_session_id(self, valeur: Optional[str]):
        self.id_session_active = valeur

    @property
    def last_activity(self) -> float:
        return self.derniere_activite

    @last_activity.setter
    def last_activity(self, valeur: float):
        self.derniere_activite = float(valeur)

    def acquerir_controle(self, id_session: str) -> bool:
        """Tente d'acquérir ou de renouveler le contrôle exclusif."""
        with self.verrou:
            maintenant = time.time()
            if self.id_session_active is None or (maintenant - self.derniere_activite > self.delai_expiration):
                self.id_session_active = id_session
                self.derniere_activite = maintenant
                return True
            if self.id_session_active == id_session:
                self.derniere_activite = maintenant
                return True
            return False

    acquire_control = acquerir_controle

    def liberer_controle(self, id_session: str) -> None:
        """Libère le contrôle."""
        with self.verrou:
            if self.id_session_active == id_session:
                self.id_session_active = None
                self.derniere_activite = 0.0

    release_control = liberer_controle

    def est_controle_par(self, id_session: Optional[str]) -> bool:
        """Vérifie si la session donnée a le droit de piloter."""
        with self.verrou:
            if not self.id_session_active:
                return True
            maintenant = time.time()
            if maintenant - self.derniere_activite > self.delai_expiration:
                self.id_session_active = None
                return True
            return id_session == self.id_session_active

    is_controlled_by = est_controle_par


# Alias de classe rétrocompatible
SessionManager = GestionnaireSession

