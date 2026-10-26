# Architecture du Projet Dobot IA Multimodale

## 1. Vue d'Ensemble
Le système adopte une architecture en couches étanches avec **un point d'étranglement sécuritaire unique** :

```
Clients Web (Navigateurs, Mobile, PC)
  │ (REST, JSON, HTTPS)
  ▼
API Flask (app/api/routes.py)
  ├── Route directe /api/commande (ou /api/command)
  └── Route texte /api/texte (ou /api/text) ──► NLU à règles (app/core/commandes.py)
                                                   │
                                                   ▼ Commande JSON Normalisée
                                             Validation Sécurité (app/core/securite.py)
                                                   │
                                                   ▼
                                             File FIFO (app/core/executeur.py)
                                                   │
                                                   ▼
                                             ControleurDobot (app/robot/controleur.py)
                                                   │
                   ┌───────────────────────────────┴───────────────────────────────┐
                   ▼                                                               ▼
           DobotSimule (Simulateur)                                     Dobot Magician Réel
         (app/robot/simulation.py)                                    (app/robot/protocole.py)
```

## 2. Décisions de Conception Clés

### A. Allègement du Battement JOG
* **Problème d'origine** : Chaque requête `/api/jog/beat` ou `/api/jog/battement` (10 fois par seconde) interrogeait la pose (`device.pose()`) et les registres d'alarmes sur le port série USB sous un verrou exclusif, saturant le bus.
* **Solution retenue** : `/api/jog/battement` se contente d'actualiser `controleur.dernier_battement = time.time()`. La lecture de la pose et des alarmes est prise en charge par un thread de télémétrie cadencé à 4 Hz.

### B. Contrôleur Simulable (`DobotSimule` / `MockDobot`)
* Implémente l'ensemble des méthodes nécessaires (`obtenir_pose` / `pose`, `deplacer_vers` / `move_to`, `regler_vitesse` / `speed`, `aspirer` / `suck`, `pincer` / `grip`, `recaler` / `home`, `fermer` / `close`).
* Intègre une simulation physique fluide des déplacements cartésiens et articulaires.
* Permet le travail en parallèle sans matériel et valide l'intégralité de la suite de tests automatisée.

### C. Flux Vidéo Singleton (`ServiceCamera` / `CameraService`)
* Un seul thread de capture instancie `cv2.VideoCapture` et diffuse les images JPEG encodées en mémoire (`/flux_video` ou `/video_feed`).
* Évite les blocages de `CAP_DSHOW` sous Windows lors de connexions concurrentes.
* Génère une mire synthétique de repérage et de calibration si aucune caméra n'est connectée.

## 3. Nomenclature et Fichiers en Français

| Composant | Fichier Principal | Classe / Fonction Clé | Alias de Compatibilité |
| :--- | :--- | :--- | :--- |
| **Commandes Normalisées** | `app/core/commandes.py` | `CommandeDeplacerVers`, `CommandePince`, `analyser_dictionnaire_commande` | `MoveToCommand`, `GripperCommand`, `parse_command_dict` |
| **Sécurité Cartésienne** | `app/core/securite.py` | `VerificateurSecurite` | `SafetyChecker` |
| **File d'Exécution** | `app/core/executeur.py` | `ExecuteurCommandes` | `CommandExecutor` |
| **Verrou de Session** | `app/core/etat.py` | `GestionnaireSession` | `SessionManager` |
| **Contrôleur Robot** | `app/robot/controleur.py`| `ControleurDobot` | `DobotController` |
| **Simulation Logicielle**| `app/robot/simulation.py`| `DobotSimule` | `MockDobot` |
| **Protocole Série** | `app/robot/protocole.py` | `envoyer_commande_brute`, `BASE_JOG_CARTESIEN` | `send_raw_command`, `JOG_CARTESIAN_BASE` |
| **Procédure HOME** | `app/robot/recalage.py` | `executer_sequence_recalage` | `run_homing_sequence` |
| **Service Vidéo** | `app/vision/camera.py` | `ServiceCamera`, `generer_flux_mjpeg` | `CameraService`, `generate_mjpeg_stream` |
| **Routes & API** | `app/api/routes.py` | `creer_routes` | `create_routes` |
| **Point d'Entrée** | `app/main.py` | `creer_application`, `charger_configuration` | `create_app`, `load_config` |
