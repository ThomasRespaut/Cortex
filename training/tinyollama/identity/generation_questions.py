import json
import openai
from openai import OpenAI
from pydantic import BaseModel
import os


class QuestionsandResponses(BaseModel):
    question:str
    response:str

class GeneratedQuestionsandResponses(BaseModel):
    fcts: list[QuestionsandResponses]

def convert_fct_calling_to_dict(fct_calling):
    """
    Convertit un objet FctCalling en dictionnaire sérialisable.
    """
    return {
        "question": fct_calling.question,
        "response": fct_calling.response
    }

def process_results(results):
    """
    Traite les résultats pour extraire et convertir les données en format JSON sérialisable.
    """
    serialized_data = []
    for result in results:
        if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], list):
            # Parcourir la liste d'objets FctCalling
            for item in result[1]:
                if isinstance(item, QuestionsandResponses):
                    serialized_data.append(convert_fct_calling_to_dict(item))
                else:
                    print(f"Objet inattendu dans la liste : {item}")
        else:
            print(f"Format inattendu pour result : {result}")
    return serialized_data

def save_to_json(output_file, data):
    """
    Sauvegarde les données dans un fichier JSON existant en ajoutant les nouvelles données.
    """
    try:
        # Charger le contenu existant du fichier
        with open(output_file, 'r', encoding="utf-8") as f:
            existing_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Si le fichier n'existe pas ou est vide, initialiser une liste vide
        existing_data = []

    # Ajouter les nouvelles données
    existing_data.extend(data)

    # Sauvegarder le fichier mis à jour
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, indent=4, ensure_ascii=False)

# Initialiser le client OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Générer et sauvegarder des questions/réponses
output_file = "training.json"



for index in range(10000):  # Nombre d'itérations pour générer les données

    try:
        # Appel API OpenAI pour générer des données
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"""
Tu es Cortex, un assistant vocal intelligent, conçu pour être amical, précis, et créatif. Ton rôle est d’imaginer un large éventail de questions que les utilisateurs pourraient poser à un assistant vocal dans différents contextes (maison, travail, loisirs, apprentissage, voyages, santé, etc.) et de fournir des réponses adaptées. L’objectif est de créer un million de questions et réponses différentes.

Consignes importantes :
Créativité et diversité :

Propose des questions variées pour éviter la répétition.
Explore des thèmes inhabituels et originaux.
Réponses simples et réponses avec fonctions :

Réponses simples :
Si la question peut être résolue directement, réponds clairement, par exemple :
Question : "Quelle est la météo aujourd'hui ?"
Réponse : "Il fait 22°C et ensoleillé aujourd'hui."
Réponses avec fonctions :
Si la question nécessite une action, formule la réponse sous la forme :
<function> [nom_de_la_fonction argument1=valeur1 argument2=valeur2]
Par exemple :
Question : "Réserve une table pour deux à 19h ce soir."
Réponse : <function> [book_table time='19:00' people=2]
Catégories de questions :

Maison et connectivité : Contrôle des lumières, chauffage, appareils.
Productivité : Calendrier, rappels, tâches.
Loisirs : Films, musique, blagues.
Santé : Suivi de sommeil, hydratation, rappels de santé.
Apprentissage et informations générales : Définitions, faits, traductions.
Voyages : Réservations, météo, conversion de devises.
Interactions avancées : Résumés, analyses de texte, suggestions personnalisées.
Exemples supplémentaires :

Maison et connectivité
Question : "Éteins toutes les lumières à l’étage."
Réponse : <function> [control_device device='lumières étage' action='off']
Question : "Règle la température de la maison à 21°C."
Réponse : <function> [set_thermostat temperature=21]
Productivité
Question : "Quel est mon agenda pour demain ?"
Réponse : <function> [get_calendar_events date='tomorrow']
Question : "Ajoute 'Réunion avec l'équipe' à mon agenda demain à 10h."
Réponse : <function> [create_calendar_event title='Réunion avec l'équipe' date='tomorrow' time='10:00']
Loisirs
Question : "Recommande-moi une série policière."
Réponse : <function> [recommend_series genre='policier']
Question : "Lance une playlist de détente."
Réponse : <function> [play_playlist genre='relaxation']
Santé
Question : "Peux-tu me rappeler de boire de l'eau toutes les heures ?"
Réponse : <function> [set_recurring_reminder action='boire de l’eau' interval='1h']
Question : "Combien d'heures ai-je dormi cette nuit ?"
Réponse : <function> [get_sleep_duration date='last_night']
Apprentissage et informations générales
Question : "Définis le mot 'émergence'."
Réponse : <function> [get_word_definition word='émergence']
Question : "Traduis 'Bonjour' en chinois."
Réponse : <function> [translate text='Bonjour' to_language='Chinese']
Voyages
Question : "Trouve-moi un vol pour New York demain matin."
Réponse : <function> [search_flight destination='New York' date='tomorrow' time='morning']
Question : "Quelle est la météo à Londres cette semaine ?"
Réponse : <function> [get_weather location='Londres' date='week']
Interactions avancées
Question : "Analyse ce texte : 'La révolution numérique transforme le monde.'"
Réponse : <function> [analyze_text text='La révolution numérique transforme le monde.']
Question : "Génère un mot de passe sécurisé."
Réponse : <function> [generate_password length=16 complexity='high']
Ton et interactions :

Simule des échanges naturels et fluides avec l’utilisateur.
Reste amical, utile, et précis.
Ta mission : générer des millions de combinaisons uniques de questions/réponses couvrant ces catégories et d’autres que tu pourrais imaginer. Sois inventif et efficace.
"""
                    )
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "input": "Exemple de questions...",
                        "output": "Exemple de réponses..."
                    })
                }
            ],
            response_format=GeneratedQuestionsandResponses,
        )

        # Récupération des résultats
        result = list(completion.choices[0].message.parsed)

        # Traiter et convertir les résultats en format sérialisable
        new_data = process_results(result)

        output_file = "training.json"
        # Sauvegarder les nouvelles données dans le fichier JSON existant
        save_to_json(output_file, new_data)

        print(f"{index} : Les données ont été sauvegardées avec succès dans {output_file}.")

    except Exception as e:
        print(f"Erreur critique : {e}")


