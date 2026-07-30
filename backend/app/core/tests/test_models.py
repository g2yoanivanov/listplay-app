"""
Tests for models.
"""
from django.db.utils import IntegrityError
from django.test import TestCase
from django.contrib.auth import get_user_model

from core import models

from django.utils import timezone
from datetime import timedelta


class UserModelTests(TestCase):
    """
    Test User model
    """

    def test_create_user_with_email_successful(self):
        """
        Test creating a user with email successful
        """
        email = "test@example.com"
        password = 'testpass123'
        user = get_user_model().objects.create_user(
            email=email,
            password=password
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normilized(self):
        """
        Test email is normalized for new users
        """
        sample_emails = [
            ["test1@EXAMPLE.com", "test1@example.com"],
            ["Test2@Example.com", "Test2@example.com"],
            ["TEST3@EXAMPLE.COM", "TEST3@example.com"],
            ["test4@example.COM", "test4@example.com"]
        ]

        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(email, "pass123")

            self.assertEqual(user.email, expected)

    def test_new_user_without_email_raises_error(self):
        """
        Test creating a user without an email raises a ValueError
        """
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user('', 'pass123')

    def test_create_superuser(self):
        """
        Test creating a superuser
        """
        user = get_user_model().objects.create_superuser(
            'test@example.com',
            'pass123'
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)


class MusicModelTests(TestCase):
    """
    Test music models
    """

    def setUp(self):
        """
        Set up initial data for the tests.
        """
        self.user = models.User.objects.create_user(
            email='musiclover@example.com',
            password='testpassword123'
        )

    def test_create_genre(self):
        """
        Test creating a genre is successful
        """
        genre = models.Genre.objects.create(
            name='Action'
        )

        self.assertEqual(str(genre), genre.name)

    def test_create_artist(self):
        """
        Test creating an artist is successful
        """
        artist = models.Artist.objects.create(
            spotify_id='4dpJCX1x00000000000000',
            name='Rick Astley'
        )

        self.assertEqual(str(artist), 'Rick Astley')

    def test_create_track(self):
        """
        Test creating a track is successful
        """
        artist = models.Artist.objects.create(
            spotify_id='4dpJCX1x00000000000000',
            name='Rick Astley'
        )

        track = models.Track.objects.create(
            spotify_id='4cOdK2wGLETKBW3PvgPWqT',
            title='Never Gonna Give You Up',
            duration_ms=213573
        )

        track.artists.add(artist)

        self.assertEqual(str(track), 'Rick Astley // Never Gonna Give You Up')
        self.assertEqual(track.artists.count(), 1)

    def test_create_playlist(self):
        """
        Test creating a playlist, UUID generation, and string representation.
        """
        playlist = models.Playlist.objects.create(
            name='My Workout Vibes',
            description='High energy tracks',
            created_by=self.user
        )

        self.assertIsNotNone(playlist.id)
        self.assertEqual(str(playlist), 'My Workout Vibes')

        self.assertEqual(self.user.playlists.count(), 1)

    def test_playlist_track_ordering(self):
        """
        Test that tracks in a playlist are returned in the correct order.
        """
        playlist = models.Playlist.objects.create(name='Chill', created_by=self.user)

        track1 = models.Track.objects.create(
            spotify_id='id_1', title='Song A', duration_ms=1000
        )
        track2 = models.Track.objects.create(
            spotify_id='id_2', title='Song B', duration_ms=2000
        )

        models.PlaylistTrack.objects.create(playlist=playlist, track=track2, order=2)
        models.PlaylistTrack.objects.create(playlist=playlist, track=track1, order=1)

        tracks = playlist.tracks.all().order_by('playlisttrack__order')

        self.assertEqual(tracks[0], track1)
        self.assertEqual(tracks[1], track2)

    def test_playlist_track_str(self):
        """
        Test the string representation of the intermediate model.
        """
        playlist = models.Playlist.objects.create(name='Top 50', created_by=self.user)
        track = models.Track.objects.create(
            spotify_id='id_3', title='Blinding Lights', duration_ms=200020
        )
        pt = models.PlaylistTrack.objects.create(playlist=playlist, track=track, order=1)

        self.assertEqual(str(pt), 'Top 50 - Blinding Lights')

    def test_add_same_track_twice_raises_error(self):
        """Test that adding the same track to the same playlist twice raises an IntegrityError."""
        playlist = models.Playlist.objects.create(name='Loop Playlist', created_by=self.user)
        track = models.Track.objects.create(
            spotify_id='trk_test',
            title='One More Time',
            duration_ms=320000
        )

        models.PlaylistTrack.objects.create(playlist=playlist, track=track, order=1)

        with self.assertRaises(IntegrityError):
            models.PlaylistTrack.objects.create(playlist=playlist, track=track, order=2)


class SpotifyTokenModelTests(TestCase):
    """
    Test SpotifyToken Model
    """

    def test_create_spotify_token(self):
        """
        Test creating tokens is successful.
        """
        user = get_user_model().objects.create_user('spotifyuser@example.com', 'testpass123')
        expires = timezone.now() + timedelta(hours=1)

        token = models.SpotifyToken.objects.create(
            user=user,
            access_token='mock_access_token',
            refresh_token='mock_refresh_token',
            expires_in=expires,
            token_type='Bearer'
        )

        self.assertEqual(token.user, user)
        self.assertEqual(token.access_token, 'mock_access_token')
        self.assertEqual(str(token), f"Spotify Token for {user.email}")
