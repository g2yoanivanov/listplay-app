import requests

from core.models import SpotifyToken


class SpotifyException(Exception):
    """
    Custom exception class for handling Spotify API-related errors.
    """
    pass


def get_valid_token(user):
    """
    Retrieves a valid Spotify access token for the given user. If the token is expired,
    it refreshes the token using the refresh token.
    """
    try:
        spotify_token = SpotifyToken.objects.get(user=user)
    except SpotifyToken.DoesNotExist:
        raise SpotifyException("No valid Spotify token found for the user.")

    if not spotify_token.is_valid():
        spotify_token.refresh()

    return spotify_token.access_token


def search_tracks(user, query, limit=10):
    """
    Searches for tracks on Spotify based on the provided query.

    Args:
        user: The user performing the search.
        query: The search query string.
        limit: The maximum number of results to return (default is 10).
    """
    access_token = get_valid_token(user)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    search_url = "https://api.spotify.com/v1/search?q={query}&type=track&limit={limit}"
    response = requests.get(search_url, headers=headers)

    if response.status_code != 200:
        error_msg = response.json().get("error", {}).get("message", "Unknown error.")
        raise SpotifyException(f"Failed to search tracks on Spotify: {error_msg}")

    tracks_data = response.json().get("tracks", {}).get("items", [])
    formatted_tracks = []

    for track in tracks_data:
        formatted_tracks.append({
            'spotify_id': track.get("id"),
            'title': track.get("name"),
            'artists': [artist.get("name") for artist in track.get("artists", [])],
            'duration_ms': track.get("duration_ms"),
            'image_url': track.get("album", {}).get("images", [{}])[0].get("url")
        })

    return formatted_tracks


def create_plalist_on_spotify(user, name, description="", public=False):
    """
    Creates a new playlist on Spotify for the given user.
    """
    access_token = get_valid_token(user)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    profile_response = requests.get('https://api.spotify.com/v1/me', headers=headers)
    if profile_response.status_code != 200:
        error_msg = profile_response.json().get("error", {}).get("message", "Unknown error.")
        raise SpotifyException(f"Failed to retrieve user profile from Spotify: {error_msg}")

    spotify_user_id = profile_response.json().get("id")

    create_url = f"https://api.spotify.com/v1/users/{spotify_user_id}/playlists"
    payload = {
        'name': name,
        'description': description,
        'public': public
    }

    playlist_response = requests.post(create_url, headers=headers, json=payload)
    if playlist_response.status_code not in [200, 201]:
        error_msg = playlist_response.json().get("error", {}).get("message", "Unknown error.")
        raise SpotifyException(f"Failed to create playlist on Spotify: {error_msg}")

    return playlist_response.json()


def add_tracks_to_spotify_playlist(user, spotify_playlist_id, spotify_track_ids):
    """
    Adds a track to a Spotify playlist for the given user.
    """
    access_token = get_valid_token(user)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    tracks_uris = [f"spotify:track:{track_id}" for track_id in spotify_track_ids]

    url = f"https://api.spotify.com/v1/playlists/{spotify_playlist_id}/tracks"
    payload = {
        'uris': tracks_uris
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code not in [200, 201]:
        error_msg = response.json().get("error", {}).get("message", "Unknown error.")
        raise SpotifyException(f"Failed to add track to Spotify playlist: {error_msg}")

    return response.json()
