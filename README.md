# Dobot AI Multimodale - Plateforme de Tri et Pilotage Intelligent

Projet 16 — Équipe ELT4A (ENSIL-ENSCI) — Version 1.1 (Français)

Architecture logicielle modulaire pour le pilotage multimodal d'un bras robotisé Dobot Magician : manette tactile, commandes textuelles, vocales (STT), gestuelles (MediaPipe) et vision par ordinateur (OpenCV / YOLO).

---

## 1. Principes Fondamentaux de Conception

1. **Chemin d'exécution unifié (Contrat Commun)** :
   Tous les modes de commande (manette JOG, texte libre, voix, gestes) sont traduits en amont en une commande structurée JSON validée par les modèles Pydantic (`app/core/commandes.py`).
2. **Point unique de sécurité** :
   Le module `app/core/securite.py` vérifie les limites de zone cartésienne, les hauteurs minimales de sécurité et plafonne les vitesses avant toute exécution matérielle.
3. **Découplage Simulation / Matériel (`DobotSimule`)** :
   L'application fonctionne à 100% avec ou sans bras physique branché grâce à la classe `DobotSimule` (`app/robot/simulation.py`), permettant à toute l'équipe de développer et tester sur PC ou à distance.
4. **Fluidité du JOG** :
   - Le battement `battement_jog` ne fait aucun appel bloquant sur le port série ; il rafraîchit uniquement un horodatage.
   - La télémétrie de pose et d'alarmes est déléguée à un thread d'arrière-plan cadencé à 4 Hz.
   - Les interfaces web sont organisées en templates Jinja2 (`app/web/templates/`) et fichiers statiques (`app/web/static/`).
   - Le flux vidéo caméra est capturé par un thread unique (Singleton `ServiceCamera`), évitant la saturation de `CAP_DSHOW`.

---

## 2. Arborescence du Projet

```
dobot-ai/
├── config/
│   ├── settings.yaml            # Paramètres de port, vitesses, zones de sécurité, bacs
│   └── calibration.json         # Homographie 4 points caméra vers repère robot
├── app/
│   ├── main.py                  # Point d'entrée de l'application Flask (creer_application)
│   ├── api/
│   │   └── routes.py            # Routes HTTP et endpoints REST (/api/commande, /api/jog, etc.)
│   ├── core/
│   │   ├── commandes.py         # Schémas Pydantic du contrat de commande & parser NLU
│   │   ├── securite.py          # Enveloppe de travail cartésienne et vérifications limites
│   │   ├── executeur.py         # File de tâches FIFO et gestion de l'arrêt prioritaire
│   │   └── etat.py              # Statut partagé et verrou de session utilisateur
│   ├── robot/
│   │   ├── protocole.py         # Trames Dobot, parsing binaire, gestion des alarmes
│   │   ├── controleur.py        # ControleurDobot unifié (gestion JOG, chien de garde, télémétrie)
│   │   ├── simulation.py        # Simulateur logiciel DobotSimule (développement sans bras)
│   │   └── recalage.py          # Procédure HOME sécurisée
│   ├── vision/
│   │   └── camera.py            # ServiceCamera partagé (cross-platform + mire synthétique)
│   └── web/
│       ├── templates/           # Pages HTML (base, index, manuel, texte, voix, gestes, image)
│       └── static/              # CSS et JS client (manette tactile fluide en français)
├── tests/
│   ├── test_commandes.py        # Tests unitaires des schémas Pydantic et règles NLU
│   ├── test_securite.py         # Tests des bornes de sécurité et validation d'enveloppe
│   ├── test_simulation.py       # Tests de déplacement simulé et dynamique JOG
│   └── test_api.py              # Tests d'intégration Flask des routes et de l'API
├── docker-compose.yml           # Déploiement multi-services (app Flask + serveur LLM llama.cpp)
├── Dockerfile                   # Conteneurisation pour Raspberry Pi 5
├── requirements.txt             # Dépendances Python
└── .env.example                 # Variables d'environnement
```

---

## 3. Guide de Démarrage Rapide

### Sur PC (Windows)

1. **Création d'un environnement virtuel & installation des dépendances** :
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Lancement en mode Simulation (sans bras physique)** :
   ```bash
   # Dans .env ou directement :
   set MOCK_ROBOT=true
   python app/main.py
   ```
   L'interface est accessible sur [http://localhost:5000](http://localhost:5000).

3. **Lancement avec le Dobot Magician branché** :
   - Vérifier le port COM attribué (ex: `COM4`) dans le Gestionnaire de périphériques.
   - Ajuster `config/settings.yaml` ou définir `DOBOT_PORT=COM4`.
   - Lancer :
     ```bash
     python app/main.py
     ```

### Exécution des Tests

```bash
pytest tests/ -v
```

---

## 4. Spécification des Commandes (Contrat JSON)

Toutes les actions acceptent un JSON structuré via `POST /api/commande` (ou `POST /api/command`) :

### A. Déplacement Cartésien Absolu
```json
{
  "action": "deplacer_vers",
  "x": 200.0,
  "y": 50.0,
  "z": 40.0,
  "r": 0.0
}
```

### B. Déplacement Relatif
```json
{
  "action": "deplacer_relatif",
  "axe": "Z",
  "pas": 20.0
}
```

### C. Actionnement Effecteurs
```json
{
  "action": "ventouse",
  "activer": true
}
```
ou pour la pince :
```json
{
  "action": "pince",
  "activer": true
}
```

### D. Tri Global
```json
{
  "action": "trier_tout",
  "regle": "par_couleur"
}
```
