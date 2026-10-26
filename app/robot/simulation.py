"""
app/robot/simulation.py
Simulation logicielle du bras Dobot Magician (DobotSimule / MockDobot) en français.
Permet de développer, exécuter et tester toutes les fonctionnalités de l'application
(JOG, PTP, recalage, pince, ventouse, vision) sans matériel physique.
"""

import time
import math
import threading
from typing import List, Optional, Tuple


class DobotSimule:
    """
    Simulateur de bras Dobot Magician implémentant l'API de pydobot.Dobot
    avec dynamique temporelle simplifiée.
    """

    def __init__(self, port: str = "SIMULATION", verbeux: bool = False, **kwargs):
        self.port = port
        self.verbeux = kwargs.get("verbose", verbeux)
        self.connecte = True

        # Position cartésienne courante (x, y, z, r) et articulaire (j1, j2, j3, j4)
        self.x = 250.0
        self.y = 0.0
        self.z = 50.0
        self.r = 0.0
        self.j1 = 0.0
        self.j2 = 25.0
        self.j3 = 45.0
        self.j4 = 0.0

        # Cible en cours de déplacement
        self._cible_x = self.x
        self._cible_y = self.y
        self._cible_z = self.z
        self._cible_r = self.r

        # HOME enregistré
        self.home_x = 250.0
        self.home_y = 0.0
        self.home_z = 50.0
        self.home_r = 0.0

        # Effecteurs
        self.ventouse_active = False
        self.pince_active = False

        # Dynamique
        self.vitesse = 200.0
        self.acceleration = 200.0
        self.ratio_jog = 100.0

        # JOG simulé
        self.jog_en_cours = False
        self.axe_jog = "X"
        self.direction_jog = 1.0
        self.jog_est_articulaire = False

        # Alarmes
        self.alarmes_actives = False
        self._octets_alarmes = bytearray([0] * 32)

        # Thread de mise à jour de la physique simulée
        self._en_cours = True
        self._fil_simulation = threading.Thread(target=self._boucle_physique, daemon=True)
        self._fil_simulation.start()

    # --- Propriétés de rétrocompatibilité en anglais ---

    @property
    def verbose(self) -> bool:
        return self.verbeux

    @verbose.setter
    def verbose(self, v: bool):
        self.verbeux = v

    @property
    def connected(self) -> bool:
        return self.connecte

    @connected.setter
    def connected(self, v: bool):
        self.connecte = v

    @property
    def suction_on(self) -> bool:
        return self.ventouse_active

    @suction_on.setter
    def suction_on(self, v: bool):
        self.ventouse_active = v

    @property
    def gripper_on(self) -> bool:
        return self.pince_active

    @gripper_on.setter
    def gripper_on(self, v: bool):
        self.pince_active = v

    @property
    def velocity(self) -> float:
        return self.vitesse

    @velocity.setter
    def velocity(self, v: float):
        self.vitesse = float(v)

    @property
    def jog_ratio(self) -> float:
        return self.ratio_jog

    @jog_ratio.setter
    def jog_ratio(self, v: float):
        self.ratio_jog = float(v)

    @property
    def jog_moving(self) -> bool:
        return self.jog_en_cours

    @jog_moving.setter
    def jog_moving(self, v: bool):
        self.jog_en_cours = v

    @property
    def jog_axis(self) -> str:
        return self.axe_jog

    @jog_axis.setter
    def jog_axis(self, v: str):
        self.axe_jog = v

    @property
    def jog_dir(self) -> float:
        return self.direction_jog

    @jog_dir.setter
    def jog_dir(self, v: float):
        self.direction_jog = float(v)

    @property
    def jog_is_joint(self) -> bool:
        return self.jog_est_articulaire

    @jog_is_joint.setter
    def jog_is_joint(self, v: bool):
        self.jog_est_articulaire = v

    @property
    def alarms_active(self) -> bool:
        return self.alarmes_actives

    @alarms_active.setter
    def alarms_active(self, v: bool):
        self.alarmes_actives = v

    @property
    def _alarm_bytes(self) -> bytearray:
        return self._octets_alarmes

    @_alarm_bytes.setter
    def _alarm_bytes(self, v: bytearray):
        self._octets_alarmes = v

    @property
    def _running(self) -> bool:
        return self._en_cours

    @_running.setter
    def _running(self, v: bool):
        self._en_cours = v

    # --- Méthodes de l'interface pydobot / Dobot ---

    def pose(self) -> List[float]:
        """Retourne la pose [x, y, z, r, j1, j2, j3, j4] comme pydobot."""
        return [self.x, self.y, self.z, self.r, self.j1, self.j2, self.j3, self.j4]

    obtenir_pose = pose

    def move_to(self, x: float, y: float, z: float, r: float, wait: bool = False, **kwargs) -> None:
        """Déplacement PTP vers coordonnées cibles."""
        attente = kwargs.get("attente", wait)
        self._cible_x = float(x)
        self._cible_y = float(y)
        self._cible_z = float(z)
        self._cible_r = float(r)

        if attente:
            delai_max = 10.0
            t0 = time.time()
            while time.time() - t0 < delai_max:
                if (abs(self.x - self._cible_x) < 0.5 and
                    abs(self.y - self._cible_y) < 0.5 and
                    abs(self.z - self._cible_z) < 0.5):
                    break
                time.sleep(0.05)

    deplacer_vers = move_to

    def speed(self, velocity: float, acceleration: float) -> None:
        """Règle la vitesse PTP."""
        self.vitesse = float(velocity)
        self.acceleration = float(acceleration)

    regler_vitesse = speed

    def suck(self, enable: bool) -> None:
        """Active/désactive la ventouse."""
        self.ventouse_active = bool(enable)

    aspirer = suck

    def grip(self, enable: bool) -> None:
        """Active/désactive la pince."""
        self.pince_active = bool(enable)

    pincer = grip

    def home(self) -> None:
        """Déclenche la procédure HOME simulée."""
        self.move_to(self.home_x, self.home_y, self.home_z, self.home_r, wait=False)

    recaler = home

    def close(self) -> None:
        """Ferme la liaison simulée."""
        self._en_cours = False
        self.connecte = False

    fermer = close

    # Méthode requise par le protocole pour simuler pydobot._send_command
    def _send_command(self, msg):
        class ReponseSimulee:
            def __init__(self, params=None):
                self.params = params or []

        # ID_ETAT_ALARMES (20)
        if msg.id == 20 and not msg.rw:
            return ReponseSimulee(params=self._octets_alarmes)

        # ID_EFFACER_ALARMES (21)
        if msg.id == 21 and msg.rw:
            self.alarmes_actives = False
            self._octets_alarmes = bytearray([0] * 32)
            return ReponseSimulee()

        # ID_PARAMETRES_HOME (30)
        if msg.id == 30 and not msg.rw:
            import struct
            donnees = struct.pack('<4f', self.home_x, self.home_y, self.home_z, self.home_r)
            return ReponseSimulee(params=list(donnees))

        # ID_COMMANDE_JOG (73)
        if msg.id == 73 and msg.rw:
            est_articulaire = bool(msg.params[0]) if msg.params else False
            code_cmd = int(msg.params[1]) if len(msg.params) > 1 else 0

            if code_cmd == 0:
                self.jog_en_cours = False
            else:
                self.jog_en_cours = True
                self.jog_est_articulaire = est_articulaire
                self._appliquer_commande_jog_simule(code_cmd, est_articulaire)
            return ReponseSimulee()

        return ReponseSimulee()

    def _appliquer_commande_jog_simule(self, code_cmd: int, est_articulaire: bool):
        if not est_articulaire:
            correspondances = {
                1: ("X", 1.0), 2: ("X", -1.0),
                3: ("Y", 1.0), 4: ("Y", -1.0),
                5: ("Z", 1.0), 6: ("Z", -1.0),
                7: ("R", 1.0), 8: ("R", -1.0)
            }
            if code_cmd in correspondances:
                self.axe_jog, self.direction_jog = correspondances[code_cmd]
        else:
            correspondances = {
                1: ("J1", 1.0), 2: ("J1", -1.0),
                3: ("J2", 1.0), 4: ("J2", -1.0),
                5: ("J3", 1.0), 6: ("J3", -1.0),
                7: ("J4", 1.0), 8: ("J4", -1.0)
            }
            if code_cmd in correspondances:
                self.axe_jog, self.direction_jog = correspondances[code_cmd]

    def _boucle_physique(self):
        """Met à jour les coordonnées en continu pour simuler un mouvement physique fluide."""
        dt = 0.05
        while self._en_cours:
            time.sleep(dt)

            if self.jog_en_cours:
                pas_cartesien = 80.0 * (self.ratio_jog / 100.0) * dt * self.direction_jog
                pas_articulaire = 40.0 * (self.ratio_jog / 100.0) * dt * self.direction_jog

                if not self.jog_est_articulaire:
                    if self.axe_jog == "X":
                        self.x += pas_cartesien
                    elif self.axe_jog == "Y":
                        self.y += pas_cartesien
                    elif self.axe_jog == "Z":
                        self.z += pas_cartesien
                    elif self.axe_jog == "R":
                        self.r += pas_cartesien
                    self._mettre_a_jour_cinematique_depuis_cartesien()
                else:
                    if self.axe_jog == "J1":
                        self.j1 += pas_articulaire
                    elif self.axe_jog == "J2":
                        self.j2 += pas_articulaire
                    elif self.axe_jog == "J3":
                        self.j3 += pas_articulaire
                    elif self.axe_jog == "J4":
                        self.j4 += pas_articulaire
                    self._mettre_a_jour_cinematique_depuis_articulaire()

            else:
                # Interpolation vers la cible en mode PTP
                vitesse_ptp = 150.0 * dt
                dx = self._cible_x - self.x
                dy = self._cible_y - self.y
                dz = self._cible_z - self.z
                dr = self._cible_r - self.r
                dist = math.sqrt(dx * dx + dy * dy + dz * dz)

                if dist > 0.5:
                    facteur = min(1.0, vitesse_ptp / dist)
                    self.x += dx * facteur
                    self.y += dy * facteur
                    self.z += dz * facteur
                else:
                    self.x = self._cible_x
                    self.y = self._cible_y
                    self.z = self._cible_z

                if abs(dr) > 0.5:
                    self.r += math.copysign(min(abs(dr), 50.0 * dt), dr)
                else:
                    self.r = self._cible_r

                self._mettre_a_jour_cinematique_depuis_cartesien()

    def _mettre_a_jour_cinematique_depuis_cartesien(self):
        # Approximation cinématique inverse pour synchroniser les angles de joints
        rayon = math.sqrt(self.x * self.x + self.y * self.y)
        self.j1 = math.degrees(math.atan2(self.y, self.x))
        self.j4 = self.r - self.j1
        self.j2 = max(-10.0, min(85.0, (rayon - 150.0) * 0.3))
        self.j3 = max(-10.0, min(95.0, (self.z - 20.0) * 0.4))

    def _mettre_a_jour_cinematique_depuis_articulaire(self):
        # Approximation cinématique directe
        angle_rad = math.radians(self.j1)
        r_approx = 150.0 + (self.j2 * 3.3)
        self.x = r_approx * math.cos(angle_rad)
        self.y = r_approx * math.sin(angle_rad)
        self.z = 20.0 + (self.j3 * 2.5)
        self.r = self.j1 + self.j4
        self._cible_x, self._cible_y, self._cible_z, self._cible_r = self.x, self.y, self.z, self.r


# Alias rétrocompatible
MockDobot = DobotSimule

