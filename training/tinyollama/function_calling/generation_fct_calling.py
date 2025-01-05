import json
import openai
from openai import OpenAI
from pydantic import BaseModel
import os


class FctCalling(BaseModel):
    question:str
    response:str

class GeneratedFctCalling(BaseModel):
    fcts: list[FctCalling]

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
                if isinstance(item, FctCalling):
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
output_file = "training_function_calling.json"

#Récupérer les données:
data = json.load(open("tools_transformed.json", encoding="utf-8"))

taille = len(data)
compteur = 0

for item in data:
    question = item["question"]
    response = item["response"]
    compteur = compteur + 1
    print(f"{compteur}/{taille} : {question}")

    for index in range(1):  # Nombre d'itérations pour générer les données

        try:
            # Appel API OpenAI pour générer des données
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-2024-08-06",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"""
                            Tu es une IA spécialisée dans la génération de questions et réponses pour des outils spécifiques. Voici une tâche que tu dois réaliser :

À partir des informations suivantes :

Thème : {question}
Réponse type : {response}
Ta mission est de générer :
Il est crucial que tu sois créatif pour pas que les questions/réponses se se ressemblent. Essaye le plus possible d'utiliser un vocabulaire différent. 
Souvent la question à générer est un ordre, Joue X musique, Quelle heure est-il ? Qu'elle est la météo ? Génère un nombre etc... Les questions sont destinés à un LLM lors d'une discussion oral entre l'utilisateur et l'IA, appellé Cortex.
Une réponse pour chaque question, sous la forme d'une commande permettant d'activer l'outil avec les bons arguments.
Exemple :

Thème : Envoi d'un brouillon d'email.
Réponse type : "[send_draft draft_id='example' content='example' user_id='example']"
Résultat attendu :

Question : "Peux-tu envoyer le brouillon d'email intitulé 'Rapport mensuel' ?"

Réponse : "[send_draft draft_id='12345' content='Rapport mensuel' user_id='me']"


Avec ce modèle, remplace simplement le thème, la question type et la réponse type par ceux associés à ton outil, et l'IA générera automatiquement des scénarios pertinents. Si tu veux que je développe directement un exemple pour un autre thème, fais-le-moi savoir !
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
                response_format=GeneratedFctCalling,
            )

            # Récupération des résultats
            result = list(completion.choices[0].message.parsed)

            # Traiter et convertir les résultats en format sérialisable
            new_data = process_results(result)

            output_file = "training_function_calling.json"
            # Sauvegarder les nouvelles données dans le fichier JSON existant
            save_to_json(output_file, new_data)

            print(f"Les données ont été sauvegardées avec succès dans {output_file}.")

        except Exception as e:
            print(f"Erreur critique : {e}")


