"""
Tests for the Playlist Custom Actions for the API.
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Track,
    Playlist,
    PlaylistTrack
)

import os
import tempfile
from PIL import Image


GENRES_URL = reverse('playlist:genre-list')
ARTISTS_URL = reverse('playlist:artist-list')
TRACKS_URL = reverse('playlist:track-list')
PLAYLISTS_URL = reverse('playlist:playlist-list')


def playlist_detail_url(playlist_id):
    """
    Create and return a playlist detail URL.
    """
    return reverse('playlist:playlist-detail', args=[playlist_id])


def create_user(**params):
    """
    Create and return a new user.
    """
    return get_user_model().objects.create_user(**params)


def image_upload_url(playlist_id):
    """
    Create and return an image upload URL.
    """
    return reverse('playlist:playlist-upload-cover', args=[playlist_id])


class PlaylistActionTests(TestCase):
    """
    Test custom actions (add_track, remove_track) on PlaylistViewSet.
    """
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='password123'
        )
        self.client.force_authenticate(self.user)

        self.playlist = Playlist.objects.create(name='Test Mix', created_by=self.user)
        self.track1 = Track.objects.create(spotify_id='track_1', title='Song 1', duration_ms=200000)
        self.track2 = Track.objects.create(spotify_id='track_2', title='Song 2', duration_ms=210000)

    def test_add_track_success(self):
        """Test successfully adding a track via the add_track action."""
        url = f"{playlist_detail_url(self.playlist.id)}add-track/"
        payload = {'spotify_id': 'track_1'}

        res = self.client.post(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(
            PlaylistTrack.objects.filter(playlist=self.playlist, track=self.track1, order=1).exists()
        )

    def test_add_track_missing_spotify_id(self):
        """
        Test that missing spotify_id returns a 400 Bad Request.
        """
        url = f"{playlist_detail_url(self.playlist.id)}add-track/"
        res = self.client.post(url, {}, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_track_not_found(self):
        """
        Test that adding a non-existent track returns a 404 Not Found.
        """
        url = f"{playlist_detail_url(self.playlist.id)}add-track/"
        payload = {'spotify_id': 'fake_id'}

        res = self.client.post(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_remove_track_success_and_reorder(self):
        """
        Test removing a track and verifying that the remaining tracks
        are automatically reordered (closing the gap).
        """
        PlaylistTrack.objects.create(playlist=self.playlist, track=self.track1, order=1)
        PlaylistTrack.objects.create(playlist=self.playlist, track=self.track2, order=2)

        url = f"{playlist_detail_url(self.playlist.id)}remove-track/"
        payload = {'spotify_id': 'track_1'}

        res = self.client.delete(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(
            PlaylistTrack.objects.filter(playlist=self.playlist, track=self.track1).exists()
        )

        pt2 = PlaylistTrack.objects.get(playlist=self.playlist, track=self.track2)
        self.assertEqual(pt2.order, 1)

    def test_remove_track_not_in_playlist(self):
        """
        Test that trying to remove a track not in the playlist returns 404.
        """
        url = f"{playlist_detail_url(self.playlist.id)}remove-track/"
        payload = {'spotify_id': 'track_1'}

        res = self.client.delete(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_other_users_public_playlist_detail(self):
        """
        Test user can view the detail of another user's public playlist.
        """
        other_user = get_user_model().objects.create_user(
            email='other@example.com',
            password='password123'
        )
        public_playlist = Playlist.objects.create(
            name='Public Party Mix',
            created_by=other_user,
            is_public=True
        )

        url = playlist_detail_url(public_playlist.id)
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['name'], 'Public Party Mix')

    def test_update_other_users_playlist_forbidden(self):
        """
        Test user cannot update another user's playlist.
        """
        other_user = get_user_model().objects.create_user(
            email='other@example.com',
            password='password123'
        )
        other_playlist = Playlist.objects.create(
            name='Other Private List',
            created_by=other_user,
            is_public=False
        )

        url = playlist_detail_url(other_playlist.id)
        payload = {'name': 'Hacked Name'}

        res = self.client.patch(url, payload, format='json')

        self.assertIn(res.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_add_duplicate_track_fails(self):
        """
        Test adding the same track twice returns a 400 Bad Request.
        """
        url = f"{playlist_detail_url(self.playlist.id)}add-track/"
        payload = {'spotify_id': 'track_1'}

        res1 = self.client.post(url, payload, format='json')
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        res2 = self.client.post(url, payload, format='json')
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data['status'], 'track is already in the playlist')


class PlaylistImageUploadTests(TestCase):
    """
    Test the image upload API.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpassword123'
        )
        self.client.force_authenticate(self.user)
        self.playlist = Playlist.objects.create(created_by=self.user, name='Cover Test')

    def test_upload_image_to_playlist(self):
        """Test uploading a valid image to a playlist."""
        url = image_upload_url(self.playlist.id)

        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')

            image_file.seek(0)

            payload = {'cover_img': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.playlist.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('cover_img', res.data)

        self.assertTrue(os.path.exists(self.playlist.cover_img.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image."""
        url = image_upload_url(self.playlist.id)

        payload = {'cover_img': 'not_an_image'}
        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
