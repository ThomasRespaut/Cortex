from openai import OpenAI  # Pour TTS et STT
from mistralai import Mistral
import io
from pydub import AudioSegment
from pydub.playback import play
import pvporcupine
import pyaudio
import numpy as np
import os
from dotenv import load_dotenv
import time
import json


from functools import partial
import functions  # Importer les fonctions du fichier functions.py

names_to_functions = {
    'get_current_time': functions.get_current_time,  # Appelle la fonction get_current_time sans arguments.
    'generate_random_number': functions.generate_random_number  # Appelle la fonction avec les paramètres fournis.
}

load_dotenv()

class Cortex:
    def __init__(self,input_mode="voice",output_mode="voice"):
        openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None
        self.voice = "echo"
        self.first_keyword_detection = True  # Détection du premier ok Cortex

        mistral_api_key = os.getenv('MISTRAL_API_KEY')
        self.mistral_client = Mistral(api_key=mistral_api_key) if mistral_api_key else None
        self.mistral_model = "open-mistral-nemo"

        with open("tools.json", "r") as file:
            self.tools = json.load(file)

        self.system = """
        Tu es Cortex, un assistant vocal intelligent et discret. Ton objectif est de fournir des réponses précises, courtes et utiles à l'utilisateur, sans rentrer dans les détails de ton fonctionnement ou de tes capacités. Comporte-toi comme un ami respectueux et serviable, prêt à aider sans donner d'explications inutiles sur toi-même. Réponds de manière simple et directe, sans rappeler que tu es un assistant. Reste concentré sur la question de l'utilisateur et sur la meilleure façon de l'aider immédiatement.
        """

        self.messages = [
            {"role": "system", "content": self.system},
        ]

        self.input_mode = input_mode
        self.output_mode = output_mode

    def generate_speach(self, text):
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
        try:
            audio_stream.seek(0)
            transcription = self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_stream,
                response_format="text",
                language="fr"
            )
            if transcription:
                if transcription.strip() == "Sous-titres réalisés para la communauté d'Amara.org":
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

    def record_audio(self, rate=44100, chunk=1024, silent_limit=2, threshold=1000, save_to_file=False,
                     filename="output.wav"):
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=rate, input=True, frames_per_buffer=chunk)
        print("Enregistrement en cours.")
        frames = []
        silent_chunks = 0
        recording = True
        min_recording_duration = 1  # Durée minimale d'enregistrement en secondes
        start_time = time.time()

        while recording:
            data = stream.read(chunk)
            frames.append(data)

            if time.time() - start_time > min_recording_duration:
                if self.is_silent(data, threshold):
                    silent_chunks += 1
                else:
                    silent_chunks = 0

                if silent_chunks > int(silent_limit * rate / chunk):
                    print("Silence détecté, arrêt de l'enregistrement.")
                    recording = False

        print("Arrêt de l'enregistrement")
        stream.stop_stream()
        stream.close()
        p.terminate()

        audio_segment = AudioSegment(
            data=b''.join(frames),
            sample_width=p.get_sample_size(pyaudio.paInt16),
            frame_rate=rate,
            channels=1
        )

        if save_to_file:
            audio_segment.export(filename, format="wav")
            return filename
        else:
            audio_stream = io.BytesIO()
            audio_segment.export(audio_stream, format="wav")
            audio_stream.seek(0)
            return audio_stream

    def generate_text(self, prompt):
        ai_response = None

        self.messages.append({"role": "user", "content": prompt})
        try:
            chat_response = self.mistral_client.chat.complete(
                model=self.mistral_model,
                messages=self.messages,
                tools=self.tools,
                tool_choice="auto"
            )

            # Vérification et extraction de l'appel de fonction
            tool_call = chat_response.choices[0].message.tool_calls

            if tool_call:
                function_name = tool_call[0].function.name
                function_params = json.loads(tool_call[0].function.arguments)

                try:
                    # Vérifie si la fonction existe dans le dictionnaire names_to_functions
                    if function_name in names_to_functions:
                        function_result = names_to_functions[function_name](**function_params)

                        # Ajoutez le résultat de la fonction comme un message de l'utilisateur pour continuer le contexte
                        self.messages.append({"role": "user",
                                              "content": f"Résultat de la fonction '{function_name}': {function_result}"})

                        # Rappeler l'API pour générer une réponse finale avec le contexte mis à jour
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

        except Exception as e:
            print(f"Erreur lors de l'appel à Mistral : {e}")
            if hasattr(e, 'data'):
                print(f"Détails de l'erreur : {e.data}")
            return "Désolé, une erreur est survenue lors de la génération de texte."

    def keyword_detection(self):
        access_key = os.getenv('picovoice_api_key')
        keyword_path = "Ok-Cortex.ppn"

        porcupine = pvporcupine.create(access_key=access_key, keyword_paths=[keyword_path],
                                       model_path="porcupine_params_fr.pv")

        pa = pyaudio.PyAudio()
        audio_stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length
        )

        #print("Conversation initialisé.")
        while True:
            pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = np.frombuffer(pcm, dtype=np.int16)
            result = porcupine.process(pcm)
            if result >= 0:
                audio_stream.close()
                porcupine.delete()
                return True

    def wait_for_response(self, timeout=5):
        print("Le micro est activé, attente d'une réponse de l'utilisateur...")
        filename = self.record_audio(save_to_file=True, silent_limit=0.5, threshold=500)
        if filename:
            with open(filename, "rb") as audio_file:
                user_response = self.transcribe_audio(audio_file)
                if user_response and user_response.strip():
                    return user_response

        print("Aucune réponse détectée pendant 5 secondes, retour à la détection du mot clé.")
        return None

    def conversation(self):

        print("Ok Cortex pour démarrer...")  # Message de démarrage
        while True:
            user_response = None

            if self.input_mode == "voice":
                if self.first_keyword_detection:
                    if not self.keyword_detection():
                        continue
                    self.first_keyword_detection = False

                user_response = self.wait_for_response()

                if user_response:
                    print(f"Utilisateur : {user_response}")
                else:
                    self.first_keyword_detection = True
                    continue

            if self.input_mode == "text":
                user_response = input("Utilisateur : ")

                if user_response.lower() in ["quit", "stop", "exit"]:
                    print("Conversation terminée.")
                    break

            if not user_response:
                continue

            ai_response = self.generate_text(user_response)
            print(f"Cortex : {ai_response}")

            if self.output_mode == "voice":
                if isinstance(ai_response, str) and ai_response.strip():
                    audio_stream = self.generate_speach(ai_response)
                    if audio_stream:
                        self.play_audio(audio_stream)
                    else:
                        print("Impossible de générer l'audio.")

            print("-" * 100)


if __name__ == "__main__":
    cortex = Cortex(input_mode = "text",output_mode = "text")
    cortex.conversation()
