import os
import wave
import vosk

MODEL_PATH = "vosk-model-small-fr-0.22"  # Chemin vers le dossier du modèle

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Le modèle {MODEL_PATH} est introuvable. Téléchargez-le et extrayez-le correctement.")

print("Chargement du modèle...")
model = vosk.Model(MODEL_PATH)
recognizer = vosk.KaldiRecognizer(model, 44100)

def transcribe_audio_whole(filename):
    """
    Fonction pour transcrire un fichier audio complet sans le diviser en blocs.
    
    Args:
        filename (str): Le chemin du fichier audio à traiter.
    
    Returns:
        str: Le texte transcrit à partir de l'audio, ou un message d'erreur.
    """
    if not os.path.exists(filename):
        return f"Erreur : Le fichier {filename} est introuvable."

    try:
        with wave.open(filename, "rb") as wf:
            if wf.getnchannels() != 1:
                return "Erreur : Le fichier audio doit être mono (1 canal)."
            
            #recognizer = vosk.KaldiRecognizer(model, 44100)
            print(wf.getframerate())
            data = wf.readframes(wf.getnframes())  # Lire tout le fichier d'un coup

            if recognizer.AcceptWaveform(data):
                result = recognizer.Result()
                transcription = eval(result).get("text", "")
                return transcription

            final_result = recognizer.FinalResult()
            final_text = eval(final_result).get("text", "")
            return final_text if final_text else "Aucune transcription n'a pu être générée."

    except Exception as e:
        return f"Une erreur est survenue lors du traitement de l'audio : {e}"

# Exemple d'utilisation
filename = "output.wav"
transcription = transcribe_audio_whole(filename)
print("Transcription :", transcription)
