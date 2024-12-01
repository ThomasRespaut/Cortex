import json
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Configuration OAuth2
SPOTIPY_CLIENT_ID = "e63d4210d0154cceb13bc3c9552dbed7"
SPOTIPY_CLIENT_SECRET = "b127ca139a524d4fa1045ba4202c0f1e"
SPOTIPY_REDIRECT_URI = "http://localhost:8888/callback_spotify"
SPOTIPY_SCOPE = "user-read-playback-state user-modify-playback-state streaming"

TOKEN_FILE = "token_info.json"

class SpotifyAssistant:
    def __init__(self):
        self.sp_oauth = SpotifyOAuth(
            client_id=SPOTIPY_CLIENT_ID,
            client_secret=SPOTIPY_CLIENT_SECRET,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope=SPOTIPY_SCOPE
        )
        self.token_info = self.get_token()
        self.sp = spotipy.Spotify(auth=self.token_info['access_token']) if self.token_info else None

    def get_token(self):
        token_info = None
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                token_info = json.load(f)

        if not token_info or self.sp_oauth.is_token_expired(token_info):
            if token_info and 'refresh_token' in token_info:
                token_info = self.sp_oauth.refresh_access_token(token_info['refresh_token'])
            else:
                auth_url = self.sp_oauth.get_authorize_url()
                print(f"Veuillez autoriser l'application en visitant ce lien : {auth_url}")
                redirect_response = input("Collez l'URL de redirection après l'autorisation : ")
                code = self.sp_oauth.parse_response_code(redirect_response)
                token_info = self.sp_oauth.get_access_token(code)

            with open(TOKEN_FILE, "w") as f:
                json.dump(token_info, f)

        return token_info

    def get_spotify_instance(self):
        if not self.sp:
            self.token_info = self.get_token()
            self.sp = spotipy.Spotify(auth=self.token_info['access_token']) if self.token_info else None
        return self.sp

    def play_track(self, track_name):
        sp = self.get_spotify_instance()
        if not sp:
            return "Impossible de jouer le morceau."

        try:
            result = sp.search(q=track_name, type="track", limit=1)
            if result["tracks"]["items"]:
                track_uri = result["tracks"]["items"][0]['uri']
                sp.start_playback(uris=[track_uri])
                return f"Lecture du morceau : '{track_name}'."
            else:
                return f"Morceau '{track_name}' introuvable."
        except spotipy.exceptions.SpotifyException as e:
            return f"Erreur lors de la lecture du morceau : {e}"

    def pause_playback(self):
        sp = self.get_spotify_instance()
        if not sp:
            return "Impossible de mettre en pause."

        try:
            sp.pause_playback()
            return "Lecture mise en pause."
        except spotipy.exceptions.SpotifyException as e:
            return f"Erreur lors de la mise en pause : {e}"

    def resume_playback(self):
        sp = self.get_spotify_instance()
        if not sp:
            return "Impossible de reprendre la lecture."

        try:
            sp.start_playback()
            return "Lecture reprise."
        except spotipy.exceptions.SpotifyException as e:
            return f"Erreur lors de la reprise de la lecture : {e}"

    def next_track(self):
        sp = self.get_spotify_instance()
        if not sp:
            return "Impossible de passer au morceau suivant."

        try:
            sp.next_track()
            return "Passage au morceau suivant."
        except spotipy.exceptions.SpotifyException as e:
            return f"Erreur lors du passage au morceau suivant : {e}"

    def previous_track(self):
        sp = self.get_spotify_instance()
        if not sp:
            return "Impossible de revenir au morceau précédent."

        try:
            sp.previous_track()
            return "Retour au morceau précédent."
        except spotipy.exceptions.SpotifyException as e:
            return f"Erreur lors du retour au morceau précédent : {e}"

    def set_volume(self, volume_level):
        sp = self.get_spotify_instance()
        if not sp:
            return "Impossible de régler le volume."

        try:
            sp.volume(volume_level)
            return f"Volume réglé à {volume_level}%."
        except spotipy.exceptions.SpotifyException as e:
            return f"Erreur lors du réglage du volume : {e}"

    def get_current_playback(self):
        sp = self.get_spotify_instance()
        if not sp:
            return "Impossible de récupérer les informations de lecture."

        try:
            current_playback = sp.current_playback()
            if current_playback and current_playback['item']:
                track = current_playback['item']
                return f"En cours de lecture : '{track['name']}' par {track['artists'][0]['name']}."
            else:
                return "Aucune lecture en cours."
        except spotipy.exceptions.SpotifyException as e:
            return f"Erreur lors de la récupération des informations de lecture : {e}"

    def play_recommendations_track(self, track_name=None, artist_name=None, genre_name=None):
        sp = self.get_spotify_instance()
        if not sp:
            return "Impossible de se connecter à Spotify."

        seed_tracks = self.get_track_id(track_name) if track_name else None
        seed_artists = self.get_artist_seed(artist_name) if artist_name else None
        seed_genres = self.get_genre_seed(genre_name) if genre_name else None

        if not seed_tracks and not seed_artists and not seed_genres:
            return "Veuillez fournir au moins un titre, un artiste, ou un genre pour obtenir des recommandations."

        try:
            recommendations = sp.recommendations(
                seed_tracks=[seed_tracks] if seed_tracks else [],
                seed_artists=[seed_artists] if seed_artists else [],
                seed_genres=[seed_genres] if seed_genres else [],
                limit=5
            )['tracks']

            if not recommendations:
                return "Aucune recommandation disponible."

            sp.start_playback(uris=[recommendations[0]['uri']])
            recommendation_info = f"Lecture recommandée : '{recommendations[0]['name']}' par {recommendations[0]['artists'][0]['name']}.\n"

            for track in recommendations[1:]:
                try:
                    sp.add_to_queue(track['uri'])
                    recommendation_info += f"Morceau ajouté à la file d'attente : '{track['name']}' par {track['artists'][0]['name']}.\n"
                except spotipy.exceptions.SpotifyException as e:
                    recommendation_info += f"Erreur lors de l'ajout à la file d'attente : '{track['name']}' par {track['artists'][0]['name']} - {e}\n"

            return recommendation_info
        except spotipy.exceptions.SpotifyException as e:
            return f"Erreur lors de la lecture des recommandations : {e}"

    def get_artist_seed(self, artist_name):
        sp = self.get_spotify_instance()
        if not artist_name:
            return None
        try:
            results = sp.search(q=artist_name, type="artist", limit=1)
            if results['artists']['items']:
                return results['artists']['items'][0]['id']
            return None
        except spotipy.exceptions.SpotifyException:
            return None

    def get_genre_seed(self, genre_name):
        sp = self.get_spotify_instance()
        if not genre_name:
            return None
        try:
            available_genres = sp.recommendation_genre_seeds()['genres']
            if genre_name.lower() in available_genres:
                return genre_name.lower()
            return None
        except spotipy.exceptions.SpotifyException:
            return None

    def get_track_id(self, track_name):
        sp = self.get_spotify_instance()
        if not sp or not track_name:
            return None

        try:
            result = sp.search(q=track_name, type="track", limit=1)
            if result["tracks"]["items"]:
                return result["tracks"]["items"][0]['id']
            return None
        except spotipy.exceptions.SpotifyException:
            return None

if __name__ == "__main__":
    spotify_assistant = SpotifyAssistant()

    # Dictionnaire des fonctions à appeler
    names_to_functions = {
        'play_track': spotify_assistant.play_track,
        'pause_playback': spotify_assistant.pause_playback,
        'resume_playback': spotify_assistant.resume_playback,
        'next_track': spotify_assistant.next_track,
        'previous_track': spotify_assistant.previous_track,
        'set_volume': spotify_assistant.set_volume,
        'get_current_playback': spotify_assistant.get_current_playback,
        'play_recommendations_track': spotify_assistant.play_recommendations_track
    }

    # Menu interactif pour tester les différentes fonctions
    while True:
        print("\n=== Menu Spotify Assistant ===")
        print("1. Jouer un morceau")
        print("2. Mettre en pause")
        print("3. Reprendre la lecture")
        print("4. Passer au morceau suivant")
        print("5. Revenir au morceau précédent")
        print("6. Régler le volume")
        print("7. Obtenir les informations de lecture en cours")
        print("8. Jouer des recommandations")
        print("9. Quitter")

        choice = input("\nChoisissez une option (1-9) : ").strip()

        if choice == "1":
            track_name = input("Entrez le nom du morceau à jouer : ").strip()
            print(names_to_functions['play_track'](track_name))
        elif choice == "2":
            print(names_to_functions['pause_playback']())
        elif choice == "3":
            print(names_to_functions['resume_playback']())
        elif choice == "4":
            print(names_to_functions['next_track']())
        elif choice == "5":
            print(names_to_functions['previous_track']())
        elif choice == "6":
            volume_level = input("Entrez le niveau de volume (0-100) : ").strip()
            try:
                volume_level = int(volume_level)
                if 0 <= volume_level <= 100:
                    print(names_to_functions['set_volume'](volume_level))
                else:
                    print("Veuillez entrer une valeur entre 0 et 100.")
            except ValueError:
                print("Veuillez entrer un nombre valide.")
        elif choice == "7":
            print(names_to_functions['get_current_playback']())
        elif choice == "8":
            track_name = input("Entrez un titre de morceau ou laissez vide pour jouer des recommandations par défaut : ").strip()
            print(names_to_functions['play_recommendations_track'](track_name))
        elif choice == "9":
            print("Au revoir!")
            break
        else:
            print("Choix invalide. Veuillez réessayer.")
