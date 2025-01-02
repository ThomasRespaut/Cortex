# functions.py
from datetime import datetime
import random

# Fonction pour obtenir l'heure actuelle
def get_current_time():
    current_time = datetime.now().strftime("%H:%M:%S")
    #print(f"Heure actuelle : {current_time}")
    return current_time

# Fonction pour générer un nombre aléatoire dans une plage
def generate_random_number(min_value, max_value):
    if int(min_value) > int(max_value):
        print("Erreur : min_value doit être inférieur ou égal à max_value.")
        return None
    random_number = random.randint(min_value, max_value)
    return random_number

