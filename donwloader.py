import os
import glob
from pydub import AudioSegment
from mutagen.flac import FLAC, Picture
from PIL import Image
import requests
from yt_dlp import YoutubeDL, utils
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

def download_youtube_playlist(playlist_url, base_folder):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'flac',
            'preferredquality': '0',  # best quality
        }],
        'outtmpl': os.path.join(base_folder, '%(playlist)s', '%(title)s.%(ext)s'),
        'noplaylist': False,
        'ignoreerrors': True,  # Ignore errors and continue with the next video
    }
    
    with YoutubeDL(ydl_opts) as ydl:
        try:
            playlist_info = ydl.extract_info(playlist_url, download=False)
            playlist_title = playlist_info.get('title', 'Unknown Playlist').replace('/', '_').replace('\\', '_')
            output_folder = os.path.join(base_folder, playlist_title)
            
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
                print(f"Created directory: {output_folder}")
            
            ydl_opts['outtmpl'] = os.path.join(output_folder, '%(title)s.%(ext)s')
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([playlist_url])
            
        except utils.DownloadError as e:
            print(f"Error extracting playlist info: {e}")
    
    return output_folder

def process_audio_files(folder_path):
    flac_files = glob.glob(os.path.join(folder_path, '*.flac'))
    print(f"Found {len(flac_files)} FLAC files in {folder_path}")

    for flac_file in flac_files:
        print(f"Processing file: {flac_file}")
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
playlist_url = 'https://www.youtube.com/watch?v=RSqhSXx-jeE&list=PLSKsoW1K1XENCymMwQtJAO3UuQoewTeQS'  # Replace with your YouTube playlist URL
base_folder = './MusicDownloads'  # Base folder for all playlists

# Step 1: Download YouTube playlist
playlist_folder = download_youtube_playlist(playlist_url, base_folder)

# Step 2: Add metadata
process_audio_files(playlist_folder)
