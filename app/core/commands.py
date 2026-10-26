"""
app/core/commands.py
Module de compatibilité redirigeant vers app/core/commandes.py.
Conserve la compatibilité avec tout code important les noms historiques en anglais.
"""

from app.core.commandes import (
    SpecificationObjet,
    ObjectSpec,
    CommandeDeplacerVers,
    MoveToCommand,
    CommandeDeplacerRelatif,
    MoveRelCommand,
    CommandeJog,
    JogCommand,
    CommandePrendreDeposer,
    PickPlaceCommand,
    CommandeTrierTout,
    SortAllCommand,
    CommandePince,
    GripperCommand,
    CommandeVentouse,
    SuctionCommand,
    CommandeRecalage,
    HomeCommand,
    CommandeArret,
    StopCommand,
    CommandeClarification,
    ClarifyCommand,
    TypeCommande,
    CommandType,
    analyser_dictionnaire_commande,
    parse_command_dict,
    analyser_regles_texte,
    parse_text_rules,
)
