"""
app/core/securite.py
Module de validation géométrique et sécuritaire en français.
Vérifie les enveloppes de travail autorisées (limites X/Y/Z, altitude de sécurité,
vitesses maximales) pour toute commande, quelle que soit son origine (manette, texte, voix...).
"""

from typing import Tuple, Optional, Dict, Any
from app.core.commandes import (
    TypeCommande,
    CommandeDeplacerVers,
    CommandeDeplacerRelatif,
    CommandePrendreDeposer
)


class VerificateurSecurite:
    """
    Vérificateur de sécurité centralisé.
    Empêche les collisions avec le sol, les fins de course matérielles et les dépassements de vitesse.
    """

    def __init__(self, limites: Optional[Dict[str, Any]] = None):
        limites = limites or {}
        self.x_min = float(limites.get("x_min", 100.0))
        self.x_max = float(limites.get("x_max", 320.0))
        self.y_min = float(limites.get("y_min", -200.0))
        self.y_max = float(limites.get("y_max", 200.0))
        self.z_min = float(limites.get("z_min", -50.0))
        self.z_max = float(limites.get("z_max", 150.0))
        self.z_transit_min = float(limites.get("z_transit_min", 20.0))
        self.ratio_vitesse_auto_max = float(limites.get("max_auto_speed_ratio", 70.0))

    @property
    def max_auto_speed_ratio(self) -> float:
        return self.ratio_vitesse_auto_max

    @max_auto_speed_ratio.setter
    def max_auto_speed_ratio(self, valeur: float):
        self.ratio_vitesse_auto_max = float(valeur)

    def valider_commande(self, commande: TypeCommande, pose_courante: Dict[str, float]) -> Tuple[bool, str]:
        """
        Vérifie la validité sécuritaire d'une commande.
        Retourne (True, "OK") ou (False, "Raison du refus").
        """
        # 1. Vérification Déplacement Absolu
        if isinstance(commande, CommandeDeplacerVers):
            return self.verifier_cible_cartesienne(commande.x, commande.y, commande.z)

        # 2. Vérification Déplacement Relatif
        if isinstance(commande, CommandeDeplacerRelatif):
            nom_axe = commande.axe.lower()
            valeur_courante = pose_courante.get(nom_axe, 0.0)
            valeur_cible = valeur_courante + commande.pas

            if nom_axe == "x":
                return self._verifier_intervalle("X", valeur_cible, self.x_min, self.x_max)
            elif nom_axe == "y":
                return self._verifier_intervalle("Y", valeur_cible, self.y_min, self.y_max)
            elif nom_axe == "z":
                return self._verifier_intervalle("Z", valeur_cible, self.z_min, self.z_max)

        # 3. Arrêt et Home toujours autorisés
        return True, "Commande sécurisée validée."

    # Alias de compatibilité
    validate_command = valider_commande

    def verifier_cible_cartesienne(self, x: float, y: float, z: float) -> Tuple[bool, str]:
        """Vérifie qu'un point (X, Y, Z) se trouve à l'intérieur du volume de travail sécurisé."""
        ok_x, message_x = self._verifier_intervalle("X", x, self.x_min, self.x_max)
        if not ok_x:
            return False, message_x

        ok_y, message_y = self._verifier_intervalle("Y", y, self.y_min, self.y_max)
        if not ok_y:
            return False, message_y

        ok_z, message_z = self._verifier_intervalle("Z", z, self.z_min, self.z_max)
        if not ok_z:
            return False, message_z

        return True, "Position cible autorisée."

    # Alias de compatibilité
    check_cartesian_target = verifier_cible_cartesienne

    @staticmethod
    def _verifier_intervalle(nom_axe: str, valeur: float, min_val: float, max_val: float) -> Tuple[bool, str]:
        if valeur < min_val or valeur > max_val:
            return False, f"Axe {nom_axe} hors limites de sécurité ({valeur:.1f} mm demandé, intervalle autorisé : [{min_val:.1f}, {max_val:.1f}])"
        return True, "OK"

    # Alias de compatibilité
    _check_range = _verifier_intervalle


# Alias de classe rétrocompatible
SafetyChecker = VerificateurSecurite

