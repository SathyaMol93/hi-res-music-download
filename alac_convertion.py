import os
import glob
import subprocess
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
    alac_file = os.path.join(output_folder, os.path.basename(flac_file).replace('.flac', '.m4a'))
    if os.path.exists(alac_file):
        print(f"Skipping already converted file: {alac_file}")
        return alac_file
    
    command = [
        'ffmpeg',
        '-i', flac_file,
        '-map', '0:a:0',
        '-acodec', 'alac',
        alac_file
    ]
    subprocess.run(command, check=True)
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

def add_songs_to_itunes(input_folder):
    import win32com.client  # Move the import here to avoid issues if not on Windows

    itunes = win32com.client.Dispatch("iTunes.Application")
    library = itunes.LibraryPlaylist
    playlists = itunes.LibrarySource.Playlists

    playlist_name = os.path.basename(os.path.dirname(input_folder))
    new_playlist = None
    
    for playlist in playlists:
        if playlist.Name == playlist_name:
            new_playlist = playlist
            break
    
    if not new_playlist:
        new_playlist = itunes.CreatePlaylist(playlist_name)
    
    alac_files = glob.glob(os.path.join(input_folder, '*.m4a'))
    for alac_file in alac_files:
        new_playlist.AddFile(alac_file)
        print(f"Added {alac_file} to {playlist_name}")

def process_and_sync_music(base_folder, start_folder=None):
    folders = [f.path for f in os.scandir(base_folder) if f.is_dir()]

    if start_folder:
        # Convert folder name to full path if it's not already
        start_folder_path = os.path.join(base_folder, start_folder) if not os.path.isabs(start_folder) else start_folder
        print(f"Starting from folder: {start_folder_path}")

        if start_folder_path in folders:
            start_index = folders.index(start_folder_path)
            folders = folders[start_index:]
        else:
            print(f"Start folder '{start_folder}' not found in base folder.")
            return
    
    for folder in folders:
        output_folder = folder + '_ALAC'
        process_audio_files(folder, output_folder)
        add_songs_to_itunes(output_folder)

# Example usage
base_folder = './MusicDownloads'  # Base folder for all music
start_folder = 'Clean Rap Songs Playlist 2024 - Clean Rap & Hip-Hop Music 2024'  # Replace with specific folder name if needed

# Convert FLAC files to ALAC, add metadata, and sync to iTunes
process_and_sync_music(base_folder, start_folder)
