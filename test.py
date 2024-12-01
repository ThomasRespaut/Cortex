import os
import requests
from dotenv import load_dotenv
from datetime import datetime

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()


class IDFMAssistant:
    def __init__(self):
        self.idfm_api_key = os.getenv('IDFM_API_KEY')


    # Fonction pour obtenir les coordonnées GPS d'une ville donnée
    def get_coords(self,city_name):
        url_places = "https://prim.iledefrance-mobilites.fr/marketplace/v2/navitia/places"

        # Paramètres de la requête
        params_places = {
            'q': city_name,  # Nom de la ville passée en paramètre
        }

        headers = {
            'Accept': 'application/json',
            'apikey': self.idfm_api_key
        }

        # Envoyer la requête
        response_places = requests.get(url_places, params=params_places, headers=headers)

        # Vérifier si la requête a réussi
        if response_places.status_code == 200:
            data_places = response_places.json()

            # Parcourir les résultats
            for place in data_places['places']:
                name = place.get('name', 'Nom non disponible')
                embedded_type = place.get('embedded_type', 'Type non disponible')

                # Vérifier les différentes sources de coordonnées
                if 'coord' in place:
                    coord = place['coord']
                elif 'stop_area' in place and 'coord' in place['stop_area']:
                    coord = place['stop_area']['coord']
                elif 'address' in place and 'coord' in place['address']:
                    coord = place['address']['coord']
                else:
                    coord = None

                # Retourner les coordonnées si disponibles
                if coord:
                    return {'lat': coord['lat'], 'lon': coord['lon']}
        else:
            print(f"Erreur {response_places.status_code} : {response_places.text}")

        return None

    from datetime import datetime

    def calculate_route(self, from_city, to_city):
        # Récupérer les coordonnées GPS des villes
        from_coords = self.get_coords(from_city)
        to_coords = self.get_coords(to_city)

        if from_coords and to_coords:
            # URL de l'API pour calculer un itinéraire
            url_journey = "https://prim.iledefrance-mobilites.fr/marketplace/v2/navitia/journeys"

            # Récupérer la date et l'heure actuelles
            current_datetime = datetime.now().strftime('%Y%m%dT%H%M%S')

            # Paramètres pour la requête d'itinéraire
            params_journey = {
                'from': f"{from_coords['lon']};{from_coords['lat']}",
                'to': f"{to_coords['lon']};{to_coords['lat']}",
                'datetime': current_datetime,  # Utiliser la date et l'heure actuelles
                'datetime_represents': 'departure',
                'max_nb_journeys': 1
            }

            # En-têtes de la requête
            headers = {
                'Accept': 'application/json',
                'apikey': self.idfm_api_key
            }

            # Envoi de la requête pour calculer l'itinéraire
            response_journey = requests.get(url_journey, params=params_journey, headers=headers)

            # Vérification du statut de la requête
            if response_journey.status_code == 200:
                data_journey = response_journey.json()
                itineraries = []

                # Pour chaque itinéraire trouvé
                for journey in data_journey['journeys']:
                    itinerary = {
                        'departure_time': journey['departure_date_time'],
                        'arrival_time': journey['arrival_date_time'],
                        'duration': journey['duration'],
                        'co2_emission': journey.get('co2_emission', {}).get('value', 'Non disponible'),
                        'nb_transfers': journey.get('nb_transfers', 0),
                        'walking_distance': journey.get('distances', {}).get('walking', 'Non disponible'),
                        'fare': journey.get('fare', {}).get('total', {}).get('value', 'Non disponible'),
                        'currency': journey.get('fare', {}).get('total', {}).get('currency', 'Non disponible'),
                        'sections': []
                    }

                    # Ajouter les sections (étapes) de l'itinéraire
                    for section in journey['sections']:
                        section_info = {
                            'type': section['type'],
                            'mode': section.get('mode', 'Non spécifié'),
                            'from_name': section.get('from', {}).get('name', 'Point de départ inconnu'),
                            'to_name': section.get('to', {}).get('name', 'Destination inconnue'),
                            'section_duration': section['duration']
                        }
                        itinerary['sections'].append(section_info)

                    itineraries.append(itinerary)

                return itineraries
            else:
                return f"Erreur {response_journey.status_code} : {response_journey.text}"

        else:
            return "Impossible de récupérer les coordonnées GPS pour les villes spécifiées."


if __name__ == "__main__":

    IDFMAssistant = IDFMAssistant()
    # Récupérer les noms des villes de départ et d'arrivée
    from_city = input("Entrez la ville de départ : ")
    to_city = input("Entrez la ville d'arrivée : ")

    result = IDFMAssistant.calculate_route(from_city, to_city)

    print(result)
