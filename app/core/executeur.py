"""
app/core/executeur.py
File d'exécution séquentielle des tâches en français (un seul mouvement à la fois).
Garantit que l'arrêt d'urgence passe en priorité absolue et vide la file.
"""

import queue
import threading
import time
from typing import Dict, Any
from app.core.commandes import (
    TypeCommande,
    CommandeDeplacerVers,
    CommandeDeplacerRelatif,
    CommandePince,
    CommandeVentouse,
    CommandeRecalage,
    CommandeArret
)


class ExecuteurCommandes:
    """
    Exécuteur de commandes asynchrone avec file FIFO et arrêt prioritaire.
    """

    def __init__(self, controleur, verificateur_securite):
        self.controleur = controleur
        self.securite = verificateur_securite
        self.file_attente = queue.Queue()
        self._en_cours = True
        self._fil_travailleur = threading.Thread(target=self._boucle_travailleur, daemon=True)
        self._fil_travailleur.start()

    # Propriétés de compatibilité anglais
    @property
    def controller(self):
        return self.controleur

    @controller.setter
    def controller(self, valeur):
        self.controleur = valeur

    @property
    def safety(self):
        return self.securite

    @safety.setter
    def safety(self, valeur):
        self.securite = valeur

    @property
    def queue(self):
        return self.file_attente

    @queue.setter
    def queue(self, valeur):
        self.file_attente = valeur

    @property
    def _running(self):
        return self._en_cours

    @_running.setter
    def _running(self, valeur):
        self._en_cours = valeur

    def soumettre(self, commande: TypeCommande) -> Dict[str, Any]:
        """
        Soumet une commande validée à l'exécuteur.
        Si la commande est un arrêt d'urgence, la file est vidée sur-le-champ.
        """
        if isinstance(commande, CommandeArret):
            # Vidage immédiat de la file d'attente
            with self.file_attente.mutex:
                self.file_attente.queue.clear()
            # Appel de la méthode d'arrêt d'urgence du contrôleur
            if hasattr(self.controleur, 'arret_urgence'):
                return self.controleur.arret_urgence()
            return self.controleur.emergency_stop()

        # Validation de sécurité préalable
        pose_courante = getattr(self.controleur, 'cible', getattr(self.controleur, 'target', {}))
        if hasattr(self.securite, 'valider_commande'):
            valide, raison = self.securite.valider_commande(commande, pose_courante)
        else:
            valide, raison = self.securite.validate_command(commande, pose_courante)

        if not valide:
            return {"ok": False, "message": f"Refus sécuritaire : {raison}"}

        self.file_attente.put(commande)
        nom_action = getattr(commande, 'action', 'inconnue')
        return {"ok": True, "message": f"Commande '{nom_action}' ajoutée à la file d'attente."}

    # Alias de compatibilité
    submit = soumettre

    def _boucle_travailleur(self):
        while self._en_cours:
            try:
                commande: TypeCommande = self.file_attente.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                self._distribuer(commande)
            except Exception as e:
                print(f"[Executeur] Erreur d'exécution de la commande : {e}")
            finally:
                self.file_attente.task_done()

    _worker_loop = _boucle_travailleur

    def _distribuer(self, commande: TypeCommande):
        if isinstance(commande, CommandeDeplacerVers):
            if hasattr(self.controleur, 'deplacer_vers'):
                self.controleur.deplacer_vers(commande.x, commande.y, commande.z, commande.r, attente=True)
            else:
                self.controleur.move_to(commande.x, commande.y, commande.z, commande.r, wait=True)

        elif isinstance(commande, CommandeDeplacerRelatif):
            axe = getattr(commande, 'axe', getattr(commande, 'axis', 'X'))
            pas = getattr(commande, 'pas', getattr(commande, 'step', 0.0))
            if hasattr(self.controleur, 'deplacer_relatif'):
                self.controleur.deplacer_relatif(axe, pas)
            else:
                self.controleur.move_relative(axe, pas)

        elif isinstance(commande, CommandePince):
            actif = getattr(commande, 'activer', getattr(commande, 'on', False))
            if hasattr(self.controleur, 'regler_effecteur'):
                self.controleur.regler_effecteur("pince", actif)
            else:
                self.controleur.set_effector("gripper", actif)

        elif isinstance(commande, CommandeVentouse):
            actif = getattr(commande, 'activer', getattr(commande, 'on', False))
            if hasattr(self.controleur, 'regler_effecteur'):
                self.controleur.regler_effecteur("ventouse", actif)
            else:
                self.controleur.set_effector("suction", actif)

        elif isinstance(commande, CommandeRecalage):
            if hasattr(self.controleur, 'demarrer_recalage_asynchrone'):
                self.controleur.demarrer_recalage_asynchrone()
            else:
                self.controleur.start_homing_async()
            # Attente de la fin du recalage
            while getattr(self.controleur, 'occupe', getattr(self.controleur, 'busy', False)) and self._en_cours:
                time.sleep(0.2)

    _dispatch = _distribuer


# Alias de classe rétrocompatible
CommandExecutor = ExecuteurCommandes

