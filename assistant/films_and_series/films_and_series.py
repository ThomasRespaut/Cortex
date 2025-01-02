import requests
import os
from dotenv import load_dotenv

import ast

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

def levenshtein_distance(s1, s2):
    """Calculer la distance de Levenshtein entre deux chaînes."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def recommend_media(title=None, genre=None, media_type='movie'):
    """
    Recommander un média basé sur le titre, le genre, et le type de média.
    Si le genre est fourni et ne correspond pas directement, on cherche le genre le plus proche.
    """

    if media_type == 'film':
        media_type = 'movie'

    if media_type == 'tv':
        genre_list = ["Action & adventure", "Animation", "Comédie", "Crime", "Documentaire", "Drame", "Familial","Kids", "Mystère", "News", "Reality","Science - fiction & fantastique","Soap","Talk","War & politics","Western"]
    else:
        genre_list = ["Action", "Aventure", "Animation", "Comédie", "Crime", "Documentaire", "Drame", "Familial",
                      "Fantastique", "Histoire", "Horreur", "Musique", "Mystère", "Romance", "Science-fiction", "Téléfilm",
                      "Thriller", "Guerre", "Western"]

    # Si le genre n'est pas None mais ne correspond pas directement, trouver le plus proche
    if genre and genre not in genre_list:
        closest_genre = min(genre_list, key=lambda g: levenshtein_distance(genre, g))
        print(f"Genre '{genre}' non trouvé. Utilisation du genre le plus proche : {closest_genre}.")
        genre = closest_genre

    results = search_media(query=title, genre_name=genre, media_type=media_type)
    if not results:
        print(f"Aucun {media_type} trouvé.")
        return

    return str(results)

def propose_recommendations(media_type='movie'):
    genres = get_genre_list(media_type)

    # Afficher les genres disponibles
    if genres:
        print("\n=== Genres Disponibles ===")
        for genre_name in genres.keys():
            print(f"- {genre_name.capitalize()}")

    # Choisir une recherche par titre ou par genre
    user_choice = input("\nVoulez-vous rechercher par titre ou par genre? (titre/genre) : ").strip().lower()

    results = []
    if user_choice == 'titre':
        title = input("Entrez le titre : ").strip()
        results = recommend_media(title=title, media_type=media_type)
    elif user_choice == 'genre':
        genre = input("Entrez le genre : ").strip()
        results = recommend_media(genre=genre, media_type=media_type)
    else:
        print("Choix non valide. Veuillez réessayer.")
        return

    # Conversion de la chaîne en liste si nécessaire
    if isinstance(results, str):
        try:
            results = ast.literal_eval(results)
        except Exception as e:
            print(f"Erreur lors de la conversion des résultats : {e}")
            return

    # Vérification et affichage des résultats
    if results and isinstance(results, list) and len(results) > 0:
        print("\n======= Résultats de la Recherche =======\n")
        for index, result in enumerate(results, start=1):
            title = result.get('title', 'Titre non disponible')
            release_date = result.get('release_date', 'Non spécifiée')
            overview = result.get('overview', 'Aucun synopsis disponible').replace("\n", " ")
            popularity = result.get('popularity', 'N/A')
            vote_average = result.get('vote_average', 'N/A')
            vote_count = result.get('vote_count', 0)
            poster_path = result.get('poster_path', 'Non disponible')

            print(f"{index}. Titre : {title}")
            print(f"   Date de sortie : {release_date}")
            print(f"   Note : {vote_average} ({vote_count} votes)")
            print(f"   Popularité : {popularity}")
            print(f"   Synopsis : {overview[:150]}...")
            print(f"   Affiche : {poster_path}")
            print("\n---\n")
    else:
        print("Aucun résultat trouvé. Veuillez vérifier votre saisie ou réessayer.")


if __name__ == "__main__":
    print("Recommandations de Films :")
    propose_recommendations(media_type='movie')

    print("\nRecommandations de Séries TV :")
    propose_recommendations(media_type='tv')
