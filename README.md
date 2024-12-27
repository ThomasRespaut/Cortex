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
- Python 3.8 ou supérieur
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
4. Configurer les fichiers `.env` avec vos clés API et informations personnelles.
5. Lancer le projet :
   ```bash
   python cortex.py
   ```

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
