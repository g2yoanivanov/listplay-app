from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from unittest.mock import patch

from urllib.parse import urlparse, parse_qs

from core.models import SpotifyToken

AUTH_URL = reverse('spotify:get-auth-url')
CALLBACK_URL = reverse('spotify:spotify-callback')


class PublicSpotifyApiTests(TestCase):
    """Test unauthenticated users"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_url_unauthenticated(self):
        """
        Test unauthenticated users cannot generate a link
        """
        res = self.client.get(AUTH_URL)

        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


class PrivateSpotifyApiTests(TestCase):
    """
    Test logged in users
    """
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user('authuser@example.com', 'testpass123')
        self.client.force_authenticate(self.user)

    @override_settings(
        SPOTIFY_CLIENT_ID='test_client_id_123',
        SPOTIFY_REDIRECT_URI='http://localhost:8000/api/spotify/callback/'
    )
    def test_get_auth_url_success(self):
        """
        Test generating login url for Spotify.
        """
        res = self.client.get(AUTH_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('url', res.data)

        url = res.data['url']

        self.assertTrue(url.startswith('https://accounts.spotify.com/authorize'))

        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)

        self.assertEqual(query_params['client_id'][0], 'test_client_id_123')
        self.assertEqual(query_params['response_type'][0], 'code')
        self.assertEqual(query_params['redirect_uri'][0], 'http://localhost:8000/api/spotify/callback/')
        self.assertEqual(query_params['scope'][0], 'playlist-modify-public playlist-modify-private')

    @patch('spotify.views.requests.post')
    def test_spotify_callback_success(self, mock_post):
        """
        Test successful retrieving access token
        """
        class MockResponse:
            def json(self):
                return {
                    'access_token': 'test_access_token_123',
                    'refresh_token': 'test_refresh_token_456',
                    'expires_in': 3600,
                    'token_type': 'Bearer'
                }

        mock_post.return_value = MockResponse()

        res = self.client.get(CALLBACK_URL, {'code': 'auth_code_from_spotify'})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('successfully connected', res.data['message'])

        token_exists = SpotifyToken.objects.filter(user=self.user).exists()
        self.assertTrue(token_exists)

        token = SpotifyToken.objects.get(user=self.user)
        self.assertEqual(token.access_token, 'test_access_token_123')
        self.assertEqual(token.refresh_token, 'test_refresh_token_456')

    def test_spotify_callback_missing_code(self):
        """
        Test callback does not return code
        """
        res = self.client.get(CALLBACK_URL)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('No code provided', res.data['error'])

    def test_spotify_callback_with_error_param(self):
        """
        Test error in url - the user denied access"
        """
        res = self.client.get(CALLBACK_URL, {'error': 'access_denied'})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Spotify error: access_denied', res.data['error'])

    @patch('spotify.views.requests.post')
    def test_spotify_callback_invalid_code(self, mock_post):
        """
        Test handling errors
        """
        class MockResponse:
            def json(self):
                return {
                    'error': 'invalid_grant',
                    'error_description': 'Invalid authorization code'
                }
        mock_post.return_value = MockResponse()

        res = self.client.get(CALLBACK_URL, {'code': 'invalid_or_expired_code'})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['error'], 'Invalid authorization code')
