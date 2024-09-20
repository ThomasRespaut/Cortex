import os

import requests

from pyicloud import PyiCloudService
from pyicloud.exceptions import PyiCloudFailedLoginException, PyiCloudAPIResponseException

from dotenv import load_dotenv
load_dotenv()

class Apple_Assistant():
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
                    print("Impossible de vérifier le code de sécurité.")


        except PyiCloudFailedLoginException as e:
            print(f"Impossible de se connecter à Icloud : {e}")
            self.client = None

        except PyiCloudAPIResponseException as e:
            print(f"Erreur dans l'API : {e}")
            self.client = None

        except Exception as e:
            print(f"Erreur : {e}")
            self.client = None

    def get_iphone_battery(self):
        try:
            iphone_info = self.client.iphone.status()
            battery_level = iphone_info.get("batteryLevel", None)

            self.battery_level = f"{battery_level * 100:.0f}%" if battery_level is not None else "N/A"

        except Exception as e:
            print(f"Erreur lors de la récupération du niveau de batterie : {e}")
            self.battery_level = "N/A"
    def get_location(self):
        self.location = self.client.iphone.location()
        self.latitude = self.location.get("latitude","0")
        self.longitude = self.location.get("longitude","0")

        try:
            url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={self.latitude},{self.longitude}&key={self.maps_api_key}"
            response = requests.get(url)
            address = response.json()
            if address["status"] == "OK":
                self.adress = address["results"][0]["formatted_address"]
            else:
                self.adress = "Adresse inconnue"

        except Exception as e:
            print(f"Erreur dans la récupération de l'adresse : {e}")
            self.adress = "Adresse inconnue"

    def get_weather(self):
        try:
            self.get_location()
            url = f"http://api.openweathermap.org/data/2.5/weather?lat={self.latitude}&lon={self.longitude}&appid={self.openweathermap_api_key}&units=metric"
            response = requests.get(url)
            weather = response.json()
            if weather['cod'] == 200:
                weather_main = weather['weather'][0]['main']
                weather_description = weather['weather'][0]['description']
                weather_temp = weather['main']["temp"]
                self.weather = f"Conditions météo : {weather_main}, {weather_description}. Température : {weather_temp}°C."
            else:
                self.weather = "Informations météorologiques non disponibles."

        except Exception as e:
            print(f"Erreur lors de la récupération de la météo: {e}")
            self.weather = "Informations météorologiques non disponibles."

    def get_contacts(self, name=None):
        # Récupère tous les contacts
        self.contacts = self.client.contacts.all()

        if name:
            self.contacts = [contact for contact in self.contacts if
                             contact.get('firstName', '').lower().startswith(name.lower())]

        if not self.contacts:
            print(f"Aucun contact trouvé dont le prénom commence par '{name}'.")
        else:
            print(f"{len(self.contacts)} contact(s) trouvé(s) dont le prénom commence par '{name}':")
            for contact in self.contacts:
                first_name = contact.get('firstName', 'Prénom indisponible')
                last_name = contact.get('lastName', '')
                birthday = contact.get('birthday', '')
                phones = [phone.get('field', 'Numéro indisponible') for phone in contact.get('phones', [])]
                emails = [email.get('field', 'Email indisponible') for email in contact.get('emails', [])]
                addresses = [address.get('field', 'Adresse indisponible') for address in contact.get('addresses', [])]

                contact_info = f"Prénom: {first_name}"
                if last_name:
                    contact_info += f", Nom: {last_name}"
                if phones:
                    contact_info += f", Numéro(s): {', '.join(phones)}"
                if emails:
                    contact_info += f", Email(s): {', '.join(emails)}"
                if birthday:
                    contact_info += f", Anniversaire: {birthday}"
                if addresses:
                    contact_info += f", Adresse(s): {', '.join(addresses)}"

                print(contact_info)

    def play_sound(self):
        self.client.iphone.play_sound()

    def lost_mode(self):
        phone_number = '+33 7 62 73 98 94'
        message = 'Merci de me rendre mon téléphone.'
        self.client.iphone.lost_device(phone_number, message)


if __name__ == "__main__":
    apple = Apple_Assistant()

    apple.get_iphone_battery()
    print(apple.battery_level)

    apple.get_location()
    print(apple.location)
    print(apple.adress)

    apple.get_weather()
    print(apple.weather)

    print(apple.get_contacts("Edvin"))




