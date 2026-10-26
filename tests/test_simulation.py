"""
tests/test_simulation.py
Tests unitaires du contrôleur simulé DobotSimule et de ControleurDobot en mode simulation en français.
"""

import time
from app.robot.simulation import DobotSimule
from app.robot.controleur import ControleurDobot


def test_dobot_simule_de_base():
    robot = DobotSimule()
    assert robot.connecte is True

    pose = robot.obtenir_pose()
    assert len(pose) == 8
    assert pose[0] == 250.0

    # Déplacement PTP
    robot.deplacer_vers(200.0, 50.0, 30.0, 0.0, attente=True)
    p2 = robot.obtenir_pose()
    assert abs(p2[0] - 200.0) < 1.0
    assert abs(p2[1] - 50.0) < 1.0

    # Effecteurs
    robot.aspirer(True)
    assert robot.ventouse_active is True
    robot.pincer(True)
    assert robot.pince_active is True

    robot.fermer()


def test_controleur_dobot_jog_simule():
    controleur = ControleurDobot(simulation=True, delai_inactivite_jog=0.4)
    controleur.initialiser()

    statut = controleur.obtenir_statut()
    assert statut["simulation"] is True
    assert statut["ok"] is True

    # Début JOG
    res = controleur.demarrer_jog("X", 1.0)
    assert res["jog_actif"] is True

    # Battement léger (quasi instantané, < 100ms)
    t0 = time.time()
    for _ in range(5):
        controleur.battement_jog()
    dt = time.time() - t0
    assert dt < 0.1

    # Arrêt JOG
    res_stop = controleur.arreter_jog()
    assert res_stop["jog_actif"] is False

    # Arrêt d'urgence
    res_arret = controleur.arret_urgence()
    assert res_arret["ok"] is True

