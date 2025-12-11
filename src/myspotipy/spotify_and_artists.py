import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Replace these with your Spotify API credentials
SPOTIPY_CLIENT_ID = '51414a9bac514659a29b32e5f5973e0e'
SPOTIPY_CLIENT_SECRET = '5a10d84c734a468bb0c45454eedfcb5d'

# The playlist URL or ID
PLAYLIST_URL = 'https://open.spotify.com/playlist/0meTsYyNGv1A2SUDFyXdEf?si=64a1b8267037406c'
def get_playlist_id(url):
    if 'playlist/' in url:
        return url.split('playlist/')[1].split('?')[0]
    return url

def main():
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET
    ))

    playlist_id = get_playlist_id(PLAYLIST_URL)
    results = sp.playlist_tracks(playlist_id)
    artists_set = set()

    while results:
        for item in results['items']:
            track = item['track']
            if not track:
                continue
            # Main artists
            for artist in track['artists']:
                name = artist['name']
                if '&' in name or ' and ' in name.lower():
                    artists_set.add(name)
        # Pagination
        if results['next']:
            results = sp.next(results)
        else:
            break

    print("Artists or featured artists with '&' or 'and' in their name:")
    for artist in sorted(artists_set):
        print(artist)

if __name__ == '__main__':
    main()
