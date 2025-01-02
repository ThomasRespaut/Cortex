from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection
from huawei_lte_api.enums.sms import BoxTypeEnum, SortTypeEnum
import time
from huawei_lte_api.enums.client import ResponseEnum
from start import TinyCortex

class Dongle:
    def __init__(self, username='admin', password='admin', dongle_url='192.168.8.1'):
        self.connection_url = f'http://{username}:{password}@{dongle_url}/'
        self.connection = None
        self.client = None
        self.processed_messages = {}

    def connect(self):
        try:
            self.connection = Connection(self.connection_url)
            self.client = Client(self.connection)
            print("Connexion réussie au dongle.")
            print(self.client.device.information())
        except Exception as e:
            print(f"Erreur lors de la connexion au dongle : {str(e)}")
            raise

    def close_connection(self):
        if self.connection:
            self.connection.close()
            print("Connexion fermée.")

    def reboot_modem(self):
        try:
            print("Fermeture de la connexion avant le reboot.")
            self.close_connection()  # Fermer la connexion pour éviter les problèmes de session
            self.connect()  # Ré-établir une connexion propre
            if self.client.device.reboot() == ResponseEnum.OK.value:
                print("Reboot demandé avec succès.")
                time.sleep(30)  # Attente pour que le modem redémarre
            else:
                print("Erreur lors du reboot du modem.")
        except Exception as e:
            print(f"Erreur lors du reboot du modem : {str(e)}")

    def get_received_sms(self):
        try:
            sms_list = self.client.sms.get_sms_list(
                page=1,
                box_type=BoxTypeEnum.LOCAL_INBOX,  # Boîte de réception
                read_count=20,
                sort_type=SortTypeEnum.DATE,
                ascending=False,
                unread_preferred=False
            )

            messages = sms_list.get('Messages', {}).get('Message', [])
            if not messages:
                print("Aucun SMS trouvé dans la boîte de réception.")
                return []

            for message in messages:
                if all(key in message for key in ['Phone', 'Content', 'Date', 'Index']):
                    print(f"De: {message['Phone']}\nMessage: {message['Content']}\nDate: {message['Date']}\n{'-'*40}")
                else:
                    print(f"Message avec clés manquantes : {message}")

            return messages

        except Exception as e:
            if "125003" in str(e):
                print("Erreur 125003 détectée. Tentative de reboot du modem.")
                self.reboot_modem()
            else:
                print(f"Erreur lors de la récupération des SMS : {str(e)}")
            return []

    def send_sms(self, phone_number, content):
        try:
            self.client.sms.send_sms(phone_number, content)
            print(f"SMS envoyé à {phone_number}: {content}")
        except Exception as e:
            if "125003" in str(e):
                print("Erreur 125003 détectée. Tentative de reboot du modem.")
                self.reboot_modem()
            else:
                print(f"Erreur lors de l'envoi du SMS : {str(e)}")

    def delete_sms(self, message_id):
        try:
            self.client.sms.delete_sms(message_id)
            print(f"Message Index {message_id} supprimé.")
        except Exception as e:
            print(f"Erreur lors de la suppression du message : {str(e)}")

    def auto_respond_to_new_sms(self,cortex):
        while True:
            try:
                messages = self.get_received_sms()
                for message in messages:
                    if 'Index' in message and 'Phone' in message and 'Content' in message:
                        message_id = message['Index']
                        message_signature = (message_id, message['Phone'], message['Content'])

                        if message_signature not in self.processed_messages:
                            phone_number = message['Phone']
                            sms = f"Question : {message['Content']} \n Réponse : "
                            #Utiliser le modèle pour répondre :
                            reply_content = cortex.generate_response(sms)
                            self.send_sms(phone_number, reply_content)
                            self.delete_sms(message_id)
                            self.processed_messages[message_signature] = True
                    else:
                        print(f"Message avec clés manquantes : {message}")

                time.sleep(5)

            except KeyboardInterrupt:
                print("Arrêt de la vérification automatique des SMS.")
                break
            except Exception as e:
                print(f"Erreur lors de l'auto-réponse : {str(e)}. Messages en cours : {messages}")

class DongleManager:
    def __init__(self, dongle_urls, username='admin', password='admin'):
        self.dongle_urls = dongle_urls
        self.current_index = 0
        self.username = username
        self.password = password
        self.current_dongle = self._initialize_dongle()

    def _initialize_dongle(self):
        return Dongle(username=self.username, password=self.password, dongle_url=self.dongle_urls[self.current_index])

    def switch_dongle(self):
        print(f"Changement de dongle. Ancien dongle : {self.dongle_urls[self.current_index]}")
        self.current_index = (self.current_index + 1) % len(self.dongle_urls)
        self.current_dongle = self._initialize_dongle()
        print(f"Nouvel dongle : {self.dongle_urls[self.current_index]}")

    def handle_error_and_switch(self, error):
        print(f"Erreur critique détectée : {error}")
        self.switch_dongle()

# Exemple d'utilisation de DongleManager
if __name__ == "__main__":
    dongle_urls = ["192.168.8.1", "192.168.8.2"]  # Liste des dongles disponibles
    manager = DongleManager(dongle_urls)
    cortex = TinyCortex()
    try:
        manager.current_dongle.connect()
        manager.current_dongle.auto_respond_to_new_sms(cortex)
    except Exception as e:
        manager.handle_error_and_switch(e)
    finally:
        manager.current_dongle.close_connection()

