import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('API_KEY_MOVIE')

base_url = 'https://api.themoviedb.org/3'

def make_request(endpoint, params):
    params['api_key'] = api_key
    params['language'] = 'fr-FR'
    response = requests.get(f"{base_url}/{endpoint}", params=params)
    return response.json() if response.status_code == 200 else {}

def get_genre_list(media_type='movie'):
    data = make_request(f'genre/{media_type}/list', {})
    return {genre['name'].lower(): genre['id'] for genre in data.get('genres', [])}

def search_media(query=None, genre_name=None, media_type='movie'):
    endpoint = 'discover' if genre_name else 'search'
    params = {'query': query} if query else {}

    if genre_name:
        genre_id = get_genre_list(media_type).get(genre_name.lower())
        if not genre_id:
            print(f"Le genre '{genre_name}' n'a pas été trouvé.")
            return []
        params['with_genres'] = genre_id

    data = make_request(f"{endpoint}/{media_type}", params)
    return data.get('results', [])


def recommend_media(title=None, genre=None, media_type='movie'):
    results = search_media(query=title, genre_name=genre, media_type=media_type)
    if not results:
        print(f"Aucun {media_type} trouvé.")
        return

    return str(results)


def propose_recommendations(media_type='movie'):
    genres = get_genre_list(media_type)
    if genres:
        print("\n=== Genres Disponibles ===")
        for genre_name in genres.keys():
            print(f"- {genre_name.capitalize()}")

    user_choice = input("\nVoulez-vous rechercher par titre ou par genre? (titre/genre) : ").strip().lower()
    if user_choice == 'titre':
        title = input("Entrez le titre : ").strip()
        recommend_media(title=title, media_type=media_type)
    elif user_choice == 'genre':
        genre = input("Entrez le genre : ").strip()
        recommend_media(genre=genre, media_type=media_type)
    else:
        print("Choix non valide. Veuillez réessayer.")


if __name__ == "__main__":
    print("Recommandations de Films :")
    propose_recommendations(media_type='movie')

    print("\nRecommandations de Séries TV :")
    propose_recommendations(media_type='tv')
