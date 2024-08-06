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

# Set the absolute path for the cache file
cache_file = os.path.join(os.path.expanduser("~"), '.cache-spotify')
track_cache_file = os.path.join(os.path.expanduser("~"), '.track_cache.json')

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

        response.raise_for_status()  # Raise an error for bad responses
        data = response.json()
        releases = data.get('releases', [])
        collection.extend(releases)

        if not data['pagination']['items']:
            break
        page += 1

    print(f"Retrieved {len(collection)} albums from Discogs.")
    return collection

def check_and_remove_duplicates(playlist_id, existing_tracks):
    print("Checking for duplicates in the playlist...")
    all_tracks = sp.playlist_tracks(playlist_id)

    track_titles = {}
    duplicate_count = 0

    # Fetch all pages of tracks
    while True:
        for track in all_tracks['items']:
            track_title = track['track']['name'].lower()  # Normalize case for comparison
            track_uri = track['track']['uri']

            if track_title in track_titles:
                # If the title already exists, remove the duplicate track
                sp.playlist_remove_all_occurrences_of_items(playlist_id, [track_uri])
                duplicate_count += 1
                print(f"Removed duplicate track: {track_title}")
            else:
                track_titles[track_title] = track_uri

        # Check for more pages
        if all_tracks['next']:
            all_tracks = sp.next(all_tracks)
        else:
            break

    print(f"Removed a total of {duplicate_count} duplicate tracks from the playlist.")

def load_track_cache():
    if os.path.exists(track_cache_file):
        with open(track_cache_file, 'r') as f:
            return json.load(f)
    return {}

def save_track_cache(track_ids):
    with open(track_cache_file, 'w') as f:
        json.dump(track_ids, f)

def create_or_update_playlist(collection):
    user_id = sp.me()['id']
    playlist_name = "RECORD COLLECTION" #Spotify playlist name Change to whatever you prefer
    playlist_description = "all my vinyl as logged in my Discogs account. updated via a Python script." #Spotify description Change to whatever you prefer
    
    # Initialize existing_tracks to an empty set
    existing_tracks = set()
    new_albums_added = set()  # Keep track of unique albums added

    # Check if the playlist already exists
    playlists = sp.user_playlists(user_id)
    playlist_id = None
    for playlist in playlists['items']:
        if playlist['name'] == playlist_name:
            playlist_id = playlist['id']
            break
    
    if playlist_id is None:
        playlist = sp.user_playlist_create(user_id, playlist_name, description=playlist_description)
        playlist_id = playlist['id']
    else:
        # Retrieve existing tracks only if the playlist exists
        existing_tracks = {track['track']['uri'] for track in sp.playlist_tracks(playlist_id)['items']}
        check_and_remove_duplicates(playlist_id, existing_tracks)

    new_tracks = []
    skipped_albums = []
    not_found_albums = []
    fallback_results = []  # To keep track of fallback results

    # Load track cache
    track_cache = load_track_cache()

    for item in collection:
        album_name = item["basic_information"]["title"]
        artist_name = item["basic_information"]["artists"][0]["name"]
        search_query = f"album:{album_name} artist:{artist_name}"
        
        print(f"Searching for: {search_query}")
        search_results = sp.search(q=search_query, type='album')
        
        if search_results['albums']['items']:
            album_uri = search_results['albums']['items'][0]['uri']
            tracks = sp.album_tracks(album_uri)
            for track in tracks['items']:
                track_uri = track['uri']
                track_title = track['name'].lower()

                # Check if the track is in the cache or existing playlist
                if track_uri in existing_tracks or track_uri in track_cache:
                    continue  # Skip if the track is already in the playlist or cache
                else:
                    new_tracks.append(track_uri)
                    new_albums_added.add(album_name)  # Track the album being added

            print(f"Added tracks from album: {album_name}")
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
                        track_title = track['name'].lower()
                        if track_uri not in existing_tracks and track_uri not in track_cache:  # Check against existing and cached tracks
                            new_tracks.append(track_uri)
                            new_albums_added.add(album_name)  # Track the album being added
                    fallback_results.append((search_query, fallback_results_search['albums']['items'][0]['name']))
                    print(f"Used fallback album: {fallback_results_search['albums']['items'][0]['name']}")
                else:
                    not_found_albums.append(album_name)
                    print(f"Album artist name mismatch for fallback: {fallback_artist_name} (original: {artist_name})")
            else:
                not_found_albums.append(album_name)
                print(f"Album still not found: {album_name}")

    # Add new tracks to the playlist in chunks of 100
    while new_tracks:
        chunk = new_tracks[:100]
        sp.playlist_add_items(playlist_id, chunk)
        new_tracks = new_tracks[100:]

    # Print the total number of new albums added
    # Functionality here is a bit iffy, may not be accurate
    if new_albums_added:
        print(f"Total number of albums added since the script last ran: {len(new_albums_added)}")
        print("Albums added:")
        for album in new_albums_added:
            print(album)
    else:
        print("No new albums were added.")
    print()
    if not_found_albums:
        print("Albums not found in Spotify:")
        for album in not_found_albums:
            print(album)

    if fallback_results:
        print("\nFallback searches used:")
        for original_query, fallback_album in fallback_results:
            print(f"Original: {original_query} -> Fallback: {fallback_album}")

    # Save track cache
    track_cache.update({track_uri for track_uri in new_tracks})
    save_track_cache(track_cache)

    # Final check for duplicates after adding tracks
    check_and_remove_duplicates(playlist_id, existing_tracks)

# Example usage
collection = get_discogs_collection()
create_or_update_playlist(collection)
