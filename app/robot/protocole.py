"""
app/robot/protocole.py
Extraction propre du protocole Dobot Magician en français.
Gère les identifiants de commandes, le packaging structuré des trames et l'acquittement.
"""

import struct
from typing import Optional, Tuple, Sequence
from pydobot.message import Message

# --- Identifiants du Protocole Dobot (en français) ---
ID_NUMERO_SERIE = 0
ID_NOM_APPAREIL = 1
ID_VERSION_APPAREIL = 2

# Alarmes
ID_ETAT_ALARMES = 20        # Lecture (rw=0) des 32 octets de bits d'alarmes
ID_EFFACER_ALARMES = 21     # Effacement (rw=1) des alarmes actives

# Recalage / Homing
ID_PARAMETRES_HOME = 30     # Lecture/écriture des coordonnées HOME (4 floats)
ID_COMMANDE_HOME = 31       # Déclenchement de la procédure de homing

# Outils d'extrémité (effecteurs)
ID_VENTOUSE = 62            # Ventouse pneumatique
ID_PINCE = 63               # Pince préhensile

# JOG (pilotage pas-à-pas continu)
ID_JOG_PARAMETRES_ARTICULAIRES = 70    # Vitesses et accélérations articulaires (8 floats)
ID_JOG_PARAMETRES_COORDONNEES = 71     # Vitesses et accélérations cartésiennes (8 floats)
ID_JOG_PARAMETRES_COMMUNS = 72         # Ratios de vitesse/accélération JOG (2 floats)
ID_COMMANDE_JOG = 73                   # Commande JOG instantanée (2 octets: est_articulaire, code_cmd)

# File d'attente (Queue)
ID_DEMARRER_FILE = 240      # Démarrage de l'exécution de la file
ID_ARRETER_FILE = 241       # Arrêt temporaire
ID_ARRET_FORCE_FILE = 242   # Arrêt forcé immédiat
ID_VIDER_FILE = 245         # Vidage de la file d'attente

# Correspondances historiques en anglais (rétrocompatibilité)
ID_DEVICE_SN = ID_NUMERO_SERIE
ID_DEVICE_NAME = ID_NOM_APPAREIL
ID_DEVICE_VERSION = ID_VERSION_APPAREIL
ID_ALARMS_STATE = ID_ETAT_ALARMES
ID_CLEAR_ALARMS = ID_EFFACER_ALARMES
ID_HOME_PARAMS = ID_PARAMETRES_HOME
ID_HOME_CMD = ID_COMMANDE_HOME
ID_SUCTION_CUP = ID_VENTOUSE
ID_GRIPPER = ID_PINCE
ID_JOG_JOINT_PARAMS = ID_JOG_PARAMETRES_ARTICULAIRES
ID_JOG_COORD_PARAMS = ID_JOG_PARAMETRES_COORDONNEES
ID_JOG_COMMON_PARAMS = ID_JOG_PARAMETRES_COMMUNS
ID_JOG_CMD = ID_COMMANDE_JOG
ID_QUEUE_START = ID_DEMARRER_FILE
ID_QUEUE_STOP = ID_ARRETER_FILE
ID_QUEUE_FORCE_STOP = ID_ARRET_FORCE_FILE
ID_QUEUE_CLEAR = ID_VIDER_FILE

# Correspondance des commandes JOG cartésiennes et articulaires
# (+0 pour sens positif, +1 pour sens négatif)
BASE_JOG_CARTESIEN = {
    "X": 1,   # 1 = X+, 2 = X-
    "Y": 3,   # 3 = Y+, 4 = Y-
    "Z": 5,   # 5 = Z+, 6 = Z-
    "R": 7    # 7 = R+, 8 = R-
}
JOG_CARTESIAN_BASE = BASE_JOG_CARTESIEN

BASE_JOG_ARTICULAIRE = {
    "J1": 1,  # 1 = J1+, 2 = J1-
    "J2": 3,  # 3 = J2+, 4 = J2-
    "J3": 5,  # 5 = J3+, 6 = J3-
    "J4": 7   # 7 = J4+, 8 = J4-
}
JOG_JOINT_BASE = BASE_JOG_ARTICULAIRE


def envoyer_commande_brute(appareil, id_cmd: int, lecture_ecriture: bool, en_file: bool = False,
                           parametres: Optional[Sequence[int] | bytes] = None) -> Optional[Message]:
    """
    Envoie une trame de commande brute au contrôleur Dobot et retourne la réponse.
    """
    if appareil is None:
        raise ConnectionError("Périphérique Dobot non connecté.")

    msg = Message()
    msg.id = id_cmd
    msg.rw = lecture_ecriture
    msg.is_queued = en_file
    if parametres is not None:
        msg.params = bytearray(parametres)

    # pydobot implémente _send_command
    return appareil._send_command(msg)


send_raw_command = envoyer_commande_brute


def verifier_alarmes(appareil) -> bool:
    """Retourne True si au moins un bit d'alarme est actif."""
    try:
        reponse = envoyer_commande_brute(appareil, ID_ETAT_ALARMES, lecture_ecriture=False)
        if reponse and reponse.params:
            return any(b != 0 for b in reponse.params)
    except Exception:
        pass
    return False


check_alarms = verifier_alarmes


def effacer_alarmes(appareil) -> None:
    """Efface les alarmes actives (ID 21)."""
    try:
        envoyer_commande_brute(appareil, ID_EFFACER_ALARMES, lecture_ecriture=True)
    except Exception as e:
        print(f"[Protocole] Erreur effacement alarmes : {e}")


clear_alarms = effacer_alarmes


def arreter_et_vider_file(appareil) -> None:
    """
    Arrêt forcé immédiat + purge de la file + réactivation de l'exécuteur de file.
    Note : ID_DEMARRER_FILE est indispensable après un arrêt forcé pour accepter de nouveaux mouvements.
    """
    try:
        envoyer_commande_brute(appareil, ID_ARRET_FORCE_FILE, lecture_ecriture=True)
        envoyer_commande_brute(appareil, ID_VIDER_FILE, lecture_ecriture=True)
        envoyer_commande_brute(appareil, ID_DEMARRER_FILE, lecture_ecriture=True)
    except Exception as e:
        print(f"[Protocole] Erreur purge et redémarrage file : {e}")


stop_and_clear_queue = arreter_et_vider_file


def lire_parametres_home(appareil) -> Tuple[float, float, float, float]:
    """Lit les coordonnées X, Y, Z, R de HOME enregistrées dans l'EEPROM du contrôleur."""
    reponse = envoyer_commande_brute(appareil, ID_PARAMETRES_HOME, lecture_ecriture=False)
    if reponse is None or not reponse.params or len(reponse.params) < 16:
        raise RuntimeError("Impossible de lire les paramètres HOME du Dobot.")
    donnees = bytes(reponse.params[:16])
    return struct.unpack('<4f', donnees)


read_home_params = lire_parametres_home


def declencher_commande_recalage(appareil) -> None:
    """Déclenche la commande de homing matériel."""
    if hasattr(appareil, 'home'):
        appareil.home()
    else:
        envoyer_commande_brute(appareil, ID_COMMANDE_HOME, lecture_ecriture=True, en_file=True, parametres=[0, 0, 0, 0])


trigger_homing_command = declencher_commande_recalage


def configurer_dynamique_jog(appareil, vitesse: float, acceleration: float, ratio: float) -> None:
    """Configure les paramètres de dynamique du mode JOG (vitesses, accélérations et ratio global)."""
    params_8f = struct.pack(
        '<8f',
        vitesse, vitesse, vitesse, vitesse,
        acceleration, acceleration, acceleration, acceleration
    )
    envoyer_commande_brute(appareil, ID_JOG_PARAMETRES_COORDONNEES, lecture_ecriture=True, parametres=params_8f)
    envoyer_commande_brute(appareil, ID_JOG_PARAMETRES_ARTICULAIRES, lecture_ecriture=True, parametres=params_8f)

    ratio_borne = max(1.0, min(100.0, float(ratio)))
    params_ratio = struct.pack('<2f', ratio_borne, ratio_borne)
    envoyer_commande_brute(appareil, ID_JOG_PARAMETRES_COMMUNS, lecture_ecriture=True, parametres=params_ratio)


configure_jog_dynamics = configurer_dynamique_jog


def regler_ratio_jog(appareil, ratio: float) -> None:
    """Met à jour le pourcentage de vitesse JOG en temps réel."""
    ratio_borne = max(1.0, min(100.0, float(ratio)))
    parametres = struct.pack('<2f', ratio_borne, ratio_borne)
    envoyer_commande_brute(appareil, ID_JOG_PARAMETRES_COMMUNS, lecture_ecriture=True, parametres=parametres)


set_jog_ratio = regler_ratio_jog


def envoyer_pas_jog(appareil, est_articulaire: bool, code_cmd: int) -> None:
    """
    Envoie l'ordre de mouvement JOG.
    code_cmd = 0 pour STOP ; 1..8 pour les directions (+/-).
    """
    parametres = [1 if est_articulaire else 0, int(code_cmd)]
    envoyer_commande_brute(appareil, ID_COMMANDE_JOG, lecture_ecriture=True, parametres=parametres)


send_jog_step = envoyer_pas_jog

