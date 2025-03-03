from openai import OpenAI  # Pour TTS et STT
from mistralai import Mistral
import io
import subprocess
from pydub import AudioSegment
from pydub.playback import play
import pvporcupine
import pyaudio
import numpy as np
import os
from dotenv import load_dotenv
import time
import json
import vosk
from vosk import SetLogLevel
import wave
from database.database import Neo4jDatabase
from assistant.films_and_series import films_and_series
from assistant.spotify.spotify_assistant import SpotifyAssistant
from assistant.ratp.ratp_assistant import IDFMAssistant
from assistant import functions
from assistant.apple.iphone import AppleAssistant
from assistant.google.google_assistant import GoogleAssistant
from transformers import AutoTokenizer, AutoModelForCausalLM
import re
from function_calling import execute_tool

# Instancier les assistants Spotify et Apple
spotify_assistant = SpotifyAssistant()
apple_assistant = AppleAssistant()
idfm_assistant = IDFMAssistant()
google_assistant = GoogleAssistant()

# Créer le dictionnaire de fonctions en utilisant les instances des assistants
names_to_functions = {
    # Spotify Functions
    'get_current_time': functions.get_current_time,
    'generate_random_number': functions.generate_random_number,
    'recommend_media': films_and_series.recommend_media,
    'play_track': spotify_assistant.play_track,
    'pause_playback': spotify_assistant.pause_playback,
    'resume_playback': spotify_assistant.resume_playback,
    'next_track': spotify_assistant.next_track,
    'previous_track': spotify_assistant.previous_track,
    'set_volume': spotify_assistant.set_volume,
    'get_current_playback': spotify_assistant.get_current_playback,
    'play_recommendations_track': spotify_assistant.play_recommendations_track,

    # Apple Functions
    'get_iphone_battery': apple_assistant.get_iphone_battery,
    'get_location': apple_assistant.get_location,
    'get_weather': apple_assistant.get_weather,
    'get_contacts': apple_assistant.get_contacts,
    'play_sound_on_iphone': apple_assistant.play_sound_on_iphone,
    'activate_lost_mode': apple_assistant.activate_lost_mode,

    # IDFM Assistant Functions
    'calculate_route': idfm_assistant.calculate_route,

    # Google Assistant Functions
    'create_google_task': google_assistant.create_google_task,
    'create_calendar_event': google_assistant.create_calendar_event,
    'summarize_today_emails': google_assistant.summarize_today_emails,
    'list_and_analyze_today_emails': google_assistant.list_and_analyze_today_emails,
    'collect_emails': google_assistant.collect_emails,
    'mark_as_read': google_assistant.mark_as_read,
    'trash_message': google_assistant.trash_message,
    'archive_message': google_assistant.archive_message,
    'reply_to_message': google_assistant.reply_to_message,
    'create_email': google_assistant.create_email,
    'display_draft': google_assistant.display_draft,
    'create_draft_reply': google_assistant.create_draft_reply,
    'send_draft': google_assistant.send_draft
}

load_dotenv()

class Cortex:
    def __init__(self,input_mode="voice",output_mode="voice",local_mode=True,rate_in=44100,rate_out=22050):

        #Choix de la version locale à la version online
        self.local_mode = local_mode
        #Modèle en local :
        self.tokenizer = AutoTokenizer.from_pretrained("./tinyllama_cortex_finetuned")
        self.model = AutoModelForCausalLM.from_pretrained("./tinyllama_cortex_finetuned")
        print("Modèle fine-tuné TinyCortex chargé avec succès.")
        self.rate_in = rate_in
        self.rate_out = rate_out
        # Charger le modèle Vosk pour la transcription locale
        vosk_model_path = "vosk-model-small-fr-0.22"  # Chemin du modèle Vosk
        if os.path.exists(vosk_model_path):
            SetLogLevel(-1)
            self.model_stt = vosk.Model(vosk_model_path)
            self.recognizer = vosk.KaldiRecognizer(self.model_stt, rate_in)  
            print("Modèle Vosk chargé avec succès.")  

        voice_model_path = "piper/fr_FR-upmc-medium.onnx"
        if os.path.exists(voice_model_path):
            self.voice_model_path = voice_model_path
            piper_path = "piper/piper.exe"
            self.piper_command = [
                piper_path,           
                "--model", self.voice_model_path, 
                "--output-raw"        
            ]
            print("Modèle Piper chargé avec succès.")  

        #Modèle online :
        openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        self.voice = "echo"
        mistral_api_key = os.getenv('MISTRAL_API_KEY')
        self.mistral_client = Mistral(api_key=mistral_api_key) if mistral_api_key else None
        self.mistral_model = "ft:open-mistral-nemo:7771e396:20241004:a1df71c2"

        self.first_keyword_detection = True  # Détection du premier ok Cortex
        self.db = Neo4jDatabase()

        #Utilisation des différents outils :
        with open("assistant/tools.json", "r") as file:
            self.tools = json.load(file)

        #Prompt
        self.system = """
        Tu es Cortex, un assistant vocal intelligent et discret. Ton objectif est de fournir des réponses précises, courtes et utiles à l'utilisateur, sans rentrer dans les détails de ton fonctionnement ou de tes capacités. Comporte-toi comme un ami respectueux et serviable, prêt à aider sans donner d'explications inutiles sur toi-même. Réponds de manière simple et directe, sans rappeler que tu es un assistant. Reste concentré sur la question de l'utilisateur et sur la meilleure façon de l'aider immédiatement.
        """

        #Conversation enregistrée dans self.messages
        self.messages = [
            {"role": "system", "content": self.system},
        ]

        #Choix de l'entrée ou de la sortie (texte ou audio)
        self.input_mode = input_mode
        self.output_mode = output_mode


    def visualiser_database(self):
        db=Neo4jDatabase()
        db.visualiser_graph_interactif()

    def generate_speech(self, text):

        #Fonction local :
        if self.local_mode == True:
            return self.generate_speech_local(text)

        else:
            return self.generate_speech_online(text)

    def generate_speech_local(self,text,sample_rate=22050, chunk_size=1024):
        if not text or not isinstance(text, str):  # Vérifier que le texte est un string
            print("Invalid text input for speech generation.")
            return None
        try:


            # Lancer Piper avec le texte fourni en entrée
            process = subprocess.Popen(
                self.piper_command,
                stdin=subprocess.PIPE,   # Fournir le texte via l'entrée standard
                stdout=subprocess.PIPE,  # Capturer l'audio brut
                stderr=subprocess.PIPE   # Capturer les erreurs
            )

            # Fournir le texte à Piper (texte long)
            process.stdin.write(text.encode("utf-8"))
            process.stdin.close()

            # Jouer l'audio brut avec PyAudio
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=sample_rate,
                            output=True)

            print("Lecture de l'audio en cours...")

            # Lire et jouer l'audio par chunks au fur et à mesure qu'ils sont générés
            while True:
                chunk = process.stdout.read(chunk_size)
                if not chunk:
                    break  # Si il n'y a plus de données, on arrête la lecture
                stream.write(chunk)

            # Fermer le flux PyAudio
            stream.stop_stream()
            stream.close()
            p.terminate()

            # Vérifier si des erreurs sont survenues dans le processus
            stderr = process.stderr.read()
            if stderr:
                print(f"Erreur lors de l'exécution de Piper : {stderr.decode()}")

            process.wait()  # Attendre la fin du processus
            return -1
        except Exception as e:
            print(f"Une erreur est survenue : {e}")
    

    def generate_speech_online(self, text):
        # Fonction online :
        if self.openai_client is None:
            print("Please, provide an OpenAPI key.")
            return None

        if not text or not isinstance(text, str):  # Vérifier que le texte est un string
            print("Invalid text input for speech generation.")
            return None

        try:
            response = self.openai_client.audio.speech.create(
                model="tts-1",  # Choix du modèle (Haute définition ou non)
                voice=self.voice,  # Choix de la voix
                input=text  # Texte pour l'audio
            )
            if response and hasattr(response, "content") and response.content:
                audio_content = response.content
                audio_stream = io.BytesIO(audio_content)
                audio_stream.seek(0)
                print("L'audio a bien été générée.")
                return audio_stream
            else:
                print("Aucun audio reçu de l'API")
                return None
        except Exception as e:
            print(f"Une erreur est survenue : {e}.")
            return None

    def play_audio(self, audio_stream):
        try:
            audio_stream.seek(0)
            audio = AudioSegment.from_file(audio_stream, format="mp3")
            print("Lecture de l'audio en cours...")
            play(audio)
        except Exception as e:
            print(f"Une erreur est survenue : {e}.")

    def transcribe_audio(self, audio_stream):
        if self.local_mode == True:
            return self.transcribe_audio_local(audio_stream)
        else:
            return self.transcribe_audio_online(audio_stream)

    def transcribe_audio_local(self, audio_stream):

        try:
            wf = audio_stream
            data = wf.raw_data
            if self.recognizer.AcceptWaveform(data):
                result = self.recognizer.Result()
                transcription = eval(result).get("text", "")
                return transcription

            final_result = self.recognizer.FinalResult()
            final_text = eval(final_result).get("text", "")

            if final_text:
                return final_text 
            else:
                print("Aucune transcription n'a pu être générée.")
                return None

        except Exception as e:
            print(f"Une erreur est survenue lors du traitement de l'audio : {e}")
            return None
        
    def transcribe_audio_online(self, filename):
        try:
            audio_file = open(filename, "rb")
            transcription = self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text",
                language="fr"
            )
            if transcription:
                if transcription.strip() == "Sous-titres réalisés para la communauté d'Amara.org" or transcription.strip() == "...":
                    print("Transcription indésirable détectée.")
                    return None
                return transcription
            else:
                print("La transcription est vide.")
                return None
        except Exception as e:
            print(f"Une erreur est survenue : {e}.")
            return None

    def is_silent(self, data, threshold=500):
        return np.abs(np.frombuffer(data, np.int16)).mean() < threshold

    def record_audio(self, chunk=1024, silent_limit=2, threshold=1000, save_to_file=False,
                     filename="output.wav"):
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=self.rate_in, input=True, frames_per_buffer=chunk)
        print("Enregistrement en cours.")
        frames = []
        silent_chunks = 0
        recording = True
        min_recording_duration = 2.5  # Durée minimale d'enregistrement en secondes
        start_time = time.time()

        while recording:
            data = stream.read(chunk)
            frames.append(data)
            if time.time() - start_time > min_recording_duration:
                if self.is_silent(data, threshold):
                    silent_chunks += 1
                else:
                    silent_chunks = 0

                if silent_chunks > int(silent_limit * self.rate_in / chunk):
                    print("Silence détecté, arrêt de l'enregistrement.")
                    recording = False

        print("Arrêt de l'enregistrement")
        stream.stop_stream()
        stream.close()
        p.terminate()

        audio_segment = AudioSegment(
            data=b''.join(frames),
            sample_width=p.get_sample_size(pyaudio.paInt16),
            frame_rate=self.rate_in,
            channels=1
        )

        if save_to_file: # changement en format wav nécessaire pour whisper
            audio_segment.export(filename, format="wav")
            return filename
        else: # pas de nécessité de changer de format pour piper
            return audio_segment

    import re

    def generate_text(self, prompt):
        """
        Génère une réponse en fonction du mode sélectionné (local ou online).
        """
        if self.local_mode:
            return self.generate_text_local(prompt)
        else:
            return self.generate_text_online(prompt)

    def generate_text_local(self, prompt):
        """
        Génère une réponse en utilisant le modèle fine-tuné TinyCortex.
        """
        try:
            # Préparer l'entrée du modèle avec la gestion de la troncature
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)

            # Générer la réponse en supprimant l'argument non reconnu
            outputs = self.model.generate(
                inputs["input_ids"],
                max_length=512,
                num_return_sequences=1,
                temperature=0.7,
                do_sample=True  # Suppression de l'argument to3p_p
            )

            # Décodage de la réponse générée
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Extraction de la réponse pertinente à l'aide de regex
            match = re.search(r"Réponse\s*:\s*(.*)", response, re.IGNORECASE)
            if match:
                response = match.group(1).strip()

            print("Réponse : " + response)
            print(execute_tool(response))
            return response

        except Exception as e:
            print(f"Erreur lors de la génération de texte : {e}")
            return "Une erreur s'est produite lors du traitement de votre requête."

    def generate_text_online(self, prompt):
        """
        Génère une réponse textuelle à partir d'un prompt en utilisant la RAG (Retrieval-Augmented Generation).
        Les informations du graphe Neo4j sont récupérées et intégrées dans le contexte avant l'appel à Mistral.
        """
        ai_response = None

        # Ajouter le message utilisateur au contexte
        self.messages.append({"role": "user", "content": prompt})

        # Étape 1 : Récupérer les informations de la base Neo4j (RAG)
        database = False
        if database : 
            try:
                db = Neo4jDatabase()
                graph_data = db.recuperer_informations_graph()

                # Ajouter les informations pertinentes récupérées du graphe dans le contexte
                if graph_data and "noeuds" in graph_data and "relations" in graph_data:
                    noeuds_info = "\n".join([f"{n['proprietes'].get('nom', 'Nœud sans nom')}: {n['proprietes']}" for n in
                                            graph_data["noeuds"].values()])
                    relations_info = "\n".join(
                        [f"{rel['type']} entre {rel['de']} et {rel['vers']}" for rel in graph_data["relations"]])
                    contexte_rag = f"Voici des informations provenant de la base de données:\nNœuds:\n{noeuds_info}\nRelations:\n{relations_info}"
                    self.messages.append({"role": "system", "content": contexte_rag})

                    #print(self.messages)

            except Exception as e:
                print(f"Erreur lors de la récupération des informations du graphe : {e}")

        # Étape 2 : Appel à Mistral pour générer la réponse basée sur le contexte
        try:
            chat_response = self.mistral_client.chat.complete(
                model=self.mistral_model,
                messages=self.messages,
                tools=self.tools,  # Inclure les outils pour permettre à Mistral d'appeler des fonctions
                tool_choice="auto"
            )

            #print(chat_response)

            # Vérification et extraction de l'appel de fonction
            tool_call = chat_response.choices[0].message.tool_calls

            if tool_call:
                function_name = tool_call[0].function.name
                #print(function_name)
                function_params = json.loads(tool_call[0].function.arguments)

                try:
                    # Vérifie si la fonction existe dans le dictionnaire names_to_functions
                    if function_name in names_to_functions:
                        function_result = names_to_functions[function_name](**function_params)

                        #print(function_result)

                        # Ajouter le résultat de la fonction comme un message utilisateur pour continuer le contexte
                        self.messages.append({"role": "user",
                                              "content": f"Résultat de la fonction '{function_name}': {function_result}"})

                        # Appel de Mistral pour générer une réponse finale avec le contexte mis à jour
                        chat_response_2 = self.mistral_client.chat.complete(
                            model=self.mistral_model,
                            messages=self.messages,
                        )

                        ai_response = chat_response_2.choices[0].message.content
                        self.messages.append({"role": "assistant", "content": ai_response})

                    else:
                        print(f"La fonction '{function_name}' n'existe pas dans le dictionnaire.")
                except Exception as e:
                    print(f"Erreur lors de l'exécution de la fonction '{function_name}': {e}")

            else:
                # Récupération de la réponse de l'IA
                ai_response = chat_response.choices[0].message.content
                self.messages.append({"role": "assistant", "content": ai_response})
                return ai_response
            print(ai_response)
            return ai_response

        except Exception as e:
            print(f"Erreur lors de l'appel à Mistral : {e}")
            if hasattr(e, 'data'):
                print(f"Détails de l'erreur : {e.data}")
            return "Désolé, une erreur est survenue lors de la génération de texte."

    def add_to_database(self, user_response, ai_response):
        """
        Utilise Mistral pour ajouter des informations supplémentaires dans la base de données via Neo4j.
        """
        db = Neo4jDatabase()

        choice = "auto"

        keywords_any = ["retiens", "sauvegarde", "enregistre", "ajoute", "intègre", "insère"]

        if any(keyword in user_response.lower() for keyword in keywords_any):
            choice = "any"

        # Prompt pour guider l'IA dans l'utilisation de la fonction
        prompt = (
            f"Si tu apprends de nouvelles informations sur l'utilisateur ou que tu dois ajouter des informations, "
            f"utilise absolument les tools (outils), et en particulier la fonction ajouter_entite_et_relation() "
            f"pour les intégrer dans la base de données Neo4j. "
            f"Utilise les informations fournies dans {user_response} et {ai_response} pour compléter la base de données. "
            f"Ajoute des nœuds et des relations pour enrichir les données de l'utilisateur."
            f"\nVérifie toujours si des nœuds similaires existent déjà dans la base avant d'en créer de nouveaux. "
            f"Voici les nœuds et relations actuellement présents dans la base de données : {str(db.recuperer_informations_graph())}. "
            f"Réutilise les nœuds existants si nécessaire."
            f"\nSi tu ne peux pas ajouter ces informations toi-même, utilise la fonction ajouter_entite_et_relation() pour effectuer cette action."
        )

        # Ajouter le message à la conversation
        self.messages.append({"role": "user", "content": prompt})

        # Nom de la fonction cible
        function_name_db = "ajouter_entite_et_relation"

        # Définition de l'outil en JSON
        tool_json = {
            "type": "function",
            "function": {
                "name": "ajouter_entite_et_relation",
                "description": ("Ajoute une entité et, si spécifié, une relation avec une autre entité. "
                                "Si l'entité ou la relation cible n'existe pas, elles seront créées. "
                                "Si relation_inverse est True, on inverse la direction de la relation. "
                                "Exemple : entite='ActiviteSportive', proprietes={'nom': 'Natation', 'duree': '1h'}, "
                                "relation='PRATIQUE', cible_relation='Personne', "
                                "proprietes_relation={'prenom': 'Thomas', 'nom': 'Respaut'}, "
                                "relation_inverse=True"),
                "parameters": {
                    "entite": {
                        "type": "string",
                        "description": "Le type d'entité à créer ou à vérifier (par exemple: ActiviteSportive, Lieu, etc.)."
                    },
                    "proprietes": {
                        "type": "object",
                        "description": "Un dictionnaire contenant les propriétés de l'entité à créer (par exemple: nom, description, duree)."
                    },
                    "relation": {
                        "type": "string",
                        "description": "Le type de relation à établir entre l'entité et l'entité cible (par exemple: PRATIQUE, VIT_A, AIME)."
                    },
                    "cible_relation": {
                        "type": "string",
                        "description": "Le type de l'entité cible avec laquelle la relation sera créée (par exemple: Personne, Plat, Lieu, etc.)."
                    },
                    "proprietes_relation": {
                        "type": "object",
                        "description": "Un dictionnaire contenant les propriétés de l'entité cible pour établir une correspondance (par exemple: nom, prenom pour une Personne)."
                    },
                    "relation_inverse": {
                        "type": "boolean",
                        "description": "Indique si la relation doit être inversée. Si True, la relation ira de l'entité cible vers l'entité principale."
                    }
                }
            }
        }

        try:
            # Appel à l'API Mistral pour obtenir une réponse de l'IA
            chat_response = self.mistral_client.chat.complete(
                model=self.mistral_model,
                messages=self.messages,
                tools=[tool_json],  # Utilisation de l'outil Neo4j en JSON
                tool_choice=choice
            )


            # Extraction de l'appel de fonction (tool call)
            tool_call = chat_response.choices[0].message.tool_calls

            if tool_call:
                # Si un appel de fonction a été généré
                function_name = tool_call[0].function.name
                function_params = json.loads(tool_call[0].function.arguments)

                try:
                    # Vérifie si la fonction appelée correspond à "ajouter_entite_et_relation"
                    if function_name_db == function_name:
                        # Vérifier que l'entité principale et l'entité cible ne soient pas les mêmes
                        if function_params["proprietes_relation"] == function_params["proprietes"]:
                            return "Erreur : L'entité principale et l'entité cible ne peuvent pas être les mêmes."

                        # Exécute la fonction avec les paramètres extraits
                        function_result = db.ajouter_entite_et_relation(**function_params)

                        print(
                            f"Exécution de la fonction 'ajouter_entite_et_relation' avec les paramètres : {function_params}")
                        return f"Informations ajoutées : {function_result}"
                    else:
                        return f"La fonction '{function_name}' n'existe pas dans le dictionnaire."
                except Exception as e:
                    return f"Erreur lors de l'exécution de la fonction '{function_name}': {e}"

            else:
                return "(Pas d'informations ajoutées à la BDD.)"

        except Exception as e:
            print(f"Erreur lors de l'appel à Mistral : {e}")
            if hasattr(e, 'data'):
                print(f"Détails de l'erreur : {e.data}")
            return "Désolé, une erreur est survenue lors de la génération de l'utilisation du tool."

    def keyword_detection(self):

        access_key = os.getenv('picovoice_api_key')
        keyword_path = "porcupine/Ok-Cortex.ppn"

        porcupine = pvporcupine.create(access_key=access_key, keyword_paths=[keyword_path],
                                       model_path="porcupine/porcupine_params_fr.pv")

        pa = pyaudio.PyAudio()
        audio_stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length
        )

        while True:
            pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = np.frombuffer(pcm, dtype=np.int16)
            result = porcupine.process(pcm)
            if result >= 0:
                audio_stream.close()
                porcupine.delete()
                return True

    def wait_for_response(self, silent_limit=1):
        print("Le micro est activé, attente d'une réponse de l'utilisateur...")
        save_to_file = not self.local_mode
        audiosegment = self.record_audio(save_to_file=save_to_file, silent_limit=silent_limit, threshold=500)
        if audiosegment:
            user_response = self.transcribe_audio(audiosegment)
            if user_response and user_response.strip():
                return user_response

        print("Aucune réponse détectée pendant 5 secondes, retour à la détection du mot clé.")
        return None

    def conversation(self):

        while True:
            user_response = None

            if self.input_mode == "voice":
                if self.first_keyword_detection:
                    print("Ok Cortex pour démarrer...")  # Message de démarrage
                    if not self.keyword_detection():
                        continue
                    self.first_keyword_detection = False

                user_response = self.wait_for_response()

                if user_response:
                    print(f"Utilisateur : {user_response}")
                    
                else:
                    self.first_keyword_detection = True
                    continue
                
            else : 
                user_response = input("Utilisateur : ")

                if user_response.lower() in ["quit", "stop", "exit"]:
                    print("Conversation terminée.")
                    break

            if not user_response:
                continue
            
            ai_response = self.generate_text(user_response)

            if ai_response:
                #print(self.add_to_database(user_response,ai_response))
                print(f"Cortex : {ai_response}")

                if self.output_mode == "voice":
                    if isinstance(ai_response, str) and ai_response.strip():
                        audio_stream = self.generate_speech(ai_response)
                        if audio_stream:
                            if audio_stream != -1:
                                self.play_audio(audio_stream)

                        else:
                            print("Impossible de générer l'audio.")
            print("-" * 100)


if __name__ == "__main__":
    cortex = Cortex(input_mode="voice",output_mode="voice",local_mode=True)
    cortex.conversation()
    
