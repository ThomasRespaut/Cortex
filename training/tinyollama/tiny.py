from openai import OpenAI
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import openai
import json
import random

# Chargement des variables d'environnement
load_dotenv()

# Initialisation du client OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Modèles de données
class Relations(BaseModel):
    source: str
    target: str
    relations: str

class Nodes(BaseModel):
    name: str
    value: str

class Database(BaseModel):
    nodes: list[Nodes]
    relations: list[Relations]

class Input(BaseModel):
    prompt: str
    database: Database
    question: str

class GenerativeDataset(BaseModel):
    input: list[Input]
    output: str

# Liste de thèmes variés
contexts = [
    "Tu es Cortex, un assistant vocal intelligent et discret. Ton objectif est de fournir des réponses précises, courtes et utiles à l'utilisateur, sans rentrer dans les détails de ton fonctionnement ou de tes capacités. Comporte-toi comme un ami respectueux et serviable, prêt à aider sans donner d'explications inutiles sur toi-même. Reste concentré sur la question de l'utilisateur et sur la meilleure façon de l'aider immédiatement."
]

themes = [
    "Planification de la journée de Thomas",
    "Organisation des réunions professionnelles de Thomas",
    "Suivi de l'emploi du temps des cours de Thomas",
    "Planification des séances de sport hebdomadaires de Thomas",
    "Gestion des projets d'alternance de Thomas",
    "Organisation des sorties avec les amis de Thomas",
    "Préparation des repas et planification alimentaire de Thomas",
    "Suivi des rendez-vous médicaux de Thomas",
    "Organisation des vacances avec la famille de Thomas",
    "Planification des révisions pour les examens de Thomas",
    "Gestion des finances personnelles de Thomas",
    "Planification des appels et réunions avec les collègues de Thomas",
    "Suivi des tâches ménagères de Thomas",
    "Organisation d'une fête d'anniversaire pour Thomas ou un proche",
    "Suivi des inscriptions et participations aux événements sportifs de Thomas",
    "Planification des week-ends de détente pour Thomas",
    "Organisation des rendez-vous avec les amis de Thomas",
    "Gestion des abonnements numériques de Thomas",
    "Préparation d'une présentation ou rapport pour le travail de Thomas",
    "Organisation des trajets domicile-travail de Thomas",
    "Suivi des deadlines des projets universitaires de Thomas",
    "Planification des activités familiales pour un dimanche",
    "Gestion des notifications et rappels pour les tâches de Thomas",
    "Organisation d'un déménagement ou d'une nouvelle installation pour Thomas",
    "Préparation des courses hebdomadaires de Thomas",
    "Suivi des entraînements pour un défi sportif de Thomas",
    "Organisation des vacances scolaires ou stages de Thomas",
    "Planification des horaires pour les réunions de groupe de Thomas",
    "Gestion des hobbies et loisirs créatifs de Thomas",
    "Préparation des documents administratifs pour Thomas",
    "Organisation des discussions avec le mentor ou tuteur de Thomas",
    "Planification des visites chez les proches de Thomas",
    "Gestion des formations et certifications supplémentaires de Thomas",
    "Organisation des séances de relaxation ou méditation de Thomas",
    "Planification d'une journée type pour une alternance productive",
    "Suivi des habitudes de sommeil et bien-être de Thomas",
    "Organisation des réunions d'équipe pour les projets de Thomas",
    "Planification des repas pour une semaine chargée de Thomas",
    "Gestion des événements culturels ou expositions auxquels Thomas souhaite participer",
    "Suivi des performances personnelles et objectifs fixés par Thomas",
    "Organisation des réservations pour un week-end en famille",
    "Planification des défis éducatifs ou certifications pour Thomas",
    "Suivi des appels téléphoniques importants pour Thomas",
    "Organisation des travaux de groupe pour les cours de Thomas",
    "Gestion des pauses et moments de détente pour Thomas",
    "Planification d'une réunion familiale pour discuter des vacances",
    "Organisation des activités bénévoles auxquelles Thomas participe",
    "Suivi des déplacements et voyages professionnels de Thomas",
    "Gestion des dates importantes comme les anniversaires des proches de Thomas",
    "Planification des objectifs sportifs à court et moyen terme",
    "Organisation des rendez-vous professionnels ou académiques",
    "Suivi des remboursements et budgets liés aux études de Thomas",
    "Planification des moments de loisirs avec les amis de Thomas",
    "Organisation d'une randonnée ou sortie nature pour Thomas",
    "Gestion des tâches de travail prioritaires de Thomas",
    "Suivi des compétitions ou événements sportifs préférés de Thomas",
    "Planification des moments de qualité avec les membres de la famille",
    "Organisation des périodes de révision intense avant un examen",
    "Gestion des outils numériques pour organiser les journées de Thomas",
    "Planification des activités à réaliser pendant un jour férié",
    "Organisation des formations en ligne ou webinaires pour Thomas",
    "Suivi des séries, films ou documentaires à regarder pour Thomas",
    "Planification des sessions de brainstorming ou idéation pour des projets",
    "Organisation des déplacements interurbains pour des événements importants",
    "Gestion des rappels pour les livraisons et commandes en ligne",
    "Suivi des participations à des concours ou hackathons de Thomas",
    "Planification des routines sportives quotidiennes ou hebdomadaires",
    "Organisation des discussions et sessions de feedback avec des professeurs",
    "Gestion des abonnements à des applications d'apprentissage",
    "Planification des heures de travail flexible pour l'alternance",
    "Organisation des plans de week-end pour explorer de nouvelles activités",
    "Suivi des échéances administratives pour les inscriptions ou paiements",
    "Planification des objectifs de développement personnel pour l'année",
    "Organisation des réunions d'équipe pour collaborer sur un projet professionnel",
    "Gestion des moments d'entraînement en pleine nature",
    "Suivi des interactions et rencontres avec des partenaires professionnels",
    "Planification des heures d'études et recherches académiques",
    "Organisation des moments de découverte culinaire avec des amis",
    "Gestion des projets de rénovation ou d'aménagement intérieur pour Thomas",
    "Suivi des engagements sociaux ou participations associatives",
    "Planification des conférences et séminaires à venir",
    "Organisation des backups et sécurisations de fichiers pour les études",
    "Suivi des abonnements aux salles de sport ou clubs d'activités",
    "Planification des projets de groupe pour un hackathon académique",
    "Organisation des sorties pour explorer des sites historiques",
    "Gestion des routines de productivité pour atteindre les objectifs trimestriels",
    "Suivi des rendez-vous avec des conseillers en carrière",
    "Planification des périodes de repos après une semaine intense",
    "Organisation des événements festifs entre camarades de classe",
    "Gestion des opportunités de networking professionnel",
    "Suivi des ateliers de créativité et d'innovation auxquels Thomas participe",
    "Planification des itinéraires de voyage pour optimiser le temps de trajet",
    "Organisation des groupes de discussion pour des projets académiques",
    "Gestion des tickets et réservations pour des spectacles ou concerts",
    "Suivi des notifications importantes pour ne pas manquer de deadlines",
    "Planification des moments de loisirs numériques ou jeux vidéo",
    "Organisation des supports de présentation pour des meetings professionnels",
    "Gestion des interactions sur des plateformes de collaboration en ligne",
    "Suivi des rendez-vous médicaux ou dentaires programmés",
    "Planification des événements de bien-être mental ou physique pour Thomas"
]

# --------------------- FONCTION DE CONVERSION ---------------------
def convert_to_serializable(obj):
    """
    Convertit récursivement un objet (Pydantic, liste, dict, etc.)
    en un type Python nativement sérialisable (dict, list, str, etc.)
    """
    if isinstance(obj, BaseModel):
        return obj.dict()
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    else:
        return obj  # Types primitifs (str, int, float, bool, None) restent tels quels

# --------------------- SAUVEGARDE IMMÉDIATE ---------------------
def save_to_json(file_path, new_data):
    """
    Sauvegarde directement les nouvelles données dans le fichier JSON
    """
    # Lire les données existantes
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = []
        else:
            existing_data = []

        # Ajouter les nouvelles données
        existing_data.append(new_data)

        # Sauvegarder dans le fichier
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde dans le fichier JSON: {e}")

# --------------------- GÉNÉRATION DES DONNÉES ---------------------
output_file = "training_version2.json"

for index in range(1000):
    theme = random.choice(themes)
    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu dois créer des données d'entraînement pour une IA avec du RAG. "
                        "Ces données serviront à entraîner un HomePod du nom de Cortex."
                        "à répondre à des questions spécifiques. Thomas lance une conversation sur le thème abordé "
                        "et tu lui réponds d'un ton amical et respectueux en t'adressant à 'tu'. "
                        "Il est important d'avoir des questions/réponses basiques qui peuvent arriver plusieurs fois "
                        "par jour pour répondre aux besoins essentiels en priorité."
                    )
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "input": {
                            "prompt": (
                                "Tu es Cortex, un assistant vocal intelligent et discret. "
                                "Ton objectif est de fournir des réponses précises, courtes et utiles à l'utilisateur, "
                                "sans rentrer dans les détails de ton fonctionnement ou de tes capacités. "
                                "Comporte-toi comme un ami respectueux et serviable, "
                                "prêt à aider sans donner d'explications inutiles sur toi-même. "
                                "Reste concentré sur la question de l'utilisateur et sur la meilleure façon "
                                "de l'aider immédiatement."
                            ),
                            "database": (
                                "Génère une base de données aléatoire et réaliste selon le thème : "
                                + theme
                            ),
                            "question": (
                                "Génère une question cohérente selon le thème : "
                                + theme
                            )
                        },
                        "output": (
                            "Génère une réponse réaliste et utile basée sur la question et la base de données."
                        )
                    })
                }
            ],
            response_format=GenerativeDataset,
        )

        # Récupération du format (liste de tuples): [("input", ...), ("output", ...)]
        result = list(completion.choices[0].message.parsed)
        print(f"Résultat {index + 1}:", result)

        # Conversion pour la sauvegarde
        input_tuple, output_tuple = result
        input_data = convert_to_serializable(input_tuple[1])
        output_data = convert_to_serializable(output_tuple[1])

        # Sauvegarde immédiate
        save_to_json(output_file, {"input": input_data, "output": output_data})

    except AttributeError as e:
        print(f"Erreur lors de la génération des données à l'index {index + 1}: {e}")
        continue
