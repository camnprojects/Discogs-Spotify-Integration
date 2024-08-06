# Spotify and Discogs Integration

This Python script integrates your Spotify account with your Discogs collection, allowing you to manage your vinyl records as playlists on Spotify.
## Features

- Discogs Collection Retrieval: Fetches your album collection from your Discogs account.
- Spotify Playlist Creation: Creates a playlist in your Spotify account and adds tracks based on your Discogs collection.
- Duplicate Checking: Ensures that duplicate tracks are not added to your Spotify playlist.
- Fallback Search Functionality: If an album is not found on Spotify, a fallback search is performed using the first word of the album and artist names to increase the chances of finding the correct album.
- Local Track Reference: Maintains a local JSON file to store track references, which is used to check for duplicates and manage tracks more efficiently.

## Requirements
Python 3.x
Libraries: requests, spotipy, difflib, json, os

## Setup
Install the required libraries:
``` 
pip install requests spotipy 
```
Obtain your API credentials for both Spotify and Discogs. Update the script with your credentials.
#### Getting API Credentials for Discogs
- **Discogs:**
    - API Token
- **Spotify:**
    - Client ID
    - Client Secret
    - Redirect URI

1. Access the Discogs Developer Portal at https://www.discogs.com/settings/developers
2. Generate a personal token.
    - You will then find your Discogs API Token on this page.

#### Getting API Credentials for Spotify

1. Access the Spotify Developer Dashboard
2. Log In and create a New Application:
    - Click on “Create an App.”
    - Fill in the required fields:
        - App Name: Choose a name for your application. (I used 'Discogs Integration')
        - App Description: Provide a brief description of what your application does.
	    - Accept the terms and conditions.
3. Get Your Client ID and Client Secret:
    - After creating the app, you will be redirected to the app details page.
    - Here, you will find your Client ID and Client Secret. Keep these safe, as you'll need them in your script.
    - You can also access this in the app settings page.
4. Set Redirect URI:
    - In the app settings, find the Redirect URIs section.
    - Click on “Edit Settings” and add your redirect URI (e.g., `http://localhost:8888/callback`). This is necessary for the OAuth process.

## How to Use
Run the script to start the process:
```
python your_script_name.py
```
The script will:
- Retrieve your Discogs collection.
- Create or update a Spotify playlist with the albums found in your Discogs collection.
- Check for duplicates and ensure that only unique tracks are added.

## JSON File

The script creates a local JSON file (.track_cache.json) that serves the following purposes:

Track Reference Storage: When tracks are searched for and added to the Spotify playlist, their IDs are stored in this JSON file for future reference.
Duplicate Checking: Before adding tracks to the Spotify playlist, the script checks this JSON file to see if the track IDs already exist. If a track is found, it will not be added again.

## Output

After running the script, the output will include:
- Total number of albums added since the last run.
- A list of albums not found in Spotify. These can then be manually searched for.
- Details about any fallback searches used.

### Output Example
```
No more pages to retrieve after page 5. Ending collection retrieval.
Retrieved X albums from Discogs.
Checking for duplicates in the playlist...
Removed a total of 0 duplicate tracks from the playlist.
Checking album: Album 1 by Artist 1 (ID)
Searching for: album:Album 1 artist:Artist 1
Added tracks from album: Album 1
Checking album: Album 2 by Artist 2
Searching for: album:Album 2 artist:Artist 2
Added tracks from album: Album 2
Album not found, trying fallback search for: Album 3
Using fallback album: Album 3 by Artist 3

Added Y new tracks to the playlist.

Total number of albums added since the script last ran: Z

Albums not found in Spotify:
- Album 3
Fallback searches used:
Original: Album 3 -> Fallback: Album 3 (from fallback search)

```
