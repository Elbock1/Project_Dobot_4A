"""
tests/test_api.py
Tests d'intégration des endpoints Flask et de l'API REST en mode simulation (DobotSimule / Mock).
Vérifie la prise en charge des routes françaises et la compatibilité anglaise.
"""

import pytest
from app.main import creer_application, create_app


@pytest.fixture
def client():
    # Force le mode mock/simulation pour les tests
    import os
    os.environ["MOCK_ROBOT"] = "true"
    app = creer_application()
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_html_views(client):
    r_index = client.get("/")
    assert r_index.status_code == 200
    assert b"Plateforme Multimodale Dobot" in r_index.data

    # Vues en anglais
    r_manual = client.get("/manual")
    assert r_manual.status_code == 200
    assert b"Pilotage Direct du Bras" in r_manual.data

    r_text = client.get("/text")
    assert r_text.status_code == 200

    # Vues en français
    r_manuel = client.get("/manuel")
    assert r_manuel.status_code == 200
    assert b"Pilotage Direct du Bras" in r_manuel.data

    r_texte = client.get("/texte")
    assert r_texte.status_code == 200


def test_api_status(client):
    res_en = client.get("/api/status")
    assert res_en.status_code == 200
    data_en = res_en.get_json()
    assert data_en["ok"] is True
    assert "x" in data_en and "y" in data_en and "z" in data_en
    assert "mock" in data_en

    res_fr = client.get("/api/statut")
    assert res_fr.status_code == 200
    data_fr = res_fr.get_json()
    assert data_fr["ok"] is True
    assert "simulation" in data_fr
    assert "occupe" in data_fr


def test_api_jog_cycle(client):
    # Démarrage JOG en anglais
    r_start = client.post("/api/jog/start", json={"axis": "Y", "dir": 1})
    assert r_start.status_code == 200
    assert r_start.get_json()["jog_active"] is True

    # Battement JOG
    r_beat = client.post("/api/jog/beat")
    assert r_beat.status_code == 200

    # Arrêt JOG
    r_stop = client.post("/api/jog/stop")
    assert r_stop.status_code == 200
    assert r_stop.get_json()["jog_active"] is False

    # Cycle JOG en français
    r_start_fr = client.post("/api/jog/demarrer", json={"axe": "X", "direction": 1})
    assert r_start_fr.status_code == 200
    assert r_start_fr.get_json()["jog_actif"] is True

    r_beat_fr = client.post("/api/jog/battement")
    assert r_beat_fr.status_code == 200

    r_stop_fr = client.post("/api/jog/arreter")
    assert r_stop_fr.status_code == 200
    assert r_stop_fr.get_json()["jog_actif"] is False


def test_api_effector_and_speed(client):
    r_speed = client.post("/api/vitesse", json={"ratio": 80})
    assert r_speed.status_code == 200
    assert r_speed.get_json()["speed_ratio"] == 80.0

    r_eff = client.post("/api/effecteur", json={"outil": "pince", "actif": True})
    assert r_eff.status_code == 200
    assert r_eff.get_json()["pince"] is True
    assert r_eff.get_json()["gripper"] is True


def test_api_command_unified(client):
    # Commande valide en anglais
    valid_payload = {
        "action": "move_to",
        "x": 200.0,
        "y": 10.0,
        "z": 40.0,
        "r": 0.0
    }
    r_cmd = client.post("/api/command", json=valid_payload)
    assert r_cmd.status_code == 200
    d = r_cmd.get_json()
    assert d["ok"] is True
    assert d["command_json"]["action"] == "move_to"

    # Commande valide en français
    payload_fr = {
        "action": "deplacer_vers",
        "x": 220.0,
        "y": 0.0,
        "z": 30.0,
        "r": 0.0
    }
    r_cmd_fr = client.post("/api/commande", json=payload_fr)
    assert r_cmd_fr.status_code == 200
    d_fr = r_cmd_fr.get_json()
    assert d_fr["ok"] is True

    # Commande invalide (action inconnue)
    r_inv = client.post("/api/command", json={"action": "voler_dans_le_ciel"})
    assert r_inv.status_code == 400


def test_api_text_pipeline(client):
    # Ordre compréhensible en anglais
    res = client.post("/api/text", json={"command": "monte de 20"})
    assert res.status_code == 200
    d = res.get_json()
    assert d["ok"] is True
    assert d["command_json"]["action"] == "move_rel"
    assert d["command_json"]["axis"] == "Z"
    assert d["command_json"]["step"] == 20.0

    # Ordre compréhensible sur endpoint français
    res_fr = client.post("/api/texte", json={"commande": "descends de 10"})
    assert res_fr.status_code == 200
    d_fr = res_fr.get_json()
    assert d_fr["ok"] is True
    assert d_fr["commande_json"]["axe"] == "Z"
    assert d_fr["commande_json"]["pas"] == -10.0

    # Ordre inintelligible
    res_bad = client.post("/api/texte", json={"commande": "blabla incompréhensible"})
    assert res_bad.status_code == 422


def test_api_emergency_stop(client):
    res_en = client.post("/api/stop")
    assert res_en.status_code == 200
    assert res_en.get_json()["ok"] is True

    res_fr = client.post("/api/arret")
    assert res_fr.status_code == 200
    assert res_fr.get_json()["ok"] is True
