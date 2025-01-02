# Exemple concret de question/réponse
# Message utilisateur et réponse du LLM sous forme d'un cas réel

# Message utilisateur : Quelle est la météo à Paris ?
response = "[get_weather location=Paris]"

# Implémentation du système d'exécution
import re

def execute_tool(response):
    """
    Analyse et exécute la commande reçue dans la réponse.
    :param response: Chaîne contenant une phrase et une commande au format [tool_name arguments]
    """
    TOOLS = {
        "get_current_time": lambda: print("Il est 15h30."),
        "get_weather": lambda location, temperature_unit=None: print(f"La météo à {location} est ensoleillée avec une unité de température en {temperature_unit}.") ,
        "set_alarm": lambda time, date: print(f"Alarme réglée pour {date} à {time}.")
    }

    # Extraire la commande de la réponse
    match = re.search(r'\[(\w+)(.*?)\]', response)
    if not match:
        print("Aucune commande reconnue dans la réponse.")
        return

    # Récupérer le nom de l'outil et les arguments
    tool_name = match.group(1)
    raw_args = match.group(2).strip()

    # Convertir les arguments en dictionnaire si présents
    args = {}
    if raw_args:
        args = {
            key: value.strip() for key, value in re.findall(r'(\w+)=([\w\s]+)', raw_args)
        }

    # Exécute la commande si l'outil est reconnu
    if tool_name in TOOLS:
        try:
            TOOLS[tool_name](**args)
        except TypeError as e:
            print(f"Erreur d'exécution pour l'outil '{tool_name}': {e}")
    else:
        print(f"Outil '{tool_name}' non reconnu.")

# Exécution de l'exemple concret
execute_tool(response)
