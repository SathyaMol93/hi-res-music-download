import os
import glob
from pydub import AudioSegment
from mutagen.mp4 import MP4, MP4Cover
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

def add_metadata_to_alac(alac_file, metadata, album_cover_file):
    audio = MP4(alac_file)
    audio['\xa9nam'] = metadata['title']
    audio['\xa9ART'] = metadata['artist']
    audio['\xa9alb'] = metadata['album']
    audio['\xa9day'] = metadata['release_date']
    
    with open(album_cover_file, 'rb') as f:
        audio['covr'] = [MP4Cover(f.read(), imageformat=MP4Cover.FORMAT_JPEG)]
    
    audio.save()

def convert_to_alac(flac_file, output_folder):
    audio = AudioSegment.from_file(flac_file, format='flac')
    alac_file = os.path.join(output_folder, os.path.basename(flac_file).replace('.flac', '.m4a'))
    audio.export(alac_file, format='ipod')
    return alac_file

def process_audio_files(input_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created directory: {output_folder}")
        
    flac_files = glob.glob(os.path.join(input_folder, '*.flac'))
    print(f"Found {len(flac_files)} FLAC files in {input_folder}")

    for flac_file in flac_files:
        print(f"Processing file: {flac_file}")
        alac_file = convert_to_alac(flac_file, output_folder)
        
        track_name = os.path.basename(alac_file).replace('.m4a', '')
        metadata = fetch_spotify_metadata(track_name)
        
        if metadata:
            print(f"Fetched metadata for {track_name}: {metadata}")
            album_cover_file = download_album_cover(metadata['album_cover_url'])
            if album_cover_file:
                add_metadata_to_alac(alac_file, metadata, album_cover_file)
                os.remove(album_cover_file)  # Clean up album cover file
                print(f"Added metadata to {alac_file}")
            else:
                print(f"Failed to download album cover for {track_name}")
        else:
            print(f"No metadata found for {track_name}")

# Example usage
input_folder = './MusicDownloads/Favorite'  # Folder containing your FLAC files
output_folder = input_folder + '_ALAC'  # Output folder for converted ALAC files

# Convert FLAC files to ALAC and add metadata
process_audio_files(input_folder, output_folder)
