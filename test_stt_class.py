import os
import wave
import vosk

class VoskTranscriber:
    def __init__(self, model_path, sample_rate=44100):
        """
        Initialise le transcripteur Vosk avec le modèle spécifié.
        
        Args:
            model_path (str): Chemin du modèle Vosk.
            sample_rate (int): Taux d'échantillonnage audio (par défaut 44100 Hz).
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Le modèle {model_path} est introuvable. Téléchargez-le et extrayez-le correctement.")
        
        print("Chargement du modèle...")
        self.model = vosk.Model(model_path)
        self.recognizer = vosk.KaldiRecognizer(self.model, sample_rate)
        self.sample_rate = sample_rate
    
    def transcribe_audio_whole(self, filename):
        """
        Transcrit un fichier audio complet sans le diviser en blocs.
        
        Args:
            filename (str): Le chemin du fichier audio 
        
        Returns:
            str: Texte transcrit ou un message d'erreur.
        """
        if not os.path.exists(filename):
            return f"Erreur : Le fichier {filename} est introuvable."
        
        try:
            with wave.open(filename, "rb") as wf:
                if wf.getnchannels() != 1:
                    return "Erreur : Le fichier audio doit être mono (1 canal)."
                
                print(f"Taux d'échantillonnage du fichier : {wf.getframerate()} Hz")
                data = wf.readframes(wf.getnframes())
                
                if self.recognizer.AcceptWaveform(data):
                    result = self.recognizer.Result()
                    transcription = eval(result).get("text", "")
                    return transcription
                
                final_result = self.recognizer.FinalResult()
                final_text = eval(final_result).get("text", "")
                return final_text if final_text else "Aucune transcription n'a pu être générée."
        
        except Exception as e:
            return f"Une erreur est survenue lors du traitement de l'audio : {e}"
        
        
MODEL_PATH = "vosk-model-small-fr-0.22"
FILENAME = "output.wav"

# Création d'une instance de la classe
transcriber = VoskTranscriber(MODEL_PATH)

# Transcription d'un fichier audio
transcription = transcriber.transcribe_audio_whole(FILENAME)
print("Transcription :", transcription)

