import os
import json
import base64
from html import unescape
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import openai
from openai import OpenAI
import re
from dotenv import load_dotenv

from mistralai import Mistral

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

mistral_api_key = os.getenv("MISTRAL_API_KEY")
mistral_client = Mistral(api_key=mistral_api_key) if mistral_api_key else None


# Chemin vers les fichiers credentials et token
CREDENTIALS_FILE = "google_secret.json"
TOKEN_FILE = "token_google.json"

class GoogleAssistant:
    def __init__(self):
        self.creds = self.get_google_token()
        self.gmail_service = self.get_service('gmail', 'v1')
        self.calendar_service = self.get_service('calendar', 'v3')
        self.tasks_service = self.get_service('tasks', 'v1')

    def load_token(self):
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as token_file:
                token_data = json.load(token_file)
                return self.from_token_info(token_data)
        return None

    def from_token_info(self, token_info):
        """Créer des credentials à partir des informations du token JSON."""
        expiry = datetime.strptime(token_info['expiry'], "%Y-%m-%dT%H:%M:%S.%fZ") if token_info.get('expiry') else None
        creds = Credentials(
            token=token_info.get('token'),
            refresh_token=token_info.get('refresh_token'),
            token_uri=token_info.get('token_uri'),
            client_id=token_info.get('client_id'),
            client_secret=token_info.get('client_secret'),
            expiry=expiry
        )
        return creds

    def save_token(self, credentials):
        with open(TOKEN_FILE, 'w') as token_file:
            token_json = credentials.to_json()
            token_file.write(token_json)

    def get_google_token(self):
        """Obtenir un token Google valide."""
        creds = self.load_token()

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self.save_token(creds)
            except Exception as error:
                print(f"Erreur lors du rafraîchissement du token: {error}")
                creds = None

        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE,
                scopes=[
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/gmail.send",
                    "https://www.googleapis.com/auth/gmail.modify",
                    "https://www.googleapis.com/auth/calendar",
                    "https://www.googleapis.com/auth/tasks",
                ]
            )
            creds = flow.run_local_server(port=5000)
            self.save_token(creds)

        return creds

    def get_service(self, api_name, api_version):
        try:
            if not self.creds or not self.creds.valid:
                return None
            service = build(api_name, api_version, credentials=self.creds)
            return service
        except HttpError as error:
            return [f"Une erreur s'est produite lors de la création du service {api_name} : {error}"]

    def decode_message_body(self, encoded_body, mime_type):
        """Décode le corps du message en fonction du type MIME."""
        decoded_bytes = base64.urlsafe_b64decode(encoded_body)
        if mime_type == "text/plain":
            return decoded_bytes.decode('utf-8')
        else:
            return None  # Ignore le HTML et les autres types MIME

    def clean_up_text(self, text):
        """Nettoie les sauts de ligne excessifs dans le texte."""
        return re.sub(r'\n{3,}', '\n\n', text.strip())

    def collect_emails(self, filter_type=None, specific_recipient=None, specific_word=None, start_date=None, end_date=None, query_extra=''):
        """Collecte des emails avec des filtres avancés, incluant une plage de dates."""
        result = []
        query = query_extra

        # Filtrer par type (existant)
        if filter_type == 'unread':
            query += ' is:unread'
        elif filter_type == 'inbox':
            query += ' in:inbox'
        elif filter_type == 'today':
            today = datetime.now().strftime('%Y/%m/%d')
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y/%m/%d')
            query += f' after:{today} before:{tomorrow}'
        elif filter_type == 'week':
            week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime('%Y/%m/%d')
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y/%m/%d')
            query += f' after:{week_start} before:{tomorrow}'
        elif filter_type == 'month':
            month_start = datetime.now().replace(day=1).strftime('%Y/%m/%d')
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y/%m/%d')
            query += f' after:{month_start} before:{tomorrow}'
        elif filter_type == 'year':
            year_start = datetime.now().replace(month=1, day=1).strftime('%Y/%m/%d')
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y/%m/%d')
            query += f' after:{year_start} before:{tomorrow}'

        # Ajouter la plage de dates si spécifiée
        if start_date and end_date:
            query += f' after:{start_date} before:{end_date}'

        # Filtrer par destinataire spécifique
        if specific_recipient:
            query += f' to:{specific_recipient}'

        # Filtrer par mot spécifique dans le sujet
        if specific_word:
            query += f' subject:{specific_word}'

        summary_data = {}

        try:
            response = self.gmail_service.users().messages().list(
                userId='me',
                q=query,
                maxResults=500
            ).execute()

            messages = response.get('messages', [])
            if not messages:
                return summary_data

            for message in messages:
                email = self.read_message(message['id'], display=False)  # Récupérer l'email sans l'afficher
                if email:
                    summary_data[message['id']] = email

        except HttpError as error:
            result.append(f'Une erreur s\'est produite : {error}')

        return summary_data

    def mark_as_read(self, message_id, user_id='me'):
        """Marquer un message comme lu."""
        result = []
        try:
            self.gmail_service.users().messages().modify(userId=user_id, id=message_id, body={'removeLabelIds': ['UNREAD']}).execute()
            result.append(f"Message ID {message_id} marqué comme lu.")
        except HttpError as error:
            result.append(f"Une erreur s'est produite lors du marquage du message comme lu : {error}")
        return result

    def trash_message(self, message_id, user_id='me'):
        """Mettre un message à la corbeille."""
        result = []
        try:
            self.gmail_service.users().messages().modify(userId=user_id, id=message_id, body={'addLabelIds': ['TRASH']}).execute()
            result.append(f"Message ID {message_id} mis à la corbeille.")
        except HttpError as error:
            result.append(f"Une erreur s'est produite lors de la mise à la corbeille du message : {error}")
        return result

    def archive_message(self, message_id, user_id='me'):
        """Archiver un message."""
        result = []
        try:
            self.gmail_service.users().messages().modify(userId=user_id, id=message_id, body={'removeLabelIds': ['INBOX']}).execute()
            result.append(f"Message ID {message_id} archivé.")
        except HttpError as error:
            result.append(f"Une erreur s'est produite lors de l'archivage du message : {error}")
        return result

    def reply_to_message(self, message_id, user_id='me'):
        """Répondre à un message."""
        result = []
        try:
            # Lire le message original
            message = self.gmail_service.users().messages().get(userId=user_id, id=message_id, format='metadata').execute()
            headers = {header['name']: header['value'] for header in message['payload']['headers']}
            reply_to = headers.get('From')
            subject = headers.get('Subject', '')
            if not subject.lower().startswith("re:"):
                subject = "Re: " + subject

            reply_body = input("Entrez votre réponse : ")
            message = MIMEText(reply_body)
            message['to'] = reply_to
            message['from'] = user_id
            message['subject'] = subject

            raw_message = {'raw': base64.urlsafe_b64encode(message.as_string().encode()).decode()}
            self.gmail_service.users().messages().send(userId=user_id, body=raw_message).execute()
            result.append(f"Message envoyé à {reply_to}.")
        except HttpError as error:
            result.append(f"Une erreur s'est produite lors de l'envoi de la réponse : {error}")
        return result

    def forward_message(self, message_id, user_id='me'):
        """Transférer un message."""
        result = []
        try:
            # Lire le message original
            message = self.gmail_service.users().messages().get(userId=user_id, id=message_id, format='full').execute()
            headers = {header['name']: header['value'] for header in message['payload']['headers']}
            subject = headers.get('Subject', '')
            if not subject.lower().startswith("fwd:"):
                subject = "Fwd: " + subject

            forward_to = input("Entrez l'adresse email de transfert : ")
            forward_body = input("Entrez votre message d'introduction : ")

            # Extraire le contenu original
            original_body = ""
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    mime_type = part['mimeType']
                    if mime_type == "text/plain":  # Ne traiter que les parties texte
                        original_body += self.decode_message_body(part['body']['data'], mime_type)

            combined_body = f"{forward_body}\n\n--- Message transféré ---\n{original_body}"
            message = MIMEText(combined_body)
            message['to'] = forward_to
            message['from'] = user_id
            message['subject'] = subject

            raw_message = {'raw': base64.urlsafe_b64encode(message.as_string().encode()).decode()}
            self.gmail_service.users().messages().send(userId=user_id, body=raw_message).execute()
            result.append(f"Message transféré à {forward_to}.")
        except HttpError as error:
            result.append(f"Une erreur s'est produite lors du transfert du message : {error}")
        return result

    def read_message(self, message_id, user_id='me', preview_length=500, display=True):
        """Lire un message Gmail avec un aperçu limité et nettoyer les sauts de ligne."""
        result = []
        try:
            message = self.gmail_service.users().messages().get(userId=user_id, id=message_id, format='full').execute()

            # Extraire les en-têtes du message
            headers = {header['name']: header['value'] for header in message['payload']['headers']}
            sender = headers.get('From')
            recipient = headers.get('To')
            subject = headers.get('Subject', '(Aucun sujet)')
            date = headers.get('Date')

            result.append(f"De : {sender}")
            result.append(f"À : {recipient}")
            result.append(f"Sujet : {subject}")
            result.append(f"Date : {date}")
            result.append(f"ID : {message_id}\n")

            # Extraire le contenu du message
            body = ""
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    mime_type = part['mimeType']
                    if mime_type == "text/plain":
                        body += self.decode_message_body(part['body']['data'], mime_type)
            else:
                body = self.decode_message_body(message['payload']['body']['data'], message['payload']['mimeType'])

            if body:
                body = self.clean_up_text(body)
            else:
                body = ""

            if display:
                if len(body) > preview_length:
                    result.append(f"Message (Aperçu - {preview_length} premiers caractères) :\n{body[:preview_length]}...\n")
                else:
                    result.append(f"Message :\n{body}\n")

                action = input("Voulez-vous (m)arquer comme lu, (s)mettre à la corbeille, (a)rchiver, (r)épondre, (t)ransférer, (p)asser, ou (q)uitter ? ")

                if action == 'm':
                    self.mark_as_read(message_id, user_id)
                elif action == 's':
                    self.trash_message(message_id, user_id)
                elif action == 'a':
                    self.archive_message(message_id, user_id)
                elif action == 'r':
                    self.reply_to_message(message_id, user_id)
                elif action == 't':
                    self.forward_message(message_id, user_id)
                elif action == 'q':
                    result.append("Sortie en cours...")
                    return result
                else:
                    result.append("Passage au message suivant.")

            return {"body": body, "subject": subject}

        except HttpError as error:
            result.append(f"Une erreur s'est produite lors de la lecture du message : {error}")
            return result

    def summarize_emails(self, filter_type=None, specific_recipient=None, specific_word=None):
        """Fournir des résumés des emails."""
        result = []
        summary_data = self.collect_emails(filter_type=filter_type, specific_recipient=specific_recipient, specific_word=specific_word)

        for email_id, email in summary_data.items():
            response = client.chat.completions.create(
                model="ft:gpt-4o-mini-2024-07-18:personal:t-o-m:9w6Mhcn0",
                messages=[
                    {"role": "system", "content": "Tu es TOM, un assistant polyvalent qui aide les utilisateurs à gérer leurs mails et bien d'autres choses."},
                    {"role": "user", "content": f"Résumé cet email : {email['body']}"}
                ],
                max_tokens=150
            )
            summary = response.choices[0].message.content.strip()
            result.append(f"Résumé pour l'email {email_id} : {summary}\n")
        return result

    def list_and_interact_with_messages(self, filter_type=None, specific_recipient=None, specific_word=None, max_results=10):
        """Lister et interagir avec les messages Gmail, avec des filtres."""
        result = []
        summary_data = self.collect_emails(filter_type=filter_type, specific_recipient=specific_recipient, specific_word=specific_word, query_extra='')

        result.append(f'{len(summary_data)} messages trouvés :')
        for email_id, email in summary_data.items():
            result.append("-"*100)
            print("-"*100)
            print(f"- ID : {email_id} | Sujet : {email['subject']}")
            result.append(f"- ID : {email_id} | Sujet : {email['subject']}")
            message_result = self.read_message(email_id, preview_length=500)
            result.extend(message_result)
            if message_result == 'quitter':
                break  # Sortir de la boucle si l'utilisateur choisit de quitter
        return result

    def analyze_email(self, email):
        """Analyse un email pour le catégoriser, attribuer un score de priorité, et extraire les tâches."""
        prompt = (
            "Tu es un assistant IA nommé TOM qui aide les utilisateurs à gérer leurs emails. "
            "Analyse l'email suivant et retourne un objet JSON avec les clés suivantes : "
            "1. 'category' : La catégorie de l'email (e.g., Travail, Personnel, Finance, Promotions, Spam, Phishing), "
            "2. 'priority_score' : Un score de priorité entre 1 et 10 basé sur l'importance de l'email, "
            "3. 'tasks' : Une liste des tâches à effectuer basées sur le contenu de l'email en français, "
            "4. 'sender' : L'adresse email de l'expéditeur, "
            "5. 'recipient' : L'adresse email du destinataire, "
            "6. 'subject' : L'objet de l'email, "
            "7. 'date' : La date à laquelle l'email a été envoyé. "
            "Voici l'email :\n"
            f"Expéditeur : {email.get('sender', 'Inconnu')}\n"
            f"Destinataire : {email.get('recipient', 'Inconnu')}\n"
            f"Objet : {email.get('subject', 'Pas d\'objet')}\n"
            f"Date : {email.get('date', 'Inconnue')}\n\n"
            f"Corps : {email['body']}\n"
        )

        response = client.chat.completions.create(
            model="ft:gpt-4o-mini-2024-07-18:personal:t-o-m:9w6Mhcn0",
            messages=[
                {"role": "system", "content": "Tu es TOM, un assistant polyvalent qui aide les utilisateurs à gérer leurs mails et bien d'autres choses."},
                {"role": "user", "content": f"{prompt}"}
            ],
        )
        analysis_json = response.choices[0].message.content.strip()

        try:
            analysis = json.loads(analysis_json)
        except json.JSONDecodeError:
            analysis = {
                "category": "Inconnu",
                "priority_score": 0,
                "tasks": [],
                "sender": email.get('sender', 'Inconnu'),
                "recipient": email.get('recipient', 'Inconnu'),
                "subject": email.get('subject', 'Pas d\'objet'),
                "date": email.get('date', 'Inconnue')
            }

        return analysis

    def list_existing_labels(self):
        """Lister tous les labels existants dans Gmail."""
        service = self.gmail_service
        result = []
        try:
            labels = service.users().labels().list(userId='me').execute().get('labels', [])
            return labels
        except HttpError as error:
            result.append(f"Une erreur s'est produite lors de la récupération des labels : {error}")
            return result

    def create_labels_if_not_exist(self, labels):
        """Créer les labels dans Gmail s'ils n'existent pas."""
        result = []
        service = self.gmail_service

        try:
            existing_labels = service.users().labels().list(userId='me').execute().get('labels', [])
            existing_label_names = {label['name'] for label in existing_labels}

            for label in labels:
                if label not in existing_label_names:
                    label_body = {
                        "labelListVisibility": "labelShow",
                        "messageListVisibility": "show",
                        "name": label
                    }
                    service.users().labels().create(userId='me', body=label_body).execute()
                    result.append(f"Label '{label}' créé.")

        except HttpError as error:
            result.append(f"Une erreur s'est produite lors de la création des labels : {error}")
        return result

    def move_email_to_label(self, email_id, category):
        """Déplace un email vers le label approprié selon la catégorie."""
        result = []
        try:
            label_mapping = {
                'travail': 'Travail',
                'personnel': 'Personnel',
                'finance': 'Finance',
                'promotions': 'Promotions',
                'spam': 'Spam',
                'phishing': 'Spam',
            }

            existing_labels = self.list_existing_labels()
            label_id_map = {label['name'].lower(): label['id'] for label in existing_labels}

            label_name = label_mapping.get(category.lower())

            if label_name:
                label_id = label_id_map.get(label_name.lower())

                if label_id:
                    self.gmail_service.users().messages().modify(
                        userId='me',
                        id=email_id,
                        body={'addLabelIds': [label_id]}
                    ).execute()

                    result.append(f"Email ID {email_id} déplacé vers le label '{label_name}' avec ID '{label_id}'.")
                else:
                    result.append(f"Aucun label trouvé pour la catégorie '{category}'. Vérifiez si le label est bien créé et mappé correctement.")
            else:
                result.append(f"Catégorie '{category}' non reconnue.")

        except HttpError as error:
            result.append(f"Une erreur s'est produite lors du déplacement de l'email ID {email_id} : {error}")
        return result

    def list_and_analyze_emails(self, filter_type=None, specific_recipient=None, specific_word=None):
        """Lister et analyser les emails, puis les déplacer dans les labels appropriés."""
        result = []

        necessary_labels = ['Travail', 'Personnel', 'Finance', 'Promotions', 'Phishing']
        label_result = self.create_labels_if_not_exist(necessary_labels)
        result.extend(label_result)

        emails = self.collect_emails(filter_type=filter_type, specific_recipient=specific_recipient, specific_word=specific_word)

        if not emails:
            result.append('Aucun message trouvé.')
            return result

        result.append(f'{len(emails)} messages trouvés :')

        tasks_summary = []

        for email_id, email in emails.items():
            analysis = self.analyze_email(email)

            subject = email.get('subject', 'Aucun sujet')
            sender = analysis.get('sender', 'Inconnu')
            date = analysis.get('date', 'Inconnue')
            category = analysis.get('category', 'Inconnu')
            priority_score = analysis.get('priority_score', 0)
            tasks = analysis.get('tasks', [])

            result.append(f"- ID : {email_id} | Sujet : {subject} | De : {sender} | Date : {date}")
            result.append(f"  Catégorie : {category.capitalize()} | Priorité : {priority_score}")

            if tasks:
                result.append("  Tâches à effectuer :")
                for task in tasks:
                    result.append(f"    - {task}")
                    tasks_summary.append((priority_score, task, subject, sender, date))
            else:
                result.append("  Aucune tâche détectée.")

            result.append("\n" + "-"*80 + "\n")

        tasks_summary.sort(reverse=True, key=lambda x: x[0])

        result.append("Résumé des tâches à effectuer, ordonnées par priorité :\n")
        for priority_score, task, subject, sender, date in tasks_summary:
            result.append(f"Tâche : {task}")
            result.append(f"  Priorité : {priority_score} | Sujet : {subject} | De : {sender} | Date : {date}\n")

        return result

    def create_email(self, to, subject, additional_info=None, user_id='me'):
        """Créer un brouillon d'email en utilisant GPT pour générer le corps de l'email."""
        result = []
        try:
            # Créer le prompt pour GPT
            prompt = (
                f"Vous devez rédiger un email professionnel avec les informations suivantes : \n\n"
                f"Destinataire : {to}\n"
                f"Sujet : {subject}\n\n"
            )
            if additional_info:
                prompt += f"Informations supplémentaires pour l'email : {additional_info}\n\n"

            prompt += "Contenu de l'email :"

            # Utiliser GPT pour générer le corps de l'email
            response = client.chat.completions.create(
                model="ft:gpt-4o-mini-2024-07-18:personal:t-o-m:9w6Mhcn0",
                messages=[
                    {"role": "system", "content": "Tu es un assistant IA qui aide à rédiger des emails professionnels."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150
            )

            # Récupérer la réponse générée par GPT et la nettoyer
            email_body = response.choices[0].message.content.strip()
            email_body = email_body.replace("**", "")  # Enlever les ** du texte

            # Créer le message MIME avec les en-têtes appropriés
            message = MIMEText(email_body)
            message['To'] = to
            message['From'] = user_id  # Ce champ doit contenir l'adresse email de l'utilisateur authentifié
            message['Subject'] = subject

            # Encoder le message en base64
            raw_message = base64.urlsafe_b64encode(message.as_string().encode()).decode()

            # Créer le brouillon
            draft = {
                'message': {
                    'raw': raw_message
                }
            }

            # Envoyer la requête pour créer le brouillon
            created_draft = self.gmail_service.users().drafts().create(userId=user_id, body=draft).execute()
            result.append(f"Brouillon d'email créé avec succès. ID du brouillon : {created_draft['id']}")
            result.append(f"Contenu : {email_body}")
            result.append(created_draft)
            return result

        except HttpError as error:
            result.append(f"Une erreur s'est produite lors de la création du brouillon : {error}")
            return result

    def display_draft(self, draft_id, user_id='me'):
        """Afficher le contenu d'un brouillon basé sur son ID."""
        result = []

        try:
            # Récupérer le brouillon existant
            draft = self.gmail_service.users().drafts().get(userId=user_id, id=draft_id).execute()
            message = draft['message']
            headers = {header['name']: header['value'] for header in message['payload']['headers']}
            to = headers.get('To', '(Inconnu)')
            subject = headers.get('Subject', '(Aucun sujet)')
            from_ = headers.get('From', '(Inconnu)')

            # Extraire le contenu du brouillon
            body = ""
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    mime_type = part['mimeType']
                    if mime_type == "text/plain":  # Ne traiter que les parties texte
                        body += self.decode_message_body(part['body']['data'], mime_type)
            else:
                body = self.decode_message_body(message['payload']['body']['data'], message['payload']['mimeType'])

            # Nettoyer le texte du brouillon
            body = self.clean_up_text(body)

            # Afficher les détails du brouillon
            result.append(f"Expéditeur : {from_}")
            result.append(f"Destinataire : {to}")
            result.append(f"Sujet : {subject}")
            result.append(f"Contenu du brouillon :\n\n{body}\n")

            return result

        except HttpError as error:
            if error.resp.status == 404:
                result.append(f"Une erreur s'est produite lors de l'affichage du brouillon : {error}")
            else:
                result.append(f"Une erreur inattendue s'est produite lors de l'affichage du brouillon : {error}")
            return result

    def create_draft_reply(self, message_id, user_id='me', additional_info=None):
        """Créer un brouillon de réponse à un message donné en utilisant GPT pour générer le corps de la réponse."""
        result = []
        try:
            # Lire le message original
            message = self.gmail_service.users().messages().get(userId=user_id, id=message_id, format='full').execute()
            headers = {header['name']: header['value'] for header in message['payload']['headers']}
            reply_to = headers.get('From')
            recipient = headers.get('To')
            subject = headers.get('Subject', '')
            date = headers.get('Date')

            if not subject.lower().startswith("re:"):
                subject = "Re: " + subject

            # Extraire le contenu du message original
            body = ""
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    mime_type = part['mimeType']
                    if mime_type == "text/plain":  # Ne traiter que les parties texte
                        body += self.decode_message_body(part['body']['data'], mime_type)
            else:
                body = self.decode_message_body(message['payload']['body']['data'], message['payload']['mimeType'])

            # Nettoyer le texte du message original
            body = self.clean_up_text(body)

            # Créer le prompt pour GPT en incluant les informations supplémentaires
            prompt = (
                f"Vous devez rédiger une réponse polie et professionnelle à cet email : \n\n"
                f"Expéditeur : {reply_to}\n"
                f"Destinataire : {recipient}\n"
                f"Sujet : {subject}\n"
                f"Date d'envoi : {date}\n\n"
                f"Contenu de l'email original : \n{body}\n\n"
            )
            if additional_info:
                prompt += f"Informations supplémentaires pour la réponse : {additional_info}\n\n"

            prompt += "Réponse :"

            # Utiliser GPT pour générer le corps de la réponse
            response = client.chat.completions.create(
                model="ft:gpt-4o-mini-2024-07-18:personal:t-o-m:9w6Mhcn0",
                messages=[
                    {"role": "system", "content": "Tu es un assistant IA qui aide à rédiger des emails professionnels."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150
            )

            # Récupérer la réponse générée par GPT et la nettoyer
            reply_body = response.choices[0].message.content.strip()
            reply_body = reply_body.replace("**", "")  # Enlever les ** du texte

            # Créer le message MIME
            message = MIMEText(reply_body)
            message['to'] = reply_to
            message['from'] = user_id
            message['subject'] = subject

            # Encoder le message en base64
            raw_message = base64.urlsafe_b64encode(message.as_string().encode()).decode()

            # Créer le brouillon
            draft = {
                'message': {
                    'raw': raw_message
                }
            }

            # Envoyer la requête pour créer le brouillon
            created_draft = self.gmail_service.users().drafts().create(userId=user_id, body=draft).execute()
            result.append(f"Brouillon de réponse créé avec succès. ID du brouillon : {created_draft['id']}")
            result.append(f"Contenu : {reply_body}")
            result.append(created_draft)
            return result

        except HttpError as error:
            result.append(f"Une erreur s'est produite lors de la création du brouillon : {error}")
            return result

    def send_draft(self, draft_id, content=None, user_id='me'):
        """Modifier le contenu d'un brouillon et l'envoyer."""
        result = []
        try:
            # Récupérer le brouillon existant
            draft = self.gmail_service.users().drafts().get(userId=user_id, id=draft_id).execute()
            message = draft['message']
            headers = {header['name']: header['value'] for header in message['payload']['headers']}
            to = headers.get('To')
            subject = headers.get('Subject')

            # Vérifier que l'adresse du destinataire est présente
            if not to:
                result.append("Erreur : L'adresse du destinataire est requise pour envoyer l'email.")
                return result

            # Si un nouveau contenu est fourni, il remplace le contenu actuel du brouillon
            if content:
                message = MIMEText(content)
                message['to'] = to
                message['from'] = user_id
                message['subject'] = subject

                # Encoder le message en base64
                raw_message = base64.urlsafe_b64encode(message.as_string().encode()).decode()

                # Mettre à jour le brouillon avec le nouveau contenu
                draft_update = {
                    'message': {
                        'raw': raw_message
                    }
                }
                updated_draft = self.gmail_service.users().drafts().update(userId=user_id, id=draft_id, body=draft_update).execute()
                result.append(f"Brouillon mis à jour avec succès. ID du brouillon : {updated_draft['id']}")

            # Envoyer le brouillon (mis à jour ou original)
            sent_message = self.gmail_service.users().drafts().send(userId=user_id, body={'id': draft_id}).execute()
            result.append(f"Brouillon envoyé avec succès. ID du message envoyé : {sent_message['id']}")
            result.append(sent_message)

            return result

        except HttpError as error:
            result.append(f"Une erreur s'est produite lors de la modification ou de l'envoi du brouillon : {error}")
            return result


if __name__ == '__main__':
    google_assistant = GoogleAssistant()

    # Récupérer les emails du jour
    google_assistant.list_and_interact_with_messages(filter_type='today')
