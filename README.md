# Cortex

Cortex est un projet étudiant visant à développer un homepod utilisant l'intelligence artificielle pour créer un jumeau numérique capable de gérer les communications, les routines quotidiennes et les interactions vocales. Inspiré de Google Home, Cortex intègre une suite de fonctionnalités avancées pour offrir une expérience personnalisée et intuitive à l'utilisateur.

## Fonctionnalités principales

### 1. **Assistant IA**
- Communication vocale naturelle avec l'utilisateur.
- Interaction avec des API pour récupérer et traiter les données nécessaires à la routine quotidienne.

### 2. **Gestion des données personnelles**
- **Emails** : Intégration pour lire et organiser les emails.
- **Calendrier** : Synchronisation et gestion des événements.
- **Santé** : Récupération des données de santé à partir de capteurs et d'applications.
- **Réseaux sociaux et messagerie** : Notifications et mise à jour des messages.
- **Musique** : Gestion des playlists et recommandations.
- **Trajets quotidiens** : Analyse et optimisation des trajets.

### 3. **Personnalisation avancée**
- Création d'un jumeau numérique pour mieux comprendre et anticiper les besoins de l'utilisateur.
- Apprentissage continu grâce à un modèle d'IA entraîné sur les interactions de l'utilisateur.

## Architecture

### Technologies utilisées
- **Python** : Langage principal pour le développement des fonctionnalités.
- **Keras** : Construction et entraînement du modèle IA (CNN).
- **OpenCV** : Manipulation et traitement des images.
- **Neo4j** : Gestion et analyse des graphes relationnels.

### Intégration des API
- Récupération de données en temps réel via diverses API pour des services tels que Gmail, Google Calendar, Spotify, et des applications de santé.

## Installation

### Prérequis
- Python 3.12
- Environnement virtuel Python (recommandé)
- Modules Python : `keras`, `opencv-python`, `neo4j`, `requests`
- Accès aux clés API des services intégrés (Gmail, Google Calendar, etc.)

### Étapes d'installation
1. Cloner le dépôt :
   ```bash
   git clone https://github.com/ThomasRespaut/Cortex.git
   ```
2. Naviguer dans le répertoire du projet :
   ```bash
   cd Cortex
   ```
3. Installer les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
4. Copier `.env.example` vers `.env`, puis renseigner uniquement les services
   utilisés. Les jetons OAuth et mots de passe ne doivent jamais être commités.
5. Lancer le projet :
   ```bash
   .venv\Scripts\python.exe Screen.py
   ```

Le mot-clé « Ok Cortex » nécessite une clé Picovoice. Sans cette clé, un clic
sur le bouton Cortex lance directement l'écoute du microphone.

### Raspberry Pi et écran circulaire tactile

L'interface principale est [Screen.py](Screen.py). Pour un écran circulaire
tactile, gardez Cortex en plein écran et ajustez uniquement les variables
d'environnement nécessaires dans `.env` :

```bash
CORTEX_FULLSCREEN=true
CORTEX_HIDE_CURSOR=true
CORTEX_TOUCH_ROTATION=0
CORTEX_TOUCH_ROUND_CLIP=true
CORTEX_TOUCH_EDGE_MARGIN=0
CORTEX_TAP_MOVE_LIMIT=14
```

`CORTEX_TOUCH_ROTATION` accepte `0`, `90`, `180` ou `270` pour aligner les
coordonnées tactiles avec l'orientation réelle de l'écran.
`CORTEX_TOUCH_ROUND_CLIP=true` ignore les appuis hors du disque utile de
l'écran circulaire, et `CORTEX_TOUCH_EDGE_MARGIN` retire quelques pixels au
rayon tactile si la bordure physique déclenche des appuis parasites.
`CORTEX_TAP_MOVE_LIMIT` règle la tolérance entre un tap et un drag si le
tactile génère du jitter. Sur un poste de développement, utilisez plutôt :

```bash
CORTEX_FULLSCREEN=false
CORTEX_PREVIEW_SIZE=900
```

Pour forcer une taille exacte de fenêtre, par exemple le panneau circulaire
Raspberry Pi en 480x480, utilisez :

```bash
CORTEX_FULLSCREEN=false
CORTEX_SCREEN_SIZE=480x480
```

Pour tester le rendu sans modèle, sans micro et sans fenêtre réelle :

```bash
SDL_VIDEODRIVER=dummy CORTEX_FULLSCREEN=false CORTEX_SKIP_CORTEX_LOAD=true CORTEX_SCREENSHOT_PATH=artifacts/screen.png CORTEX_EXIT_AFTER_SCREENSHOT=true python Screen.py
```

Sur Raspberry Pi, le script de lancement kiosk applique des valeurs plein écran
adaptées à l'écran tactile, puis lance `Screen.py`, qui charge `.env` via
`python-dotenv` :

```bash
scripts/setup_raspberry_pi.sh
chmod +x scripts/launch_raspberry_pi.sh
scripts/launch_raspberry_pi.sh
```

Le lanceur force aussi `SDL_TOUCH_MOUSE_EVENTS=0` et
`SDL_MOUSE_TOUCH_EVENTS=0` afin qu'un appui tactile ne soit pas traité deux fois
par SDL/Pygame.

`requirements-raspberry-pi.txt` installe le socle interface/audio/API. Les
paquets de modèle local lourd (`torch`, `transformers`, `peft`) restent à
installer séparément si la Raspberry Pi cible a assez de mémoire et de stockage.

Un exemple de service de démarrage est disponible dans
`deploy/raspberry-pi/cortex.service.example`. Copiez-le vers
`/etc/systemd/system/cortex.service`, adaptez `User`, `WorkingDirectory` et
`ExecStart`, puis activez-le avec `sudo systemctl enable --now cortex.service`.

Pour générer ce service automatiquement depuis le répertoire courant du clone :

```bash
sudo CORTEX_PROJECT_DIR="$(pwd)" CORTEX_SERVICE_USER="$USER" deploy/raspberry-pi/install_service.sh
sudo systemctl start cortex.service
```

Le script active le service au démarrage. Il ne le démarre immédiatement que si
`CORTEX_START_SERVICE=true` est fourni.

Avant de l'activer sur la Raspberry Pi, lancez la validation locale complète.
Elle vérifie le préflight, capture `Screen.py` en mode headless, puis rend les
écrans Pygame anciens et modernes en 480x480 :

```bash
python tools/validate_raspberry_pi_ui.py --project-root . --size 480x480
```

Pour ne lancer que le préflight de configuration, sans rendu Pygame :

```bash
python tools/raspberry_pi_preflight.py --project-root .
```

### Tests rapides

Les tests du cœur local ne nécessitent ni modèle IA, ni microphone, ni compte
externe :

```bash
python tools/run_local_checks.py
```

Cette commande enchaîne compilation Python, tests unitaires, `pip check`,
validation du dataset fine-tuning et validation Raspberry Pi/Pygame. Pour lancer
une étape isolée pendant un diagnostic :

```bash
python -m unittest discover -s tests -v
python tools\validate_finetune_dataset.py --dataset-dir training\finetune_cortex_v3
```

Ces vérifications sont aussi exécutées par GitHub Actions sur les pull requests
et les pushes vers `master` ou `codex/**`.

Pour mesurer rapidement les réponses du modèle local sans lancer l'interface :

```bash
.venv\Scripts\python.exe tools\evaluate_local_model.py
```

Si le dossier `tinyllama_cortex_finetuned_v3_lora/` est présent, Cortex charge
automatiquement cet adaptateur LoRA par-dessus le modèle de base
`tinyllama_cortex_finetuned/`. Sinon, il utilise le LoRA v2 local
`tinyllama_cortex_finetuned_v2_lora/` quand il existe. Pour comparer avec le
modèle de base seul :

```bash
.venv\Scripts\python.exe tools\evaluate_local_model.py --no-adapter --limit 3
```

### Fine-tuning Cortex

Le modèle local se trouve dans `tinyllama_cortex_finetuned/`. Avant de
réentraîner, générez un dataset v3 aligné avec les vrais outils Cortex :

```bash
.venv\Scripts\python.exe tools\build_finetune_dataset.py --output-dir training\finetune_cortex_v3
.venv\Scripts\python.exe tools\validate_finetune_dataset.py --dataset-dir training\finetune_cortex_v3
```

Le script supprime les exemples qui appellent des outils inexistants, afin
d'éviter les sorties comme `play_music`, `send_message` ou `set_alarm` si ces
fonctions ne sont pas branchées dans `function_calling.py`.

Pour vérifier la chaîne LoRA sur CPU sans lancer un vrai entraînement :

```bash
.venv\Scripts\python.exe tools\train_cortex_lora.py --max-steps 1 --allow-cpu --output-dir tinyllama_cortex_finetuned_v2_lora_smoke --max-length 128
```

Pour un vrai fine-tuning TinyLlama, utilisez un environnement PyTorch avec CUDA
ou une machine GPU. La venv CPU Windows fonctionne pour valider la chaîne, mais
elle est trop lente pour un entraînement complet.

### Sécurité

Les identifiants sont chargés depuis l'environnement. Si un jeton ou un secret a
déjà été publié dans l'historique Git, le supprimer du dernier commit ne suffit
pas : il faut aussi le révoquer auprès du fournisseur concerné.

## Utilisation

Une fois lancé, Cortex sera prêt à répondre aux commandes vocales et gérer vos routines quotidiennes. Les interactions se font via une interface utilisateur vocale ou un tableau de bord Web (en cours de développement).

## Contribuer

### Comment contribuer
Les contributions sont les bienvenues ! Pour contribuer :
1. Forker le projet.
2. Créer une branche pour votre fonctionnalité ou correction :
   ```bash
   git checkout -b feature/ma-nouvelle-fonctionnalite
   ```
3. Faire vos modifications et tester.
4. Soumettre une pull request.

### Issues
Si vous rencontrez un problème ou souhaitez suggérer une amélioration, veuillez créer une issue dans le dépôt GitHub.

## À propos

Cortex est développé par **Thomas RESPAUT** dans le cadre d'un projet étudiant. Ce projet vise à explorer les capacités de l'IA dans les interactions humaines et la gestion des données personnelles.

Pour toute question ou demande d'information, veuillez contacter [Thomas RESPAUT](mailto:thomas.respaut@edu.devinci.fr).

## Licence

Cortex est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.
