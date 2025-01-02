# Exemple concret de question/réponse
# Message utilisateur et réponse du LLM sous forme d'un cas réel
# Implémentation du système d'exécution
import re
from assistant.films_and_series import films_and_series
from assistant.spotify.spotify_assistant import SpotifyAssistant
from assistant.ratp.ratp_assistant import IDFMAssistant
from assistant import functions
from assistant.apple.iphone import AppleAssistant
from assistant.google.google_assistant import GoogleAssistant
import json

# Instancier les assistants Spotify, Apple, IDFM et Google
spotify_assistant = SpotifyAssistant()
apple_assistant = AppleAssistant()
idfm_assistant = IDFMAssistant()
google_assistant = GoogleAssistant()

# Créer le dictionnaire de fonctions en utilisant les instances des assistants
TOOLS = {
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
    # Adapter l'appel de get_weather pour gérer les arguments non prévus
    'get_weather': lambda **kwargs: apple_assistant.get_weather(),
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

def execute_tool(response):
    """
    Analyse et exécute la commande reçue dans la réponse.
    :param response: Chaîne contenant une phrase et une commande au format [tool_name arguments]
    """
    # Extraire la commande de la réponse
    match = re.search(r'\[(\w+)(.*?)\]', response)
    if not match:
        return "Aucune commande reconnue dans la réponse."


    # Récupérer le nom de l'outil et les arguments
    tool_name = match.group(1)
    raw_args = match.group(2).strip()

    # Convertir les arguments en dictionnaire si présents
    args = {}
    if raw_args:
        matches = re.findall(r"(\w+)=([\'\"].+?[\'\"]|[^\s]+)", raw_args)
        args = {
            key: int(value.strip().strip("'\"")) if value.strip().strip("'\"").isdigit() else value.strip().strip("'\"")
            for key, value in matches
        }

    # Debugging :
    #for arg, value in args.items():
    #    print(f"{arg}: {value}")

    print(f"Arguments extraits: {args}")  # Debugging des arguments

    # Exécute la commande si l'outil est reconnu
    if tool_name in TOOLS:
        try:
            result = TOOLS[tool_name](**args)
            return result
        except TypeError as e:
            # Réessayer sans arguments si l'outil ne les accepte pas
            try:
                result = TOOLS[tool_name]()
                return result
            except Exception as retry_e:
                print(f"Erreur d'exécution pour l'outil '{tool_name}' lors de la nouvelle tentative: {retry_e}")
        except Exception as e:
            print(f"Erreur d'exécution pour l'outil '{tool_name}': {e}")
    else:
        print(f"Outil '{tool_name}' non reconnu.")

def execute_file(input_file,output_file):
    # Récupérer les données:
    data = json.load(open(input_file, encoding="utf-8"))

    taille = len(data)
    compteur = 0

    for item in data:
        response = item["response"]
        print(response)

        # Demander une confirmation utilisateur avant d'exécuter
        user_input = input(f"Voulez-vous exécuter cette commande : {response} ? (oui/non)\n")
        if user_input.strip().lower() == 'oui':
            # Exécution de l'exemple concret
            result = execute_tool(response)
            print(result)
        else:
            print("Commande ignorée.")

        print()

if __name__ == "__main__":

    # Générer et sauvegarder des questions/réponses
    input_file = "training/tinyollama/function_calling/training_function_calling.json"
    output_file = "training_function_calling.json"
    #execute_file(input_file,output_file)

    # Message utilisateur : Quelle est la météo à Paris ?
    response = "[play_track track_name='sois pas timide']"
    print(execute_tool(response))



