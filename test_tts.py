import subprocess
import pyaudio

def synthesize_and_play_audio_with_piper(text, piper_path, model_path, sample_rate=44100):
    """
    Génère et lit un audio directement à partir d'un texte en utilisant Piper avec PyAudio.

    Args:
        text (str): Le texte à convertir en audio.
        piper_path (str): Chemin vers l'exécutable Piper (ex: './piper').
        model_path (str): Chemin vers le modèle ONNX pour Piper (ex: './fr_FR-upmc-medium.onnx').
        sample_rate (int): Fréquence d'échantillonnage pour l'audio brut (par défaut : 22050 Hz).
    
    Returns:
        None
    """
    filename = "output.wav"
    try:
        # Commande Piper pour streamer l'audio brut
        piper_command = [
            piper_path,           # Chemin vers l'exécutable Piper
            "--model", model_path,  # Modèle ONNX
            "--output_file", filename          
        ]

        # Lancer Piper avec le texte fourni en entrée
        process = subprocess.Popen(
            piper_command,
            stdin=subprocess.PIPE,   # Fournir le texte via l'entrée standard
            stderr=subprocess.PIPE   # Capturer les erreurs
        )

        # Fournir le texte à Piper
        stderr = process.communicate(input=text.encode("utf-8"))

        # Gérer les erreurs éventuelles
        if process.returncode != 0:
            raise RuntimeError(f"Erreur lors de l'exécution de Piper : {stderr.decode()}")
        else:
            return filename
    except Exception as e:
        print(f"Une erreur est survenue : {e}")


PIPER_PATH = "piper/piper.exe"  # Chemin vers l'exécutable Piper
MODEL_PATH = "piper/fr_FR-upmc-medium.onnx"  # Chemin vers le modèle ONNX
TEXT = "L'intelligence artificielle est un domaine de l'informatique qui se concentre sur la création de systèmes capables de simuler des processus cognitifs humains. Elle englobe diverses sous-disciplines, telles que l'apprentissage automatique, la vision par ordinateur, le traitement du langage naturel et la robotique. Au fil des années, l'intelligence artificielle a considérablement évolué, offrant des applications pratiques dans de nombreux secteurs, notamment la santé, l'automobile, la finance et les services clients. Les progrès dans ce domaine continuent de transformer le monde numérique et physique, ouvrant la voie à de nouvelles innovations et défis. L'intelligence artificielle pose également des questions éthiques et philosophiques sur la relation entre l'homme et la machine, ainsi que sur les implications de son utilisation dans la société. Par conséquent, le développement responsable et la régulation de l'intelligence artificielle sont des enjeux majeurs pour les chercheurs, les gouvernements et les entreprises"   # Un texte long pour tester"

# Appeler la fonction pour générer et jouer l'audio
synthesize_and_play_audio_with_piper(TEXT, PIPER_PATH, MODEL_PATH)