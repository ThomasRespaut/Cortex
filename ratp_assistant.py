import os
import requests
from dotenv import load_dotenv
from datetime import datetime

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Récupérer la clé API depuis les variables d'environnement
IDFM_API_KEY = os.getenv('IDFM_API_KEY')

# URL de l'API pour récupérer les informations des arrêts
url_arrets = "https://data.iledefrance-mobilites.fr/api/records/1.0/search/"

# URL de l'API pour récupérer les données en temps réel
url_real_time = "https://prim.iledefrance-mobilites.fr/marketplace/stop-monitoring"

arret = input("Arret : ")

# Paramètres pour récupérer les arrêts de La Défense
params_arrets = {
    'dataset': 'arrets',
    'q': arret,
    'rows': 10  # Limite à 10 résultats pour l'exemple
}

# Fonction pour convertir l'heure au format lisible
def convert_to_readable_time(iso_time_str):
    try:
        # Convertir la chaîne ISO en objet datetime
        dt = datetime.fromisoformat(iso_time_str.replace("Z", "+00:00"))
        # Retourner un format lisible
        return dt.strftime("%d %B %Y à %H:%M")
    except ValueError:
        return 'Heure non disponible'

# Envoi de la requête pour récupérer les arrêts
response_arrets = requests.get(url_arrets, params=params_arrets)

# Vérification du statut de la requête
if response_arrets.status_code == 200:
    # Afficher les résultats de la requête
    data_arrets = response_arrets.json()

    for record in data_arrets['records']:
        # Récupérer les informations de l'arrêt
        stop_name = record['fields'].get('arrname', 'Nom d\'arrêt non disponible')
        stop_id = record['fields'].get('arrid', 'ID non disponible')
        stop_geopoint = record['fields'].get('arrgeopoint', [None, None])
        stop_lon, stop_lat = stop_geopoint if stop_geopoint else ('Longitude non disponible', 'Latitude non disponible')
        stop_town = record['fields'].get('arrtown', 'Ville non disponible')
        postal_region = record['fields'].get('arrpostalregion', 'Région non disponible')

        #print(f"Nom de l'arrêt: {stop_name}")
        #print(f"ID de l'arrêt: {stop_id}")
        #print(f"Longitude: {stop_lon}")
        #print(f"Latitude: {stop_lat}")
        #print(f"Ville: {stop_town}")
        #print(f"Région postale: {postal_region}")
        #print("----")

        # Utiliser l'ID de l'arrêt pour récupérer les données en temps réel
        monitoring_ref = f"STIF:StopPoint:Q:{stop_id}:"  # Ajout du ":" à la fin du MonitoringRef
        params_real_time = {
            'MonitoringRef': monitoring_ref,  # Utilisation du MonitoringRef
        }

        headers = {
            'Accept': 'application/json',
            'apikey': IDFM_API_KEY  # Utilisation de la clé API
        }

        # Requête pour les informations en temps réel
        response_real_time = requests.get(url_real_time, params=params_real_time, headers=headers)

        if response_real_time.status_code == 200:
            data_real_time = response_real_time.json()

            # Afficher les détails complets de la réponse (delivery)
            for delivery in data_real_time['Siri']['ServiceDelivery']['StopMonitoringDelivery']:
                for monitored_visit in delivery.get('MonitoredStopVisit', []):
                    recorded_time = monitored_visit.get('RecordedAtTime', 'Non disponible')
                    expected_arrival_time = convert_to_readable_time(monitored_visit['MonitoredVehicleJourney']['MonitoredCall'].get('ExpectedArrivalTime', 'Heure non disponible'))
                    expected_departure_time = convert_to_readable_time(monitored_visit['MonitoredVehicleJourney']['MonitoredCall'].get('ExpectedDepartureTime', 'Heure non disponible'))
                    line_ref = monitored_visit['MonitoredVehicleJourney']['LineRef'].get('value', 'Ligne non disponible')
                    direction = monitored_visit['MonitoredVehicleJourney']['DirectionName'][0].get('value', 'Direction non disponible')
                    stop_point_name = monitored_visit['MonitoredVehicleJourney']['MonitoredCall']['StopPointName'][0].get('value', 'Nom arrêt non disponible')
                    destination_name = monitored_visit['MonitoredVehicleJourney']['DestinationName'][0].get('value', 'Destination non disponible')

                    # Vérifier si l'heure d'arrivée et de départ sont identiques
                    if expected_arrival_time == expected_departure_time:
                        print(f"Enregistrement à: {recorded_time}")
                        print(f"Ligne: {line_ref}")
                        print(f"Direction: {direction}")
                        print(f"Destination: {destination_name}")
                        print(f"Nom de l'arrêt: {stop_point_name}")
                        print(f"Heure prévue: {expected_arrival_time}")
                    else:
                        print(f"Enregistrement à: {recorded_time}")
                        print(f"Ligne: {line_ref}")
                        print(f"Direction: {direction}")
                        print(f"Destination: {destination_name}")
                        print(f"Nom de l'arrêt: {stop_point_name}")
                        print(f"Heure prévue d'arrivée: {expected_arrival_time}")
                        print(f"Heure prévue de départ: {expected_departure_time}")
                    print("----")
        else:
            print(f"Erreur lors de la récupération des informations temps réel pour l'arrêt {stop_id}")
else:
    print(f"Erreur lors de la requête des arrêts : {response_arrets.status_code}")
