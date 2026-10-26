"""
app/robot/recalage.py
Procédure propre de recalage HOME en français.
Utilise le module protocole.py et s'intègre avec ControleurDobot ou DobotSimule.
"""

import time
from typing import Dict, Any, Optional, Tuple
from app.robot import protocole


def attendre_fin_mouvement(appareil, attente_min: float = 2.0, stabilite_requise: float = 1.5, delai_max: float = 30.0) -> bool:
    """Attend que la pose du bras se stabilise."""
    time.sleep(attente_min)
    temps_debut = time.time()
    derniere_pose = None
    temps_stable = None

    while time.time() - temps_debut < delai_max:
        pose_actuelle = appareil.pose() if hasattr(appareil, 'pose') else None
        if pose_actuelle:
            courante = tuple(round(v, 1) for v in pose_actuelle[:4])
            if courante == derniere_pose:
                if temps_stable is None:
                    temps_stable = time.time()
                elif time.time() - temps_stable >= stabilite_requise:
                    return True
            else:
                derniere_pose = courante
                temps_stable = None
        time.sleep(0.2)
    return False


wait_until_motion_finished = attendre_fin_mouvement


def executer_sequence_recalage(appareil, simulation: bool = False, tolerance: float = 3.0, **kwargs) -> Dict[str, Any]:
    """
    Exécute la séquence de recalage matériel ou simulé :
    1. Lecture de la position HOME cible
    2. Effacement des alarmes
    3. Déclenchement de la calibration
    4. Attente de fin de mouvement
    5. Vérification de la pose atteinte
    """
    # Prise en charge du paramètre anglais 'mock'
    if 'mock' in kwargs:
        simulation = kwargs['mock']

    print("[Recalage] Démarrage du recalage HOME...")

    # 1. Lecture de la position HOME enregistrée
    pos_home = None
    try:
        pos_home = protocole.lire_parametres_home(appareil)
        print(f"[Recalage] HOME mémorisé : X={pos_home[0]:.1f}, Y={pos_home[1]:.1f}, Z={pos_home[2]:.1f}")
    except Exception as e:
        print(f"[Recalage] Avertissement lecture HOME : {e}")
        pos_home = (250.0, 0.0, 50.0, 0.0)

    # 2. Effacement des alarmes
    protocole.effacer_alarmes(appareil)
    time.sleep(0.3)

    # 3. Déclenchement du recalage
    protocole.declencher_commande_recalage(appareil)

    # 4. Attente de stabilisation
    if simulation:
        time.sleep(1.5)  # En simulation, le recalage prend 1.5s
        termine = True
    else:
        termine = attendre_fin_mouvement(appareil, attente_min=3.0, stabilite_requise=2.0, delai_max=35.0)

    # 5. Contrôle de la pose finale
    pose_finale = appareil.pose() if hasattr(appareil, 'pose') else None
    succes = bool(pose_finale)

    if pose_finale and pos_home:
        dx = abs(pose_finale[0] - pos_home[0])
        dy = abs(pose_finale[1] - pos_home[1])
        dz = abs(pose_finale[2] - pos_home[2])
        succes = max(dx, dy, dz) <= tolerance
        message = f"Recalage réussi (écart max: {max(dx, dy, dz):.1f} mm)" if succes else "Recalage terminé avec écart supérieur à tolérance."
    else:
        message = "Recalage effectué."

    print(f"[Recalage] Résultat : {message}")
    return {
        "ok": succes,
        "message": message,
        "pose": pose_finale
    }


run_homing_sequence = executer_sequence_recalage

