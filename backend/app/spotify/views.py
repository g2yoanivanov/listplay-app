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

from core.models import SpotifyToken


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
