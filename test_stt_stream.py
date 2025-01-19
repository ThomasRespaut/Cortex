import os
import pyaudio
import vosk
# Initialisation du modèle
MODEL_PATH = "vosk-model-small-fr-0.22"  # Chemin vers le dossier du modèle

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Le modèle {MODEL_PATH} est introuvable. Téléchargez-le et extrayez-le correctement.")

print("Chargement du modèle...")
model = vosk.Model(MODEL_PATH)
recognizer = vosk.KaldiRecognizer(model, 16000)  # Fréquence d'échantillonnage à 16 kHz

# Configuration de l'entrée audio
audio = pyaudio.PyAudio()
stream = audio.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    frames_per_buffer=1024)

stream.start_stream()
print("Modèle chargé avec succès. Parlez dans le microphone...")

try:
    while True:
        data = stream.read(4000, exception_on_overflow=False)  # Lire les données audio en blocs
        if recognizer.AcceptWaveform(data):  # Reconnaissance sur le flux audio
            result = recognizer.Result()
            transcription = eval(result).get("text", "")  # Obtenir uniquement le texte
            if transcription:
                print(f"Transcription : {transcription}")
        else:
            partial_result = recognizer.PartialResult()
            partial_transcription = eval(partial_result).get("partial", "")
            if partial_transcription:
                print(f"Transcription partielle : {partial_transcription}", end="\r")
except KeyboardInterrupt:
    print("\nArrêt du programme.")
finally:
    stream.stop_stream()
    stream.close()
    audio.terminate()
