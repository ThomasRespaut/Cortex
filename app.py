from flask import Flask, redirect, request, session, url_for, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from requests_oauthlib import OAuth2Session
import google_auth_oauthlib.flow
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

app = Flask(__name__)

app.secret_key = os.urandom(24)
app.config['SESSION_COOKIE_NAME'] = 'session-cookie'

# Pour autoriser les transports non sécurisés (http) pendant le développement
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Spotify credentials
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")

SPOTIPY_SCOPE = (
    "ugc-image-upload "
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-read-currently-playing "
    "app-remote-control "
    "streaming "
    "playlist-read-private "
    "playlist-read-collaborative "
    "playlist-modify-private "
    "playlist-modify-public "
    "user-follow-modify "
    "user-follow-read "
    "user-library-read "
    "user-library-modify "
    "user-read-email "
    "user-read-private "
    "user-top-read "
    "user-read-recently-played "
    "user-read-playback-position"
)

# Google credentials
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.addons.current.message.metadata",
    "https://www.googleapis.com/auth/gmail.addons.current.action.compose",
    "https://www.googleapis.com/auth/gmail.metadata",
    "https://www.googleapis.com/auth/tasks.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.insert",
    "https://www.googleapis.com/auth/gmail.addons.current.message.action",
    "https://www.googleapis.com/auth/tasks",
    "https://www.googleapis.com/auth/gmail.addons.current.message.readonly",
    "https://www.googleapis.com/auth/youtubepartner",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/contacts",
    "https://www.googleapis.com/auth/calendar",
]

@app.route('/')
def index():
    return '''
        <h1>Bienvenue sur T.O.M!</h1>
        <a href="/login_spotify">Se connecter à Spotify</a> | 
        <a href="/login_linkedin">Se connecter à LinkedIn</a> | 
        <a href="/login_google">Se connecter à Google</a> | 
        <a href="/logout">Se déconnecter</a>
    '''

# Spotify Login
@app.route('/login_spotify')
def login_spotify():
    if 'oauth_token_spotify' in session:
        return redirect(url_for('recently_played'))

    sp_oauth = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=SPOTIPY_SCOPE
    )

    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback_spotify')
def callback_spotify():
    sp_oauth = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=SPOTIPY_SCOPE
    )

    try:
        token_info = sp_oauth.get_access_token(request.args['code'])
        session['oauth_token_spotify'] = token_info
        return redirect(url_for('get_token'))
    except Exception as e:
        return f"Failed to fetch token: {e}", 400

@app.route('/token')
def get_token():
    token_info = session.get('oauth_token_spotify')
    if not token_info:
        return jsonify({"error": "Token not found. Please login first."}), 404

    if isinstance(token_info, str):
        return jsonify({"error": "Token info is not in the correct format."}), 400

    return jsonify({
        "access_token": token_info.get('access_token'),
        "token_type": token_info.get('token_type'),
        "expires_in": token_info.get('expires_in'),
        "refresh_token": token_info.get('refresh_token'),
        "scope": token_info.get('scope'),
        "expires_at": token_info.get('expires_at')
    })

@app.route('/recently_played')
def recently_played():
    token_info = session.get('oauth_token_spotify')
    if not token_info:
        return redirect(url_for('login_spotify'))

    sp = spotipy.Spotify(auth=token_info['access_token'])
    results = sp.current_user_recently_played(limit=10)

    tracks = [f"{idx + 1}: {item['track']['name']} by {item['track']['artists'][0]['name']}"
              for idx, item in enumerate(results['items'])]

    return '<br>'.join(tracks)

# Google Login
@app.route('/login_google')
def login_google():
    session.clear()  # Clear session to avoid any previous state issues
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        'google_secret.json', scopes=GOOGLE_SCOPES)
    flow.redirect_uri = url_for('callback_google', _external=True)

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

@app.route('/login/callback')
def callback_google():
    state = session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        'google_secret.json', scopes=GOOGLE_SCOPES, state=state)
    flow.redirect_uri = url_for('callback_google', _external=True)

    authorization_response = request.url
    try:
        flow.fetch_token(authorization_response=authorization_response)
    except Exception as e:
        return f"Failed to fetch token: {e}", 400

    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)

    return redirect(url_for('google_token'))


@app.route('/google_token')
def google_token():
    if 'credentials' not in session:
        return redirect(url_for('login_google'))

    return jsonify(session['credentials'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

if __name__ == "__main__":
    app.run(debug=True, port=8888)

