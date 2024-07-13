import os
import glob
from pydub import AudioSegment
from mutagen.flac import FLAC, Picture
from PIL import Image
import requests
from yt_dlp import YoutubeDL
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

def download_youtube_playlist(playlist_url, output_folder):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'flac',
            'preferredquality': '0',  # best quality
        }],
        'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([playlist_url])

def process_audio_files(folder_path):
    flac_files = glob.glob(os.path.join(folder_path, '*.flac'))
    for flac_file in flac_files:
        track_name = os.path.basename(flac_file).replace('.flac', '')
        metadata = fetch_spotify_metadata(track_name)
        
        if metadata:
            album_cover_file = download_album_cover(metadata['album_cover_url'])
            if album_cover_file:
                add_metadata_to_flac(flac_file, metadata, album_cover_file)
                os.remove(album_cover_file)  # Clean up album cover file

# Example usage
playlist_url = 'https://www.youtube.com/watch?v=lp-EO5I60KA&list=PLxXoHPNsmuck7BoEY8pKHFCJZb9l7JsKm'  # Replace with your YouTube playlist URL
folder_path = './AllOut2010'  # Update this path if needed

# Step 1: Download YouTube playlist
download_youtube_playlist(playlist_url, folder_path)

# Step 2: Add metadata
process_audio_files(folder_path)
