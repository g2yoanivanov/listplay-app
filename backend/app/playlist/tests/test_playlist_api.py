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
    Track,
    Playlist,
    PlaylistTrack
)
from playlist.serializers import (
    PlaylistSerializer,
    TrackSerializer
)


GENRES_URL = reverse('playlist:genre-list')
ARTISTS_URL = reverse('playlist:artist-list')
TRACKS_URL = reverse('playlist:track-list')
PLAYLISTS_URL = reverse('playlist:playlist-list')


def playlist_detail_url(playlist_id):
    """Create and return a playlist detail URL."""
    return reverse('playlist:playlist-detail', args=[playlist_id])


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
        self.assertEqual(len(res.data['results']), 2)

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


class PlaylistSerializerTests(TestCase):
    """
    Test the PlaylistSerializer logic.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='user@example.com',
            password='password123'
        )

        self.track1 = Track.objects.create(
            spotify_id='track_001',
            title='Song 1',
            duration_ms=200000
        )
        self.track2 = Track.objects.create(
            spotify_id='track_002',
            title='Song 2',
            duration_ms=210000
        )

    def test_create_empty_playlist(self):
        """
        Test creating a playlist without any tracks.
        """
        data = {
            'name': 'My Chill Playlist',
            'description': 'Perfect for coding.'
        }

        serializer = PlaylistSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        playlist = serializer.save(created_by=self.user)

        self.assertEqual(playlist.name, 'My Chill Playlist')
        self.assertEqual(playlist.tracks.count(), 0)

    def test_create_playlist_with_tracks(self):
        """Test creating a playlist with initial tracks."""
        data = {
            'name': 'Workout Mix',
            'add_tracks': [
                {'spotify_id': 'track_001', 'order': 1},
                {'spotify_id': 'track_002', 'order': 2}
            ]
        }

        serializer = PlaylistSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        playlist = serializer.save(created_by=self.user)

        self.assertEqual(playlist.tracks.count(), 2)

        pt_1 = PlaylistTrack.objects.get(playlist=playlist, track=self.track1)
        self.assertEqual(pt_1.order, 1)

        pt_2 = PlaylistTrack.objects.get(playlist=playlist, track=self.track2)
        self.assertEqual(pt_2.order, 2)

    def test_update_playlist_tracks(self):
        """
        Test updating a playlist to completely replace its tracks.
        """
        playlist = Playlist.objects.create(name='Old Mix', created_by=self.user)
        PlaylistTrack.objects.create(playlist=playlist, track=self.track1, order=1)

        data = {
            'name': 'New Awesome Mix',
            'add_tracks': [
                {'spotify_id': 'track_002', 'order': 1}
            ]
        }

        serializer = PlaylistSerializer(playlist, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        updated_playlist = serializer.save()

        self.assertEqual(updated_playlist.name, 'New Awesome Mix')
        self.assertEqual(updated_playlist.tracks.count(), 1)

        remaining_track = updated_playlist.playlisttrack_set.first()
        self.assertEqual(remaining_track.track, self.track2)
        self.assertEqual(remaining_track.order, 1)


class PublicPlaylistApiTests(TestCase):
    """
    Test unauthenticated API requests for playlists.
    """
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required to view playlists."""
        res = self.client.get(PLAYLISTS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivatePlaylistApiTests(TestCase):
    """
    Test authenticated API requests for playlists.
    """
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='password123'
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_playlists_filtering(self):
        """
        Test retrieving playlists.
        Should return the user's playlists (public & private) AND other users' public playlists.
        Should NOT return other users' private playlists.
        """
        other_user = get_user_model().objects.create_user(
            email='other@example.com',
            password='password123'
        )

        Playlist.objects.create(name='My Private', created_by=self.user, is_public=False)
        Playlist.objects.create(name='My Public', created_by=self.user, is_public=True)

        Playlist.objects.create(name='Other Public', created_by=other_user, is_public=True)
        Playlist.objects.create(name='Other Private', created_by=other_user, is_public=False)

        res = self.client.get(PLAYLISTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 3)

        returned_names = [p['name'] for p in res.data['results']]
        self.assertIn('My Private', returned_names)
        self.assertIn('My Public', returned_names)
        self.assertIn('Other Public', returned_names)
        self.assertNotIn('Other Private', returned_names)

    def test_create_playlist_assigns_user(self):
        """
        Test that creating a playlist automatically assigns the authenticated user.
        """
        payload = {
            'name': 'Gym Motivation',
            'is_public': False
        }
        res = self.client.post(PLAYLISTS_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        playlist = Playlist.objects.get(id=res.data['id'])

        self.assertEqual(playlist.created_by, self.user)

    def test_cannot_access_other_users_private_playlist_detail(self):
        """
        Test that a user gets a 404 when trying to view another user's private playlist.
        """
        other_user = get_user_model().objects.create_user(
            email='other@example.com',
            password='password123'
        )
        private_playlist = Playlist.objects.create(
            name='Secret List',
            created_by=other_user,
            is_public=False
        )

        url = playlist_detail_url(private_playlist.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_tracks_by_artists(self):
        """
        Test filtering tracks by artists.
        """
        artist1 = Artist.objects.create(name='Artist 1', spotify_id='spid1')
        artist2 = Artist.objects.create(name='Artist 2', spotify_id='spid2')

        track1 = Track.objects.create(
            title='Track 1', spotify_id='sp1', duration_ms=120000
        )
        track1.artists.add(artist1)

        track2 = Track.objects.create(
            title='Track 2', spotify_id='sp2', duration_ms=120000
        )
        track2.artists.add(artist2)

        track3 = Track.objects.create(
            title='Track 3', spotify_id='sp3', duration_ms=120000
        )

        url = reverse('playlist:track-list')
        res = self.client.get(url, {'artists': f'{artist1.id}'})

        serializer1 = TrackSerializer(track1)
        serializer2 = TrackSerializer(track2)
        serializer3 = TrackSerializer(track3)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data['results'])
        self.assertNotIn(serializer2.data, res.data['results'])
        self.assertNotIn(serializer3.data, res.data['results'])

    def test_filter_tracks_by_genres(self):
        """
        Test filtering tracks by genres through artists.
        """
        genre1 = Genre.objects.create(name='Rock')
        genre2 = Genre.objects.create(name='Pop')

        artist1 = Artist.objects.create(name='Rock Band', spotify_id='spid1')
        artist1.genres.add(genre1)

        artist2 = Artist.objects.create(name='Pop Star', spotify_id='spid2')
        artist2.genres.add(genre2)

        track1 = Track.objects.create(
            title='Rock Song', spotify_id='sp4', duration_ms=180000
        )
        track1.artists.add(artist1)

        track2 = Track.objects.create(
            title='Pop Song', spotify_id='sp5', duration_ms=200000
        )
        track2.artists.add(artist2)

        url = reverse('playlist:track-list')
        res = self.client.get(url, {'genres': f'{genre1.id},{genre2.id}'})

        serializer1 = TrackSerializer(track1)
        serializer2 = TrackSerializer(track2)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(serializer1.data, res.data['results'])
        self.assertIn(serializer2.data, res.data['results'])

    def test_search_tracks_in_playlist_with_pagination(self):
        """
        Test searching tracks within a playlist returns paginated results.
        """
        playlist = Playlist.objects.create(created_by=self.user, name='My Mix')

        artist1 = Artist.objects.create(name='Metallica', spotify_id='m1')
        artist2 = Artist.objects.create(name='Eminem', spotify_id='e1')

        track1 = Track.objects.create(title='Nothing Else Matters', spotify_id='t1', duration_ms=100)
        track1.artists.add(artist1)

        track2 = Track.objects.create(title='Lose Yourself', spotify_id='t2', duration_ms=100)
        track2.artists.add(artist2)

        track3 = Track.objects.create(title='Stan', spotify_id='t3', duration_ms=100)
        track3.artists.add(artist2)

        PlaylistTrack.objects.create(playlist=playlist, track=track1, order=1)
        PlaylistTrack.objects.create(playlist=playlist, track=track2, order=2)
        PlaylistTrack.objects.create(playlist=playlist, track=track3, order=3)

        url = reverse('playlist:playlist-search-tracks', args=[playlist.id])
        res_title = self.client.get(url, {'q': 'nothing'})

        self.assertEqual(res_title.status_code, status.HTTP_200_OK)

        self.assertIn('count', res_title.data)
        self.assertIn('next', res_title.data)
        self.assertIn('previous', res_title.data)
        self.assertIn('results', res_title.data)

        self.assertEqual(res_title.data['count'], 1)
        self.assertEqual(len(res_title.data['results']), 1)
        self.assertEqual(res_title.data['results'][0]['title'], 'Nothing Else Matters')

        res_artist = self.client.get(url, {'q': 'emin'})

        self.assertEqual(res_artist.status_code, status.HTTP_200_OK)
        self.assertEqual(res_artist.data['count'], 2)
        self.assertEqual(len(res_artist.data['results']), 2)
