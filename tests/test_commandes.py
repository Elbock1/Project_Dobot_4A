"""
tests/test_commandes.py
Validation des schémas Pydantic du contrat commun et du parser à règles NLU en français.
"""

import pytest
from app.core.commandes import (
    analyser_dictionnaire_commande,
    analyser_regles_texte,
    CommandeDeplacerVers,
    CommandeDeplacerRelatif,
    CommandePrendreDeposer,
    CommandeTrierTout,
    CommandePince,
    CommandeVentouse,
    CommandeRecalage,
    CommandeArret,
    SpecificationObjet
)


def test_analyse_deplacer_vers():
    donnees = {"action": "deplacer_vers", "x": 180.5, "y": 20.0, "z": 45.0, "r": 10.0}
    cmd = analyser_dictionnaire_commande(donnees)
    assert isinstance(cmd, CommandeDeplacerVers)
    assert cmd.x == 180.5
    assert cmd.y == 20.0
    assert cmd.z == 45.0
    assert cmd.r == 10.0


def test_analyse_prendre_deposer():
    donnees = {
        "action": "prendre_deposer",
        "objet": {"forme": "cube", "couleur": "rouge"},
        "destination": "bac_1"
    }
    cmd = analyser_dictionnaire_commande(donnees)
    assert isinstance(cmd, CommandePrendreDeposer)
    assert cmd.objet.forme == "cube"
    assert cmd.objet.couleur == "rouge"
    assert cmd.destination == "bac_1"


def test_analyse_trier_tout():
    cmd = analyser_dictionnaire_commande({"action": "trier_tout", "regle": "par_couleur"})
    assert isinstance(cmd, CommandeTrierTout)
    assert cmd.regle in ("par_couleur", "by_color")


def test_analyse_effecteurs():
    cmd_pince = analyser_dictionnaire_commande({"action": "pince", "activer": True})
    assert isinstance(cmd_pince, CommandePince)
    assert cmd_pince.activer is True

    cmd_ventouse = analyser_dictionnaire_commande({"action": "ventouse", "activer": False})
    assert isinstance(cmd_ventouse, CommandeVentouse)
    assert cmd_ventouse.activer is False


def test_analyse_regles_texte_francais():
    # Arrêt
    assert isinstance(analyser_regles_texte("stop d'urgence"), CommandeArret)
    assert isinstance(analyser_regles_texte("arret"), CommandeArret)
    assert isinstance(analyser_regles_texte("arrête"), CommandeArret)

    # Recalage
    assert isinstance(analyser_regles_texte("recalage du bras"), CommandeRecalage)
    assert isinstance(analyser_regles_texte("initialise"), CommandeRecalage)

    # Effecteurs
    pince_fermee = analyser_regles_texte("ferme la pince")
    assert isinstance(pince_fermee, CommandePince) and pince_fermee.activer is True

    pince_ouverte = analyser_regles_texte("ouvre la pince")
    assert isinstance(pince_ouverte, CommandePince) and pince_ouverte.activer is False

    ventouse_on = analyser_regles_texte("active la ventouse")
    assert isinstance(ventouse_on, CommandeVentouse) and ventouse_on.activer is True

    # Déplacement absolu
    depl = analyser_regles_texte("va à X 150 Y 50 Z 20")
    assert isinstance(depl, CommandeDeplacerVers)
    assert depl.x == 150.0 and depl.y == 50.0 and depl.z == 20.0

    # Déplacement relatif
    m_rel = analyser_regles_texte("monte de 25")
    assert isinstance(m_rel, CommandeDeplacerRelatif)
    assert m_rel.axe == "Z" and m_rel.pas == 25.0

    # Tri
    tri_cmd = analyser_regles_texte("trie tout par couleur")
    assert isinstance(tri_cmd, CommandeTrierTout)
    assert tri_cmd.regle in ("par_couleur", "by_color")


def test_commande_invalide():
    with pytest.raises(Exception):
        analyser_dictionnaire_commande({"action": "action_inconnue_123"})

