import json
import openai
from openai import OpenAI
from pydantic import BaseModel
import os

class GeneratedFctCalling(BaseModel):
    question:str
    response:str

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

    for index in range(5):  # Nombre d'itérations pour générer les données

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

            # Récupération du format (liste de tuples): [("input", ...), ("output", ...)]
            result = list(completion.choices[0].message.parsed)
            print(f"Résultat {index + 1}:", result)

            # Conversion pour la sauvegarde
            input_tuple, output_tuple = result
            input_data = convert_to_serializable(input_tuple[1])
            output_data = convert_to_serializable(output_tuple[1])

            # Sauvegarde immédiate
            save_to_json(output_file, {"question": input_data, "response": output_data})

        except AttributeError as e:
            print(f"Erreur lors de la génération des données à l'index {index + 1}: {e}")
            continue











