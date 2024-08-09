import os
import json
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import difflib

# Replace these with your actual Discogs and Spotify credentials
DISCOGS_API_TOKEN = 'REPLACE WITH YOUR DISCOGS API TOKEN'
SPOTIPY_CLIENT_ID = 'REPLACE WITH YOUR SPOTIFY CLIENT ID'
SPOTIPY_CLIENT_SECRET = 'REPLACE WITH YOUR SPOTIFY CLIENT SECRET'
SPOTIPY_REDIRECT_URI = 'http://localhost:8888/callback'
DISCOGS_USERNAME = 'REPLACE WITH YOUR DISCOGS USERNAME'

# Set the absolute path for the cache file and local JSON file
cache_file = os.path.join(os.path.expanduser("~"), '.cache-spotify')
library_cache_file = os.path.join(os.path.expanduser("~"), '.library_cache.json')

# Initialize Spotipy with required scopes and custom cache path
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                               client_secret=SPOTIPY_CLIENT_SECRET,
                                               redirect_uri=SPOTIPY_REDIRECT_URI,
                                               scope='playlist-modify-public playlist-modify-private user-library-modify',
                                               cache_path=cache_file))

def get_discogs_collection():
    collection = []
    page = 1

    while True:
        url = f"https://api.discogs.com/users/{DISCOGS_USERNAME}/collection/folders/0/releases?page={page}"
        headers = {"Authorization": f"Discogs token={DISCOGS_API_TOKEN}"}
        response = requests.get(url, headers=headers)

        if response.status_code == 404:
            print(f"No more pages to retrieve after page {page}. Ending collection retrieval.")
            break

        response.raise_for_status()
        data = response.json()
        releases = data.get('releases', [])
        collection.extend(releases)

        if not data['pagination']['items']:
            break
        page += 1

    print(f"Retrieved {len(collection)} albums from Discogs.")
    return collection

def load_library_cache():
    if os.path.exists(library_cache_file):
        with open(library_cache_file, 'r') as f:
            return json.load(f)
    return {}

def save_library_cache(library):
    with open(library_cache_file, 'w') as f:
        json.dump(library, f)

def create_or_update_playlist(collection):
    user_id = sp.me()['id']
    playlist_name = "My Record Collection"
    playlist_description = "all my vinyl as logged in my Discogs account. updated via a Python script."
    
    existing_library = load_library_cache()
    current_library = {item["basic_information"]["title"]: item for item in collection}

    new_albums = [album for album in current_library if album not in existing_library]

    if not new_albums:
        print("No new albums to add.")
        return

    playlist_id = None
    playlists = sp.user_playlists(user_id)
    for playlist in playlists['items']:
        if playlist['name'] == playlist_name:
            playlist_id = playlist['id']
            break

    if playlist_id is None:
        playlist = sp.user_playlist_create(user_id, playlist_name, description=playlist_description)
        playlist_id = playlist['id']

    new_tracks = []
    not_found_albums = []
    new_albums_added = set()

    for album_name in new_albums:
        artist_name = current_library[album_name]["basic_information"]["artists"][0]["name"]
        search_query = f"album:{album_name} artist:{artist_name}"
        
        print(f"Searching for: {search_query}")
        search_results = sp.search(q=search_query, type='album')

        if search_results['albums']['items']:
            album_uri = search_results['albums']['items'][0]['uri']
            tracks = sp.album_tracks(album_uri)
            for track in tracks['items']:
                track_uri = track['uri']
                new_tracks.append(track_uri)
            new_albums_added.add(album_name)
        else:
            # Fallback search if no album found
            print(f"Album not found, trying fallback search for: {album_name}")
            first_word_album = album_name.split()[0].lower()
            first_word_artist = artist_name.split()[0].lower()
            
            # Exclude 'The' or 'A' from the first word
            if first_word_album in ['the', 'a']:
                first_word_album = album_name.split()[1].lower() if len(album_name.split()) > 1 else ''
            if first_word_artist in ['the', 'a']:
                first_word_artist = artist_name.split()[1].lower() if len(artist_name.split()) > 1 else ''
                
            fallback_query = f"album:{first_word_album} artist:{first_word_artist}"
            fallback_results_search = sp.search(q=fallback_query, type='album')

            if fallback_results_search['albums']['items']:
                # Check if the artist name matches at least 75%
                fallback_artist_name = fallback_results_search['albums']['items'][0]['artists'][0]['name']
                similarity = difflib.SequenceMatcher(None, artist_name.lower(), fallback_artist_name.lower()).ratio()
                
                if similarity >= 0.75:
                    fallback_album_uri = fallback_results_search['albums']['items'][0]['uri']
                    tracks = sp.album_tracks(fallback_album_uri)
                    for track in tracks['items']:
                        track_uri = track['uri']
                        new_tracks.append(track_uri)
                    new_albums_added.add(album_name)
                    print(f"Used fallback album: {fallback_results_search['albums']['items'][0]['name']}")
                else:
                    not_found_albums.append(album_name)
                    print(f"Album artist name mismatch for fallback: {fallback_artist_name} (original: {artist_name})")
            else:
                not_found_albums.append(album_name)
                print(f"Album still not found: {album_name}")

    while new_tracks:
        chunk = new_tracks[:100]
        sp.playlist_add_items(playlist_id, chunk)
        new_tracks = new_tracks[100:]

    if new_albums_added:
        print(f"Added {len(new_albums_added)} new albums to the playlist.")

    if not_found_albums:
        print("Albums not found in Spotify:")
        for album in not_found_albums:
            print(album)

    save_library_cache(current_library)

# Example usage
collection = get_discogs_collection()
create_or_update_playlist(collection)
