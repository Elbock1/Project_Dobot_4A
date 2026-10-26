"""
app/robot/controleur.py
Contrôleur unifié ControleurDobot encapsulant le matériel ou le simulateur en français.
Corrige le goulot d'étranglement du JOG :
- Le battement (battement_jog) rafraîchit uniquement un horodatage (0 échange série).
- Un thread d'arrière-plan de télémétrie lit la pose et les alarmes à basse fréquence (3-4 Hz).
- Chien de garde (watchdog) de sécurité automatique sur perte de battement.
"""

import threading
import time
from typing import Dict, Any, Optional

try:
    import serial
    from pydobot import Dobot
except ImportError:
    serial = None
    Dobot = None

from app.robot import protocole
from app.robot.simulation import DobotSimule


class ControleurDobot:
    """
    Contrôleur thread-safe du Dobot Magician.
    Prend en charge la déconnexion/reconnexion, la simulation (DobotSimule) et les sécurités JOG.
    """

    def __init__(self, port: str = "COM4", debit_bauds: int = 115200, simulation: bool = False,
                 delai_inactivite_jog: float = 0.5, frequence_telemetrie_hz: float = 4.0, **kwargs):
        self.port = port
        self.debit_bauds = kwargs.get("baudrate", debit_bauds)
        self.mode_simulation = kwargs.get("mock", simulation)
        self.delai_jog = kwargs.get("jog_timeout", delai_inactivite_jog)
        self.periode_telemetrie = 1.0 / max(1.0, float(kwargs.get("telemetry_rate_hz", frequence_telemetrie_hz)))

        self.appareil = None
        self.verrou = threading.Lock()

        # État interne en français
        self.occupe = False
        self.dernier_message = "Initialisation..."
        self.dernier_battement = 0.0
        self.jog_actif = False
        self.jog_articulaire = False
        self.ratio_jog = 100.0

        # Pose courante mémorisée
        self.cible = {
            "x": 250.0, "y": 0.0, "z": 50.0, "r": 0.0,
            "j1": 0.0, "j2": 0.0, "j3": 0.0, "j4": 0.0
        }

        # Outils
        self.etat_ventouse = False
        self.etat_pince = False

        # Threads d'arrière-plan
        self._en_cours = True
        self._fil_chien_de_garde = threading.Thread(target=self._boucle_chien_de_garde, daemon=True)
        self._fil_telemetrie = threading.Thread(target=self._boucle_telemetrie, daemon=True)

    # --- Propriétés de rétrocompatibilité en anglais ---

    @property
    def baudrate(self) -> int:
        return self.debit_bauds

    @baudrate.setter
    def baudrate(self, v: int):
        self.debit_bauds = v

    @property
    def use_mock(self) -> bool:
        return self.mode_simulation

    @use_mock.setter
    def use_mock(self, v: bool):
        self.mode_simulation = v

    @property
    def jog_timeout(self) -> float:
        return self.delai_jog

    @jog_timeout.setter
    def jog_timeout(self, v: float):
        self.delai_jog = v

    @property
    def telemetry_period(self) -> float:
        return self.periode_telemetrie

    @telemetry_period.setter
    def telemetry_period(self, v: float):
        self.periode_telemetrie = v

    @property
    def device(self):
        return self.appareil

    @device.setter
    def device(self, v):
        self.appareil = v

    @property
    def lock(self) -> threading.Lock:
        return self.verrou

    @property
    def busy(self) -> bool:
        return self.occupe

    @busy.setter
    def busy(self, v: bool):
        self.occupe = v

    @property
    def last_message(self) -> str:
        return self.dernier_message

    @last_message.setter
    def last_message(self, v: str):
        self.dernier_message = v

    @property
    def last_beat(self) -> float:
        return self.dernier_battement

    @last_beat.setter
    def last_beat(self, v: float):
        self.dernier_battement = v

    @property
    def jog_active(self) -> bool:
        return self.jog_actif

    @jog_active.setter
    def jog_active(self, v: bool):
        self.jog_actif = v

    @property
    def jog_joint(self) -> bool:
        return self.jog_articulaire

    @jog_joint.setter
    def jog_joint(self, v: bool):
        self.jog_articulaire = v

    @property
    def jog_ratio(self) -> float:
        return self.ratio_jog

    @jog_ratio.setter
    def jog_ratio(self, v: float):
        self.ratio_jog = v

    @property
    def target(self) -> Dict[str, float]:
        return self.cible

    @target.setter
    def target(self, v: Dict[str, float]):
        self.cible = v

    @property
    def suction_state(self) -> bool:
        return self.etat_ventouse

    @suction_state.setter
    def suction_state(self, v: bool):
        self.etat_ventouse = v

    @property
    def gripper_state(self) -> bool:
        return self.etat_pince

    @gripper_state.setter
    def gripper_state(self, v: bool):
        self.etat_pince = v

    @property
    def _running(self) -> bool:
        return self._en_cours

    @_running.setter
    def _running(self, v: bool):
        self._en_cours = v

    # --- Initialisation ---

    def initialiser(self) -> bool:
        """Tente la connexion réelle ou bascule sur DobotSimule si configuré ou en cas d'échec."""
        if not self.mode_simulation and Dobot is not None:
            print(f"[ControleurDobot] Tentative de connexion sur {self.port}...")
            self.appareil = self._connecter_serie(self.port)

        if self.appareil is None:
            print("[ControleurDobot] Bras physique non disponible -> Activation du mode SIMULATION.")
            self.mode_simulation = True
            self.appareil = DobotSimule(port=self.port)

        # Configuration initiale des vitesses
        try:
            with self.verrou:
                if hasattr(self.appareil, 'speed'):
                    self.appareil.speed(200, 200)
                protocole.configurer_dynamique_jog(self.appareil, 150, 300, self.ratio_jog)
                protocole.effacer_alarmes(self.appareil)
                self._resynchroniser_interne()
            self.dernier_message = "Prêt (Mode " + ("Simulation" if self.mode_simulation else "Matériel") + ")"
        except Exception as e:
            print(f"[ControleurDobot] Avertissement configuration initiale : {e}")

        # Démarrage des threads de fond
        self._fil_chien_de_garde.start()
        self._fil_telemetrie.start()
        return True

    initialize = initialiser

    def _connecter_serie(self, nom_port: str, tentatives_max: int = 3):
        if serial is None or Dobot is None:
            return None
        for essai in range(1, tentatives_max + 1):
            try:
                # Purge préventive du buffer COM
                with serial.Serial(nom_port, baudrate=self.debit_bauds, timeout=1) as liaison_serie:
                    liaison_serie.reset_input_buffer()
                    liaison_serie.reset_output_buffer()
                time.sleep(0.3)
                peripherique = Dobot(port=nom_port, verbose=False)
                print(f"[ControleurDobot] Dobot connecté avec succès sur {nom_port} !")
                return peripherique
            except Exception as e:
                print(f"[ControleurDobot] Essai {essai}/{tentatives_max} échoué : {e}")
                time.sleep(0.5)
        return None

    _connect_serial = _connecter_serie

    def obtenir_statut(self) -> Dict[str, Any]:
        """Retourne l'état complet actuel (thread-safe, non-bloquant), en français et en anglais."""
        return {
            **self.cible,
            # Clés en français
            "occupe": self.occupe,
            "jog_actif": self.jog_actif,
            "ratio_vitesse": self.ratio_jog,
            "ventouse": self.etat_ventouse,
            "pince": self.etat_pince,
            "simulation": self.mode_simulation,
            "dernier_message": self.dernier_message,
            # Clés en anglais pour compatibilité
            "busy": self.occupe,
            "jog_active": self.jog_actif,
            "speed_ratio": self.ratio_jog,
            "suction": self.etat_ventouse,
            "gripper": self.etat_pince,
            "mock": self.mode_simulation,
            "message": self.dernier_message,
            "ok": True
        }

    get_status = obtenir_statut

    # ------------------------------------------------------------------ JOG FLUIDE

    def demarrer_jog(self, axe: str, direction: float) -> Dict[str, Any]:
        """Déclenche le mouvement JOG continu."""
        if self.occupe:
            return self._erreur("Recalage en cours, mouvement ignoré.")

        axe_maj = str(axe).upper()
        if axe_maj in protocole.BASE_JOG_CARTESIEN:
            est_articulaire, base = False, protocole.BASE_JOG_CARTESIEN[axe_maj]
        elif axe_maj in protocole.BASE_JOG_ARTICULAIRE:
            est_articulaire, base = True, protocole.BASE_JOG_ARTICULAIRE[axe_maj]
        else:
            return self._erreur(f"Axe inconnu : {axe}")

        positif = float(direction) > 0
        code_cmd = base + (0 if positif else 1)

        with self.verrou:
            if self.occupe:
                return self._erreur("Recalage en cours, mouvement ignoré.")
            try:
                if protocole.verifier_alarmes(self.appareil):
                    self._recuperer_alarmes_interne()

                protocole.envoyer_pas_jog(self.appareil, est_articulaire, code_cmd)
                self.jog_articulaire = est_articulaire
                self.jog_actif = True
                self.dernier_battement = time.time()
                self.dernier_message = f"JOG {axe_maj} {'+' if positif else '-'}"
                return self.obtenir_statut()
            except Exception as e:
                self.jog_actif = False
                return self._erreur(f"Erreur démarrage JOG : {e}")

    jog_start = demarrer_jog

    def battement_jog(self) -> Dict[str, Any]:
        """
        Le battement met SEULEMENT à jour l'horodatage dernier_battement.
        Ne fait aucun appel série bloquant !
        """
        self.dernier_battement = time.time()
        return self.obtenir_statut()

    jog_beat = battement_jog

    def arreter_jog(self) -> Dict[str, Any]:
        """Arrête le mouvement JOG."""
        with self.verrou:
            try:
                protocole.envoyer_pas_jog(self.appareil, self.jog_articulaire, 0)
                self.jog_actif = False
                if protocole.verifier_alarmes(self.appareil):
                    self._recuperer_alarmes_interne()
                self._resynchroniser_interne()
                self.dernier_message = "Prêt."
                return self.obtenir_statut()
            except Exception as e:
                self.jog_actif = False
                return self._erreur(f"Erreur arrêt JOG : {e}")

    jog_stop = arreter_jog

    # ------------------------------------------------------------------ PTP & COMMANDES

    def deplacer_vers(self, x: float, y: float, z: float, r: float = 0.0, attente: bool = False, **kwargs) -> Dict[str, Any]:
        """Déplacement cartésien absolu contrôlé."""
        att = kwargs.get("wait", attente)
        if self.occupe:
            return self._erreur("Recalage en cours.")

        with self.verrou:
            try:
                if protocole.verifier_alarmes(self.appareil):
                    self._recuperer_alarmes_interne()
                self.appareil.move_to(float(x), float(y), float(z), float(r), wait=att)
                self.cible.update(x=float(x), y=float(y), z=float(z), r=float(r))
                self.dernier_message = f"Déplacement vers ({x:.1f}, {y:.1f}, {z:.1f})"
                return self.obtenir_statut()
            except Exception as e:
                return self._erreur(f"Erreur deplacer_vers : {e}")

    move_to = deplacer_vers

    def deplacer_relatif(self, axe: str, pas: float) -> Dict[str, Any]:
        """Déplacement pas-à-pas relatif."""
        axe_maj = str(axe).upper()
        if axe_maj not in ("X", "Y", "Z", "R"):
            return self._erreur(f"Axe relatif invalide : {axe}")

        with self.verrou:
            try:
                if protocole.verifier_alarmes(self.appareil):
                    self._recuperer_alarmes_interne()
                self._resynchroniser_interne()

                nouvelle_pose = dict(self.cible)
                nouvelle_pose[axe_maj.lower()] += float(pas)
                self.appareil.move_to(nouvelle_pose["x"], nouvelle_pose["y"], nouvelle_pose["z"], nouvelle_pose["r"], wait=False)
                self.cible.update(nouvelle_pose)
                self.dernier_message = f"Axe {axe_maj} {float(pas):+g} mm"
                return self.obtenir_statut()
            except Exception as e:
                return self._erreur(f"Erreur deplacer_relatif : {e}")

    move_relative = deplacer_relatif

    def regler_ratio_vitesse(self, ratio: float) -> Dict[str, Any]:
        """Met à jour le ratio de vitesse (1-100 %)."""
        ratio_borne = max(1.0, min(100.0, float(ratio)))
        self.ratio_jog = ratio_borne
        with self.verrou:
            try:
                protocole.regler_ratio_jog(self.appareil, ratio_borne)
                if hasattr(self.appareil, 'jog_ratio'):
                    self.appareil.jog_ratio = ratio_borne
                self.dernier_message = f"Vitesse réglée à {ratio_borne:.0f} %"
                return self.obtenir_statut()
            except Exception as e:
                return self._erreur(f"Erreur réglage vitesse : {e}")

    set_speed_ratio = regler_ratio_vitesse

    def regler_effecteur(self, outil: str, actif: bool) -> Dict[str, Any]:
        """Commande la ventouse (suction/ventouse) ou la pince (gripper/pince)."""
        outil_nom = outil.lower()
        actif_bool = bool(actif)
        with self.verrou:
            try:
                if outil_nom in ("suction", "ventouse"):
                    if hasattr(self.appareil, 'suck'):
                        self.appareil.suck(actif_bool)
                    self.etat_ventouse = actif_bool
                    self.dernier_message = "Ventouse activée" if actif_bool else "Ventouse désactivée"
                elif outil_nom in ("gripper", "pince"):
                    if hasattr(self.appareil, 'grip'):
                        self.appareil.grip(actif_bool)
                    self.etat_pince = actif_bool
                    self.dernier_message = "Pince fermée" if actif_bool else "Pince ouverte"
                else:
                    return self._erreur(f"Outil inconnu : {outil}")
                return self.obtenir_statut()
            except Exception as e:
                return self._erreur(f"Erreur effecteur {outil} : {e}")

    set_effector = regler_effecteur

    def arret_urgence(self) -> Dict[str, Any]:
        """Arrêt d'urgence prioritaire et inconditionnel."""
        self.jog_actif = False
        verrou_obtenu = self.verrou.acquire(timeout=0.3)
        try:
            protocole.envoyer_pas_jog(self.appareil, self.jog_articulaire, 0)
            protocole.arreter_et_vider_file(self.appareil)
            protocole.effacer_alarmes(self.appareil)
            if verrou_obtenu:
                self._resynchroniser_interne()
            self.dernier_message = "ARRÊT D'URGENCE EXÉCUTÉ"
            return self.obtenir_statut()
        except Exception as e:
            return self._erreur(f"Erreur arrêt d'urgence : {e}")
        finally:
            if verrou_obtenu:
                self.verrou.release()

    emergency_stop = arret_urgence

    # ------------------------------------------------------------------ RECALAGE ASYNCHRONE

    def demarrer_recalage_asynchrone(self) -> Dict[str, Any]:
        """Déclenche la procédure HOME dans un thread dédié."""
        if self.occupe:
            return self._erreur("Recalage déjà en cours.")

        with self.verrou:
            self.occupe = True
            if self.jog_actif:
                protocole.envoyer_pas_jog(self.appareil, self.jog_articulaire, 0)
                self.jog_actif = False
            self.dernier_message = "Recalage HOME en cours..."

        from app.robot.recalage import executer_sequence_recalage
        threading.Thread(target=self._executer_tache_recalage, args=(executer_sequence_recalage,), daemon=True).start()
        return self.obtenir_statut()

    start_homing_async = demarrer_recalage_asynchrone

    def _executer_tache_recalage(self, fonction_recalage):
        try:
            with self.verrou:
                resultat = fonction_recalage(self.appareil, simulation=self.mode_simulation)
                self._resynchroniser_interne()
            self.dernier_message = resultat.get("message", "Recalage terminé.")
        except Exception as e:
            self.dernier_message = f"Erreur Recalage : {e}"
        finally:
            self.occupe = False

    _run_homing_task = _executer_tache_recalage

    # ------------------------------------------------------------------ THREADS DE FOND

    def _boucle_chien_de_garde(self):
        """Vérifie la perte de battement JOG (~10 Hz)."""
        while self._en_cours:
            time.sleep(0.1)
            if self.jog_actif and (time.time() - self.dernier_battement > self.delai_jog):
                with self.verrou:
                    if self.jog_actif and (time.time() - self.dernier_battement > self.delai_jog):
                        try:
                            protocole.envoyer_pas_jog(self.appareil, self.jog_articulaire, 0)
                            print("[CHIEN DE GARDE] Battement JOG interrompu -> Bras stoppé.")
                        finally:
                            self.jog_actif = False

    _watchdog_loop = _boucle_chien_de_garde

    def _boucle_telemetrie(self):
        """Lecture périodique de la pose et des alarmes à 3-4 Hz (hors du chemin critique JOG)."""
        while self._en_cours:
            time.sleep(self.periode_telemetrie)
            if not self.occupe and not self.jog_actif:
                if self.verrou.acquire(blocking=False):
                    try:
                        self._resynchroniser_interne()
                        if protocole.verifier_alarmes(self.appareil):
                            self._recuperer_alarmes_interne()
                    except Exception:
                        pass
                    finally:
                        self.verrou.release()

    _telemetry_loop = _boucle_telemetrie

    def _resynchroniser_interne(self):
        if hasattr(self.appareil, 'pose'):
            p = self.appareil.pose()
            if p and len(p) >= 4:
                self.cible.update(x=float(p[0]), y=float(p[1]), z=float(p[2]), r=float(p[3]))
                if len(p) >= 8:
                    self.cible.update(j1=float(p[4]), j2=float(p[5]), j3=float(p[6]), j4=float(p[7]))

    _resync_internal = _resynchroniser_interne

    def _recuperer_alarmes_interne(self):
        protocole.arreter_et_vider_file(self.appareil)
        protocole.effacer_alarmes(self.appareil)
        self.dernier_message = "Alarme détectée et réinitialisée."

    _recover_alarms_internal = _recuperer_alarmes_interne

    def _erreur(self, message: str) -> Dict[str, Any]:
        self.dernier_message = message
        etat = self.obtenir_statut()
        etat["ok"] = False
        return etat

    _error = _erreur


# Alias rétrocompatible
DobotController = ControleurDobot

