"""
app/core/commandes.py
Schémas Pydantic du contrat commun de commande robotique en français.
Tous les modes d'interaction (manette, texte, voix, gestes, vision) produisent
l'une de ces structures validées avant toute exécution matérielle.
"""

from typing import Literal, Optional, Union, Dict, Any
import re
from pydantic import BaseModel, Field, ConfigDict


class SpecificationObjet(BaseModel):
    """Spécification d'un objet cible (pour prise/dépose ou tri)."""
    model_config = ConfigDict(populate_by_name=True)

    forme: Optional[str] = Field(None, alias="shape", description="Forme géométrique (ex: cube, cylindre, pyramide)")
    couleur: Optional[str] = Field(None, alias="color", description="Couleur (ex: rouge, vert, bleu, jaune)")

    @property
    def shape(self) -> Optional[str]:
        return self.forme

    @shape.setter
    def shape(self, valeur: Optional[str]):
        self.forme = valeur

    @property
    def color(self) -> Optional[str]:
        return self.couleur

    @color.setter
    def color(self, valeur: Optional[str]):
        self.couleur = valeur


# Alias de compatibilité
ObjectSpec = SpecificationObjet


# --- Modèles de Commandes Normalisées ---

class CommandeDeplacerVers(BaseModel):
    """Commande de déplacement cartésien absolu vers des coordonnées (X, Y, Z, R)."""
    model_config = ConfigDict(populate_by_name=True)

    action: Literal["move_to", "deplacer_vers"] = "move_to"
    x: float = Field(..., description="Coordonnée X cartésienne en mm")
    y: float = Field(..., description="Coordonnée Y cartésienne en mm")
    z: float = Field(..., description="Coordonnée Z cartésienne en mm")
    r: float = Field(0.0, description="Orientation angulaire R en degrés")


class CommandeDeplacerRelatif(BaseModel):
    """Commande de déplacement pas-à-pas relatif selon un axe cartésien."""
    model_config = ConfigDict(populate_by_name=True)

    action: Literal["move_rel", "deplacer_relatif"] = "move_rel"
    axe: Literal["X", "Y", "Z", "R"] = Field(..., alias="axis", description="Axe relatif")
    pas: float = Field(..., alias="step", description="Pas en mm (ou degrés pour R)")

    @property
    def axis(self) -> str:
        return self.axe

    @axis.setter
    def axis(self, valeur: str):
        self.axe = valeur

    @property
    def step(self) -> float:
        return self.pas

    @step.setter
    def step(self, valeur: float):
        self.pas = valeur


class CommandeJog(BaseModel):
    """Commande de déplacement continu (JOG)."""
    model_config = ConfigDict(populate_by_name=True)

    action: Literal["jog"] = "jog"
    axe: str = Field(..., alias="axis", description="Axe cartésien ou articulaire (X, Y, Z, R, J1, J2, J3, J4)")
    direction: float = Field(1.0, description="Sens de déplacement (+1 ou -1)")

    @property
    def axis(self) -> str:
        return self.axe

    @axis.setter
    def axis(self, valeur: str):
        self.axe = valeur


class CommandePrendreDeposer(BaseModel):
    """Commande de saisie et dépose d'un objet vers un bac de destination."""
    model_config = ConfigDict(populate_by_name=True)

    action: Literal["pick_place", "prendre_deposer"] = "pick_place"
    objet: SpecificationObjet = Field(..., alias="object", description="Objet à saisir")
    destination: str = Field(..., description="Identifiant du bac de dépose (ex: bac_1, bac_2)")

    @property
    def object(self) -> SpecificationObjet:
        return self.objet

    @object.setter
    def object(self, valeur: SpecificationObjet):
        self.objet = valeur


class CommandeTrierTout(BaseModel):
    """Commande de tri automatique de tous les objets selon une règle."""
    model_config = ConfigDict(populate_by_name=True)

    action: Literal["sort_all", "trier_tout"] = "sort_all"
    regle: Literal["by_color", "by_shape", "par_couleur", "par_forme"] = Field(
        "by_color", alias="rule", description="Règle de tri"
    )

    @property
    def rule(self) -> str:
        if self.regle in ("by_color", "par_couleur"):
            return "by_color"
        return "by_shape"

    @rule.setter
    def rule(self, valeur: str):
        self.regle = valeur


class CommandePince(BaseModel):
    """Commande d'actionnement de la pince préhensile."""
    model_config = ConfigDict(populate_by_name=True)

    action: Literal["gripper", "pince"] = "gripper"
    activer: bool = Field(..., alias="on", description="True = fermer la pince, False = ouvrir")

    @property
    def on(self) -> bool:
        return self.activer

    @on.setter
    def on(self, valeur: bool):
        self.activer = valeur


class CommandeVentouse(BaseModel):
    """Commande d'actionnement de la ventouse pneumatique."""
    model_config = ConfigDict(populate_by_name=True)

    action: Literal["suction", "ventouse"] = "suction"
    activer: bool = Field(..., alias="on", description="True = activer l'aspiration, False = relâcher")

    @property
    def on(self) -> bool:
        return self.activer

    @on.setter
    def on(self, valeur: bool):
        self.activer = valeur


class CommandeRecalage(BaseModel):
    """Commande de retour à l'origine (recalage / homing)."""
    model_config = ConfigDict(populate_by_name=True)

    action: Literal["home", "recalage"] = "home"


class CommandeArret(BaseModel):
    """Commande d'arrêt d'urgence prioritaire."""
    model_config = ConfigDict(populate_by_name=True)

    action: Literal["stop", "arret"] = "stop"


class CommandeClarification(BaseModel):
    """Demande d'éclaircissement à l'utilisateur."""
    model_config = ConfigDict(populate_by_name=True)

    action: Literal["clarify", "clarifier"] = "clarify"
    question: str = Field(..., description="Demande de précision posée à l'utilisateur")


# Type Union regroupant toutes les commandes supportées
TypeCommande = Union[
    CommandeDeplacerVers,
    CommandeDeplacerRelatif,
    CommandeJog,
    CommandePrendreDeposer,
    CommandeTrierTout,
    CommandePince,
    CommandeVentouse,
    CommandeRecalage,
    CommandeArret,
    CommandeClarification
]


# Alias de compatibilité anglais
MoveToCommand = CommandeDeplacerVers
MoveRelCommand = CommandeDeplacerRelatif
JogCommand = CommandeJog
PickPlaceCommand = CommandePrendreDeposer
SortAllCommand = CommandeTrierTout
GripperCommand = CommandePince
SuctionCommand = CommandeVentouse
HomeCommand = CommandeRecalage
StopCommand = CommandeArret
ClarifyCommand = CommandeClarification
CommandType = TypeCommande


def analyser_dictionnaire_commande(donnees: Dict[str, Any]) -> TypeCommande:
    """
    Parse et valide un dictionnaire JSON brut vers le modèle Pydantic approprié.
    Supporte les actions en français et en anglais.
    """
    action = donnees.get("action")
    correspondances = {
        # Français
        "deplacer_vers": CommandeDeplacerVers,
        "deplacer_relatif": CommandeDeplacerRelatif,
        "jog": CommandeJog,
        "prendre_deposer": CommandePrendreDeposer,
        "trier_tout": CommandeTrierTout,
        "pince": CommandePince,
        "ventouse": CommandeVentouse,
        "recalage": CommandeRecalage,
        "arret": CommandeArret,
        "clarifier": CommandeClarification,
        # Anglais (rétrocompatibilité)
        "move_to": CommandeDeplacerVers,
        "move_rel": CommandeDeplacerRelatif,
        "pick_place": CommandePrendreDeposer,
        "sort_all": CommandeTrierTout,
        "gripper": CommandePince,
        "suction": CommandeVentouse,
        "home": CommandeRecalage,
        "stop": CommandeArret,
        "clarify": CommandeClarification,
    }
    classe_commande = correspondances.get(action)
    if not classe_commande:
        raise ValueError(f"Action inconnue ou non supportée : '{action}'")
    return classe_commande(**donnees)


# Alias rétrocompatible
parse_command_dict = analyser_dictionnaire_commande


# ------------------------------------------------------------------ PARSER À RÈGLES (Texte vers JSON)

def analyser_regles_texte(texte: str) -> Optional[TypeCommande]:
    """
    Parser à règles déterministe (Regex) pour les ordres textuels simples en français et anglais.
    Fournit une exécution instantanée, fiable et hors-ligne.
    """
    t = texte.strip().lower()

    # Arrêt / Urgence
    if re.search(r"\b(stop|arret|arrête|urgence|bloque)\b", t):
        return CommandeArret()

    # Home / Recalage
    if re.search(r"\b(home|recalage|recale|origine|initialise)\b", t):
        return CommandeRecalage()

    # Pince
    if re.search(r"\b(ferme|fermer)\b.*\b(pince|gripper)\b", t) or re.search(r"\bpince\s+(on|1|ferme)\b", t):
        return CommandePince(activer=True)
    if re.search(r"\b(ouvre|ouvrir|relache|relacher)\b.*\b(pince|gripper)\b", t) or re.search(r"\bpince\s+(off|0|ouvre)\b", t):
        return CommandePince(activer=False)

    # Ventouse
    if re.search(r"\b(active|activer|aspire|aspirer|allume)\b.*\b(ventouse|suction)\b", t) or re.search(r"\bventouse\s+(on|1)\b", t):
        return CommandeVentouse(activer=True)
    if re.search(r"\b(arrete|coupe|desactive|relache|eteins)\b.*\b(ventouse|suction)\b", t) or re.search(r"\bventouse\s+(off|0)\b", t):
        return CommandeVentouse(activer=False)

    # Déplacement absolu : ex "va à X 150 Y 50 Z 20" ou "move to x=150 y=50 z=20"
    correspondance_abs = re.search(r"x\s*[:=]?\s*([+-]?\d+(?:\.\d+)?)\s*y\s*[:=]?\s*([+-]?\d+(?:\.\d+)?)\s*z\s*[:=]?\s*([+-]?\d+(?:\.\d+)?)", t)
    if correspondance_abs:
        x, y, z = correspondance_abs.groups()
        return CommandeDeplacerVers(x=float(x), y=float(y), z=float(z), r=0.0)

    # Déplacement relatif : ex "monte de 20", "descends de 15", "avance de 30"
    m_monte = re.search(r"\b(monte|haut)\b.*?(?:de\s+)?([+-]?\d+(?:\.\d+)?)", t)
    if m_monte:
        return CommandeDeplacerRelatif(axe="Z", pas=abs(float(m_monte.group(2))))
    m_descend = re.search(r"\b(descends|descend|bas)\b.*?(?:de\s+)?([+-]?\d+(?:\.\d+)?)", t)
    if m_descend:
        return CommandeDeplacerRelatif(axe="Z", pas=-abs(float(m_descend.group(2))))

    # Tri global : "trie tout par couleur", "trie par forme"
    if "trie" in t or "sort" in t:
        if "forme" in t or "shape" in t:
            return CommandeTrierTout(regle="by_shape")
        return CommandeTrierTout(regle="by_color")

    # Prise & dépôt : "mets le cube rouge dans le bac 1"
    m_prise = re.search(r"\b(prends?|mets?|place|deplace)\b.*(cube|cylindre|pyramide)?.*(rouge|vert|bleu|jaune)?.*(bac\s*[_0-9]+)", t)
    if m_prise:
        _, forme, couleur, nom_bac = m_prise.groups()
        destination = nom_bac.replace(" ", "_")
        return CommandePrendreDeposer(
            objet=SpecificationObjet(forme=forme or "cube", couleur=couleur or "rouge"),
            destination=destination
        )

    return None


# Alias rétrocompatible
parse_text_rules = analyser_regles_texte

