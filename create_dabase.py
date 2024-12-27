from database import Neo4jDatabase
import random
import json
import openai
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from openai import OpenAI

# Charger les variables d'environnement
load_dotenv()

# Définition des modèles pour la structure des donnée

db = Neo4jDatabase()

class GeneratedRelation(BaseModel):
    entite: str
    proprietes: str
    relation: str
    cible_relation: str
    proprietes_relation: str
    relation_inverse: str

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

# Fonction pour sauvegarder les données dans un fichier JSON
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

def save_to_txt(file_path, new_data):
    """
    Incrémente directement les nouvelles données dans un fichier TXT
    """
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(new_data + "\n")
    except Exception as e:
        print(f"Erreur lors de l'ajout au fichier TXT: {e}")


# Initialiser le client OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Générer et sauvegarder des questions/réponses
output_file = "relations_generées.json"

for index in range(1000):  # Nombre d'itérations pour générer les données
    try:

        data = db.recuperer_informations_graph()

        # Appel API OpenAI pour générer des données
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es Cortex, un assistant vocal conçu pour être amical, curieux et serviable. "
                        "Génère dynamiquement des relations pour une base de données. Chaque relation inclut des entités, leurs propriétés, et les connexions associées. "
                        "Les données concernent principalement les amis, les activités sportives, les projets, et les relations du nœud principal : nom = Respaut, prénom = Thomas. Essaye de toujours garder un lien proche avec ce noeud."
                        "Utilise ce format pour chaque relation : "
                        "{\"entite\": \"type d'entité\", \"proprietes\": {\"nom\": \"valeur\"}, \"relation\": \"type de relation\", "
                        "\"cible_relation\": \"type d'entité cible\", \"proprietes_relation\": {\"nom\": \"valeur\"}, \"relation_inverse\": true/false}."
                        "Les entités peuvent inclure des amis proches, des activités sportives comme le football ou la natation, ou encore des projets tels que 'Projet IA'."
                        f"Voici les informations déja présentes dans la base de données Neo4J : {data}"
                    )
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "entite": random.choice(["Lieu", "Activite", "Projet", "Personne"]),
                        "proprietes": {"nom": random.choice(["Paris", "Football", "Projet IA", "Thomas"]), "duree": "1h"},
                        "relation": random.choice(["VIT_A", "PARTICIPE_A", "TRAVAILLE_SUR", "CONNAIT"]),
                        "cible_relation": "Personne",
                        "proprietes_relation": {"prenom": "Thomas", "nom": "Respaut"},
                        "relation_inverse": random.choice([True, False])
                    })
                }
            ],
            response_format=GeneratedRelation,
        )

        # Récupération du format (liste de tuples): ["input", ...]
        # Récupération du format (liste de tuples): ["input", ...]
        result = list(completion.choices[0].message.parsed)

        for item_group in [result]:
            try:
                entite = [item[1] for item in item_group if item[0] == 'entite'][0]
                proprietes = json.loads([item[1] for item in item_group if item[0] == 'proprietes'][0])
                relation = [item[1] for item in item_group if item[0] == 'relation'][0]
                cible_relation = [item[1] for item in item_group if item[0] == 'cible_relation'][0]
                proprietes_relation = json.loads(
                    [item[1] for item in item_group if item[0] == 'proprietes_relation'][0]
                )
                relation_inverse = [item[1] for item in item_group if item[0] == 'relation_inverse'][
                                       0].lower() == 'true'

                # Appel explicite à la méthode
                db.ajouter_entite_et_relation(
                    entite=entite,
                    proprietes=proprietes,
                    relation=relation,
                    cible_relation=cible_relation,
                    proprietes_relation=proprietes_relation,
                    relation_inverse=relation_inverse,
                )

                # Sauvegarder dans un fichier TXT
                save_to_txt("relations.txt", json.dumps({
                    "entite": entite,
                    "proprietes": proprietes,
                    "relation": relation,
                    "cible_relation": cible_relation,
                    "proprietes_relation": proprietes_relation,
                    "relation_inverse": relation_inverse
                }))

                # Sauvegarder dans un fichier JSON
                save_to_json("relations.json", {
                    "entite": entite,
                    "proprietes": proprietes,
                    "relation": relation,
                    "cible_relation": cible_relation,
                    "proprietes_relation": proprietes_relation,
                    "relation_inverse": relation_inverse
                })

            except (IndexError, KeyError, ValueError, json.JSONDecodeError) as e:
                print(f"Erreur de formatage ou de décodage : {e}")

    except AttributeError as e:
        print(f"Erreur lors de la génération des données à l'index {index + 1}: {e}")
        continue
