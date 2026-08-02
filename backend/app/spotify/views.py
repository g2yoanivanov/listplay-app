"""
Views for the Spotify API related operations.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from urllib.parse import urlencode

import requests
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.shortcuts import get_object_or_404

from core.models import (
    SpotifyToken,
    Playlist,
    Track,
    Artist
)

from .services import (
    SpotifyException,
    search_tracks,
    create_plalist_on_spotify,
    add_tracks_to_spotify_playlist
)


class AuthURLView(APIView):
    """
    Generates the Spotify authorization URL.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        scopes = 'playlist-modify-public playlist-modify-private'

        params = {
            'client_id': settings.SPOTIFY_CLIENT_ID,
            'response_type': 'code',
            'redirect_uri': settings.SPOTIFY_REDIRECT_URI,
            'scope': scopes,
        }

        url = 'https://accounts.spotify.com/authorize?' + urlencode(params)

        return Response({'url': url}, status=status.HTTP_200_OK)


class SpotifyCallbackView(APIView):
    """
    Exchange the authorization code for Spotify access token
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        code = request.GET.get('code')
        error = request.GET.get('error')

        if error:
            return Response(
                {'error': f'Spotify error: {error}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not code:
            return Response(
                {'error': 'No code provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        token_url = 'https://accounts.spotify.com/api/token'

        payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': settings.SPOTIFY_REDIRECT_URI,
            'client_id': settings.SPOTIFY_CLIENT_ID,
            'client_secret': settings.SPOTIFY_CLIENT_SECRET,
        }

        response = requests.post(token_url, data=payload)
        token_info = response.json()

        if 'error' in token_info:
            return Response(
                {'error': token_info.get('error_description', 'Failed to get token')},
                status=status.HTTP_400_BAD_REQUEST
            )

        access_token = token_info.get('access_token')
        refresh_token = token_info.get('refresh_token')
        expires_in = token_info.get('expires_in')
        token_type = token_info.get('token_type')

        expires_at = timezone.now() + timedelta(seconds=expires_in)

        SpotifyToken.objects.update_or_create(
            user=request.user,
            defaults={
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_in': expires_at,
                'token_type': token_type,
            }
        )

        return Response({'message': 'Spotify account successfully connected!'}, status=status.HTTP_200_OK)


class SpotifySearchView(APIView):
    """
    Search tracks on Spotify by a key word.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.GET.get('q')

        if not query:
            return Response(
                {'error': 'No search query provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            results = search_tracks(request.user, query)
            return Response({'results': results}, status=status.HTTP_200_OK)
        except SpotifyException as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(
                {'error': 'An unexpected error occurred while searching tracks.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ExportPlaylistView(APIView):
    """
    Export a playlist to Spotify.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, playlist_id):
        playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
        valid_tracks = playlist.tracks.exclude(spotify_id__isnull=True).exclude(spotify_id__exact='')

        if not valid_tracks.exists():
            return Response(
                {'error': 'No valid tracks with Spotify IDs found in the playlist.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        track_ids = [track.spotify_id for track in valid_tracks]

        try:
            spotify_playlist = create_plalist_on_spotify(
                user=request.user,
                name=playlist.name,
                description=playlist.description or "Exported from ListPlay"
            )

            add_tracks_to_spotify_playlist(
                user=request.user,
                spotify_playlist_id=spotify_playlist['id'],
                spotify_track_ids=track_ids
            )

            return Response(
                {
                    'message': 'Playlist successfully exported to Spotify!',
                    'spotify_url': spotify_playlist.get('external_urls', {}).get('spotify', '')
                },
                status=status.HTTP_201_CREATED
            )
        except SpotifyException as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response(
                {'error': 'An unexpected error occurred while exporting the playlist.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AddTrackToPlaylistView(APIView):
    """
    Add a track to a specific playlist.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, playlist_id):
        playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)

        spotify_id = request.data.get('spotify_id')
        title = request.data.get('title')
        artists = request.data.get('artists')
        duration_ms = request.data.get('duration_ms', 0)
        image_url = request.data.get('image_url', '')

        if not all([spotify_id, title, artists]):
            return Response(
                {'error': 'Missing required track information.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        track, created = Track.objects.get_or_create(
            spotify_id=spotify_id,
            defaults={
                'title': title,
                'duration_ms': duration_ms,
                'image_url': image_url
            }
        )

        if created:
            artists_obj = []
            for artist_item in artists:
                if isinstance(artist_item, dict):
                    artist_obj, _ = Artist.objects.get_or_create(
                        spotify_id=artist_item.get('spotify_id'),
                        defaults={'name': artist_item.get('name')}
                    )

                else:
                    artist_obj, _ = Artist.objects.get_or_create(
                        name=artist_item
                    )

                artists_obj.append(artist_obj)

            track.artists.set(artists_obj)

        if track in playlist.tracks.all():
            return Response(
                {'error': 'Track already exists in the playlist.'},
                status=status.HTTP_200_OK
            )

        playlist.tracks.add(track)

        return Response(
            {
                'message': 'Track added to playlist successfully.',
                'track_id': track.id,
                'spotify_id': track.spotify_id,
                'title': track.title,
                'was_created': created
            },
            status=status.HTTP_201_CREATED
        )
