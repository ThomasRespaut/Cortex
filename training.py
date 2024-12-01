from mistralai import Mistral
import os
from dotenv import load_dotenv
import json
import time
import pandas as pd

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Charger la clé API depuis les variables d'environnement
api_key = os.getenv("MISTRAL_API_KEY")

# Créer le client Mistral
client = Mistral(api_key=api_key)

# List jobs
jobs = client.fine_tuning.jobs.list()
for job in jobs:
    print(job)

input("end :")




# Préparer et diviser les données
def prepare_data():
    # Charger le fichier original
    df = pd.read_json("dataframe_function.jsonl", lines=True)

    # Diviser les données : 80% pour l'entraînement, 20% pour la validation
    df_train = df.sample(frac=0.8, random_state=200)
    df_eval = df.drop(df_train.index)

    # Sauvegarder les jeux d'entraînement et de validation
    df_train.to_json("train_data.jsonl", orient="records", lines=True)
    df_eval.to_json("eval_data.jsonl", orient="records", lines=True)

# Appeler la préparation des données
prepare_data()

# Fonction pour téléverser un fichier
def upload_file(filename):
    # Téléverser le fichier d'entraînement
    with open(filename, "rb") as file_content:
        uploaded_file = client.files.upload(
            file={
                "file_name": filename,
                "content": file_content,
            }
        )
    return uploaded_file

# Téléverser le fichier d'entraînement et de validation
training_data = upload_file(filename="train_data.jsonl")
print(f"Training Data Uploaded: {training_data}")

eval_data = upload_file(filename="dataset_eval.jsonl")
print(f"Evaluation Data Uploaded: {eval_data}")

# Fonction pour démarrer le fine-tuning
def fine_tuning(training_file_id, validation_file_id):
    # Créer un travail de fine-tuning
    created_job = client.fine_tuning.jobs.create(
        model="open-mistral-nemo",  # Nom du modèle utilisé pour le fine-tuning
        training_files=[{"file_id": training_file_id, "weight": 1}],  # Fichier d'entraînement avec poids
        validation_files=[validation_file_id],  # Fichier de validation
        hyperparameters={
            "learning_rate": 0.0001,
            "training_steps": 10
        },
        auto_start=True  # Démarrer automatiquement après la création
    )
    return created_job

# Création et démarrage du fine-tuning
created_job = fine_tuning(training_data.id, eval_data.id)

# Affichage des informations sur le travail créé
def pprint(obj):
    print(json.dumps(obj.dict(), indent=4))

pprint(created_job)

# Vérifier le statut du fine-tuning
def monitor_job(job_id):
    retrieved_job = client.fine_tuning.jobs.get(job_id=job_id)
    while retrieved_job.status in ["RUNNING", "QUEUED"]:
        pprint(retrieved_job)
        print(f"Job is {retrieved_job.status}, waiting 10 seconds...")
        time.sleep(10)
        retrieved_job = client.fine_tuning.jobs.get(job_id=job_id)
    # Afficher le statut final
    pprint(retrieved_job)
    return retrieved_job

# Surveiller le statut du job jusqu'à la fin
retrieved_job = monitor_job(created_job.id)

# Utiliser le modèle fine-tuné pour une réponse de chat (si le fine-tuning est terminé avec succès)
if retrieved_job.status == "SUCCESS" and retrieved_job.fine_tuned_model:
    # Question basée sur la BDD de CORTEX
    messages = [
        {"role": 'user', "content": "Quels sont mes projets en cours ?"},
        {"role": 'system', "content": "Vous avez indiqué que vous participez au projet 'Cortex Dev'."}
    ]

    chat_response = client.chat.complete(
        model=retrieved_job.fine_tuned_model,
        messages=messages
    )

    pprint(chat_response)
else:
    print("Fine-tuning did not complete successfully. No model available for chat.")
