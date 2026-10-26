"""
tests/test_securite.py
Tests des règles de sécurité géométrique et de validation d'enveloppe de travail en français.
"""

from app.core.securite import VerificateurSecurite
from app.core.commandes import CommandeDeplacerVers, CommandeDeplacerRelatif


def test_securite_dans_les_limites():
    verificateur = VerificateurSecurite({
        "x_min": 100.0, "x_max": 320.0,
        "y_min": -200.0, "y_max": 200.0,
        "z_min": -50.0, "z_max": 150.0
    })

    cmd = CommandeDeplacerVers(x=200.0, y=0.0, z=50.0)
    valide, message = verificateur.valider_commande(cmd, {})
    assert valide is True


def test_securite_hors_limites_x():
    verificateur = VerificateurSecurite({"x_min": 100.0, "x_max": 320.0})

    # X trop loin
    cmd_trop_loin = CommandeDeplacerVers(x=450.0, y=0.0, z=50.0)
    valide, message = verificateur.valider_commande(cmd_trop_loin, {})
    assert valide is False
    assert "hors limites" in message

    # X trop proche de la base
    cmd_trop_proche = CommandeDeplacerVers(x=50.0, y=0.0, z=50.0)
    valide, message = verificateur.valider_commande(cmd_trop_proche, {})
    assert valide is False


def test_securite_hors_limites_z():
    verificateur = VerificateurSecurite({"z_min": -50.0, "z_max": 150.0})

    cmd_sous_sol = CommandeDeplacerVers(x=200.0, y=0.0, z=-90.0)
    valide, message = verificateur.valider_commande(cmd_sous_sol, {})
    assert valide is False
    assert "Axe Z hors limites" in message


def test_securite_deplacement_relatif():
    verificateur = VerificateurSecurite({"z_min": -50.0, "z_max": 150.0})
    pose_courante = {"x": 200.0, "y": 0.0, "z": 140.0}

    # Monter de 20 mm dépasse z_max (140 + 20 = 160 > 150)
    cmd_rel = CommandeDeplacerRelatif(axe="Z", pas=20.0)
    valide, message = verificateur.valider_commande(cmd_rel, pose_courante)
    assert valide is False
    assert "Axe Z hors limites" in message

