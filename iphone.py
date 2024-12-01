import os
import requests
from pyicloud import PyiCloudService
from pyicloud.exceptions import PyiCloudFailedLoginException, PyiCloudAPIResponseException
from dotenv import load_dotenv

load_dotenv()

class AppleAssistant:
    def __init__(self):
        self.username = os.getenv("apple_username")
        self.password = os.getenv("apple_password")
        self.maps_api_key = os.getenv("MAPS_API_KEY")
        self.openweathermap_api_key = os.getenv("OPENWEATHERMAP_API_KEY")

        try:
            self.client = PyiCloudService(self.username, self.password)

            if self.client.requires_2fa:
                code = input("Entrez le code reçu : ")
                result = self.client.validate_2fa_code(code)
                if not result:
                    raise ValueError("Impossible de vérifier le code de sécurité.")

        except (PyiCloudFailedLoginException, PyiCloudAPIResponseException, ValueError) as e:
            self.client = None
            self.error_message = f"Erreur lors de la connexion à iCloud : {e}"

    def get_iphone_battery(self):
        if not self.client:
            return {"status": "error", "message": self.error_message}
        try:
            iphone_info = self.client.iphone.status()
            battery_level = iphone_info.get("batteryLevel", None)
            battery_message = f"Niveau de batterie : {battery_level * 100:.0f}%" if battery_level is not None else "Niveau de batterie indisponible"
            return {"status": "success", "battery_level": battery_message}
        except Exception as e:
            return {"status": "error", "message": f"Erreur lors de la récupération du niveau de batterie : {e}"}

    def get_location(self):
        if not self.client:
            return {"status": "error", "message": self.error_message}
        try:
            self.location = self.client.iphone.location()
            latitude = self.location.get("latitude", "0")
            longitude = self.location.get("longitude", "0")
            url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={latitude},{longitude}&key={self.maps_api_key}"
            response = requests.get(url)
            address_data = response.json()
            address = address_data["results"][0]["formatted_address"] if address_data["status"] == "OK" else "Adresse inconnue"
            return {"status": "success", "latitude": latitude, "longitude": longitude, "address": address}
        except Exception as e:
            return {"status": "error", "message": f"Erreur lors de la récupération de l'adresse : {e}"}

    def get_weather(self):
        location_result = self.get_location()
        if location_result["status"] == "error":
            return location_result
        try:
            latitude = location_result["latitude"]
            longitude = location_result["longitude"]
            url = f"http://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid={self.openweathermap_api_key}&units=metric"
            response = requests.get(url)
            weather = response.json()
            if weather['cod'] == 200:
                weather_main = weather['weather'][0]['main']
                weather_description = weather['weather'][0]['description']
                weather_temp = weather['main']["temp"]
                weather_message = f"Conditions météo : {weather_main}, {weather_description}. Température : {weather_temp}°C."
                return {"status": "success", "weather": weather_message}
            else:
                return {"status": "error", "message": "Informations météorologiques non disponibles."}
        except Exception as e:
            return {"status": "error", "message": f"Erreur lors de la récupération de la météo : {e}"}

    def get_contacts(self, name=None):
        if not self.client:
            return {"status": "error", "message": self.error_message}
        try:
            contacts = self.client.contacts.all()
            if name:
                contacts = [contact for contact in contacts if contact.get('firstName', '').lower().startswith(name.lower())]

            if not contacts:
                return {"status": "error", "message": f"Aucun contact trouvé dont le prénom commence par '{name}'."}

            contact_list = []
            for contact in contacts:
                first_name = contact.get('firstName', 'Prénom indisponible')
                last_name = contact.get('lastName', '')
                phones = [phone.get('field', 'Numéro indisponible') for phone in contact.get('phones', [])]
                emails = [email.get('field', 'Email indisponible') for email in contact.get('emails', [])]
                contact_info = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "phones": phones,
                    "emails": emails
                }
                contact_list.append(contact_info)

            return {"status": "success", "contacts": contact_list}
        except Exception as e:
            return {"status": "error", "message": f"Erreur lors de la récupération des contacts : {e}"}

    def play_sound_on_iphone(self):
        if not self.client:
            return {"status": "error", "message": self.error_message}
        try:
            self.client.iphone.play_sound()
            return {"status": "success", "message": "Le son a été joué sur l'iPhone."}
        except Exception as e:
            return {"status": "error", "message": f"Erreur lors de la lecture du son : {e}"}

    def activate_lost_mode(self):
        if not self.client:
            return {"status": "error", "message": self.error_message}
        try:
            phone_number = '+33 7 62 73 98 94'
            message = 'Merci de me rendre mon téléphone.'
            self.client.iphone.lost_device(phone_number, message)
            return {"status": "success", "message": "Le mode perdu a été activé sur l'iPhone."}
        except Exception as e:
            return {"status": "error", "message": f"Erreur lors de l'activation du mode perdu : {e}"}


if __name__ == "__main__":
    apple_assistant = AppleAssistant()

    # Exemple d'utilisation des fonctions
    battery_info = apple_assistant.get_iphone_battery()
    print(battery_info)

    location_info = apple_assistant.get_location()
    print(location_info)

    weather_info = apple_assistant.get_weather()
    print(weather_info)

    contacts_info = apple_assistant.get_contacts("Edvin")
    print(contacts_info)
