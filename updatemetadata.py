import os
import glob
from mutagen.flac import FLAC, Picture
from PIL import Image
import requests
from spotipy.oauth2 import SpotifyOAuth
import spotipy

# Set up Spotify API credentials
SPOTIFY_CLIENT_ID = '7d3f60e483234ef6bfae3d9fa77669dc'
SPOTIFY_CLIENT_SECRET = 'a7bd5e86003a41d3a47dcb50a8a20686'
SPOTIFY_REDIRECT_URI = 'http://localhost:8888/callback'

credentials = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET, redirect_uri=SPOTIFY_REDIRECT_URI, scope="user-library-read")
sp = spotipy.Spotify(auth_manager=credentials)

def fetch_spotify_metadata(track_name):
    results = sp.search(q=track_name, limit=1)
    if results['tracks']['items']:
        track = results['tracks']['items'][0]
        album_cover_url = track['album']['images'][0]['url']
        metadata = {
            'title': track['name'],
            'artist': track['artists'][0]['name'],
            'album': track['album']['name'],
            'album_cover_url': album_cover_url,
            'release_date': track['album']['release_date']
        }
        return metadata
    return None

def download_album_cover(url, output_path='album_cover.jpg'):
    response = requests.get(url)
    if response.status_code == 200:
        with open(output_path, 'wb') as file:
            file.write(response.content)
        return output_path
    return None

def add_metadata_to_flac(flac_file, metadata, album_cover_file):
    audio = FLAC(flac_file)
    audio['title'] = metadata['title']
    audio['artist'] = metadata['artist']
    audio['album'] = metadata['album']
    audio['date'] = metadata['release_date']
    
    image = Image.open(album_cover_file)
    image_data = open(album_cover_file, 'rb').read()
    
    picture = Picture()
    picture.data = image_data
    picture.type = 3  # Front cover
    picture.mime = 'image/jpeg'
    picture.width, picture.height = image.size
    picture.depth = 24  # Color depth
    
    audio.add_picture(picture)
    audio.save()

def process_audio_files(folder_path):
    flac_files = glob.glob(os.path.join(folder_path, '*.flac'))
    print(f"Found {len(flac_files)} FLAC files in {folder_path}")

    for flac_file in flac_files:
        print(f"Processing file: {flac_file}")
        audio = FLAC(flac_file)
        
        # Check if metadata already exists
        if all(tag in audio for tag in ['title', 'artist', 'album', 'date']):
            print(f"Metadata already exists for {flac_file}, skipping...")
            continue
        
        track_name = os.path.basename(flac_file).replace('.flac', '')
        metadata = fetch_spotify_metadata(track_name)
        
        if metadata:
            print(f"Fetched metadata for {track_name}: {metadata}")
            album_cover_file = download_album_cover(metadata['album_cover_url'])
            if album_cover_file:
                add_metadata_to_flac(flac_file, metadata, album_cover_file)
                os.remove(album_cover_file)  # Clean up album cover file
                print(f"Added metadata to {flac_file}")
            else:
                print(f"Failed to download album cover for {track_name}")
        else:
            print(f"No metadata found for {track_name}")

# Example usage
playlist_folder = 'Clean Rap Songs Playlist 2024 - Clean Rap & Hip-Hop Music 2024'
base_folder = './MusicDownloads'
folder_path = os.path.join(base_folder, playlist_folder)  # Replace with the path to your folder containing FLAC files

# Add metadata to FLAC files
process_audio_files(folder_path)
