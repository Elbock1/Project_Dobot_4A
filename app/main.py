"""
app/main.py
Point d'entrée principal du serveur Flask Dobot AI Multimodale en français.
Initialise la configuration, le contrôleur robotique (réel ou simulé),
la sécurité, la file de tâches et le serveur web.
"""

import os
import sys
from pathlib import Path
import yaml
from flask import Flask

# Assure que la racine du projet est dans sys.path
RACINE_PROJET = Path(__file__).resolve().parent.parent
PROJECT_ROOT = RACINE_PROJET
if str(RACINE_PROJET) not in sys.path:
    sys.path.insert(0, str(RACINE_PROJET))

from app.robot.controleur import ControleurDobot, DobotController
from app.core.securite import VerificateurSecurite, SafetyChecker
from app.core.executeur import ExecuteurCommandes, CommandExecutor
from app.api.routes import creer_routes, create_routes


def charger_configuration() -> dict:
    """Charge la configuration depuis config/settings.yaml avec surcharge d'environnement."""
    chemin_config = RACINE_PROJET / "config" / "settings.yaml"
    cfg = {}
    if chemin_config.exists():
        with open(chemin_config, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

    # Surcharges optionnelles par variables d'environnement
    robot_cfg = cfg.setdefault("robot", {})
    if "DOBOT_PORT" in os.environ:
        robot_cfg["port"] = os.environ["DOBOT_PORT"]
    if "MOCK_ROBOT" in os.environ:
        robot_cfg["mock"] = os.environ["MOCK_ROBOT"].lower() in ("true", "1", "yes")
    if "SIMULATION_ROBOT" in os.environ:
        robot_cfg["simulation"] = os.environ["SIMULATION_ROBOT"].lower() in ("true", "1", "yes")

    return cfg


load_config = charger_configuration


def creer_application() -> Flask:
    """Factory de création de l'application Flask."""
    cfg = charger_configuration()

    # Chemins des templates et fichiers statiques
    dossier_templates = RACINE_PROJET / "app" / "web" / "templates"
    dossier_statique = RACINE_PROJET / "app" / "web" / "static"

    app = Flask(
        __name__,
        template_folder=str(dossier_templates),
        static_folder=str(dossier_statique)
    )

    # Initialisation des composants cœurs en français
    robot_cfg = cfg.get("robot", {})
    safety_cfg = cfg.get("securite") or cfg.get("safety", {})

    mode_sim = robot_cfg.get("simulation") if "simulation" in robot_cfg else robot_cfg.get("mock", False)
    controleur = ControleurDobot(
        port=robot_cfg.get("port", "COM4"),
        debit_bauds=robot_cfg.get("debit_bauds") or robot_cfg.get("baudrate", 115200),
        simulation=mode_sim,
        delai_inactivite_jog=robot_cfg.get("delai_jog") or robot_cfg.get("jog_timeout", 0.5),
        frequence_telemetrie_hz=robot_cfg.get("frequence_telemetrie_hz") or robot_cfg.get("telemetry_rate_hz", 4.0)
    )
    controleur.initialiser()

    securite = VerificateurSecurite(safety_cfg)
    executeur = ExecuteurCommandes(controleur, securite)

    # Enregistrement des routes
    bp = creer_routes(controleur, executeur, securite)
    app.register_blueprint(bp)

    # Références attachées à l'app (français et rétrocompatibilité anglais)
    app.controleur_dobot = controleur
    app.dobot_controller = controleur
    app.executeur_commandes = executeur
    app.command_executor = executeur
    app.verificateur_securite = securite
    app.safety_checker = securite

    return app


create_app = creer_application


if __name__ == '__main__':
    cfg = charger_configuration()
    serveur_cfg = cfg.get("serveur") or cfg.get("server", {})
    hote = serveur_cfg.get("hote") or serveur_cfg.get("host", "0.0.0.0")
    port = int(serveur_cfg.get("port", 5000))

    application_flask = creer_application()
    print("=" * 60)
    print(f" Dobot AI Multimodale - Serveur démarré sur http://{hote}:{port}")
    print("=" * 60)
    application_flask.run(host=hote, port=port, debug=False, threaded=True)
