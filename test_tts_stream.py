import subprocess
import pyaudio

def synthesize_and_play_audio_with_piper(text, piper_path, model_path, sample_rate=22050, chunk_size=1024):
    """
    Génère et lit l'audio d'un texte long par chunks en utilisant Piper et PyAudio.

    Args:
        text (str): Le texte à convertir en audio.
        piper_path (str): Chemin vers l'exécutable Piper (ex: './piper').
        model_path (str): Chemin vers le modèle ONNX pour Piper (ex: './fr_FR-upmc-medium.onnx').
        sample_rate (int): Fréquence d'échantillonnage pour l'audio brut (par défaut : 22050 Hz).
        chunk_size (int): Taille du chunk d'audio à lire à chaque itération (par défaut : 1024 octets).
    
    Returns:
        None
    """
    try:
        # Commande Piper pour streamer l'audio brut
        piper_command = [
            piper_path,            # Chemin vers l'exécutable Piper
            "--model", model_path, # Modèle ONNX
            "--output-raw"         # Streamer l'audio brut via stdout
        ]

        # Lancer Piper avec le texte fourni en entrée
        process = subprocess.Popen(
            piper_command,
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


PIPER_PATH = "piper/piper.exe"  # Chemin vers l'exécutable Piper
MODEL_PATH = "piper/fr_FR-upmc-medium.onnx"  # Chemin vers le modèle ONNX
TEXT = "L'intelligence artificielle est un domaine de l'informatique "   # Un texte long pour tester"

# Appeler la fonction pour générer et jouer l'audio
a = synthesize_and_play_audio_with_piper(TEXT, PIPER_PATH, MODEL_PATH)
print(a)