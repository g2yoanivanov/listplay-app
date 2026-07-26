"""
Tests for the Playlist API.
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Genre,
    Artist,
    Track
)

GENRES_URL = reverse('playlist:genre-list')
ARTISTS_URL = reverse('playlist:artist-list')
TRACKS_URL = reverse('playlist:track-list')


def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)


class PublicMusicApiTests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required for music endpoints."""
        res = self.client.get(ARTISTS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateMusicApiTests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='test@example.com', password='password123')
        self.client.force_authenticate(self.user)

    def test_retrieve_genres(self):
        """Test retrieving a list of genres."""
        Genre.objects.create(name='Rock')
        Genre.objects.create(name='Pop')

        res = self.client.get(GENRES_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)

    def test_create_artist_with_nested_genres(self):
        """Test creating an artist and automatically creating/linking genres."""
        payload = {
            'spotify_id': 'artist_123',
            'name': 'The Beatles',
            'genres': [
                {'name': 'Rock'},
                {'name': 'Classic'}
            ]
        }
        res = self.client.post(ARTISTS_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        artist = Artist.objects.get(spotify_id='artist_123')
        self.assertEqual(artist.name, 'The Beatles')
        self.assertEqual(artist.genres.count(), 2)

        self.assertTrue(Genre.objects.filter(name='Rock').exists())
        self.assertTrue(Genre.objects.filter(name='Classic').exists())

    def test_create_track_with_nested_artists(self):
        """Test creating a track and automatically creating/linking artists."""
        payload = {
            'spotify_id': 'track_123',
            'title': 'Hey Jude',
            'duration_ms': 300000,
            'cover_url': 'http://example.com/cover.jpg',
            'artists': [
                {'spotify_id': 'artist_123', 'name': 'The Beatles'}
            ]
        }
        res = self.client.post(TRACKS_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        track = Track.objects.get(spotify_id='track_123')
        self.assertEqual(track.title, 'Hey Jude')
        self.assertEqual(track.artists.count(), 1)

        artist = track.artists.first()
        self.assertEqual(artist.spotify_id, 'artist_123')
        self.assertEqual(artist.name, 'The Beatles')

    def test_create_track_with_existing_artist_update(self):
        """Test that adding a track with an existing artist updates the artist's name."""
        Artist.objects.create(spotify_id='artist_123', name='Old Name')

        payload = {
            'spotify_id': 'track_999',
            'title': 'New Song',
            'duration_ms': 200000,
            'artists': [
                {'spotify_id': 'artist_123', 'name': 'Updated Name'}
            ]
        }
        res = self.client.post(TRACKS_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Artist.objects.count(), 1)

        artist = Artist.objects.get(spotify_id='artist_123')
        self.assertEqual(artist.name, 'Updated Name')
