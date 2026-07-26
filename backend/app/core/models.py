"""
Database models for the application.
"""
import uuid

from django.conf import settings

from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)


class UserManager(BaseUserManager):
    """
    Manager for users.
    """

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a new user.
        """
        if not email:
            raise ValueError('Users must have an email address')
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a new superuser.
        """
        user = self.create_user(email, password, **extra_fields)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)

        return user


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model that supports using email instead of username.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']


class Genre(models.Model):
    """
    Genre model
    """
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Artist(models.Model):
    """
    Artist model (cache of Spotify artist)
    """
    spotify_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    genres = models.ManyToManyField(Genre, related_name='artists', blank=True)

    def __str__(self):
        return self.name


class Track(models.Model):
    """
    Track model (cache of Spotify track)
    """
    spotify_id = models.CharField(max_length=255, unique=True)
    title = models.CharField(max_length=255)
    artists = models.ManyToManyField(Artist, related_name='tracks')
    cover_url = models.URLField(max_length=500, blank=True, null=True)
    duration_ms = models.IntegerField(help_text="Duration in milliseconds")

    def __str__(self):
        first_artist = self.artists.first()
        artist_name = first_artist.name if first_artist else "Unknown Artist"
        return f'{artist_name} // {self.title}'


class Playlist(models.Model):
    """
    Playlist model
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    cover_img = models.ImageField(upload_to='playlist_covers/', blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='playlists'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_public = models.BooleanField(default=True)
    tracks = models.ManyToManyField(Track, through='PlaylistTrack', related_name='playlists', blank=True)

    def __str__(self):
        return self.name


class PlaylistTrack(models.Model):
    """
    Intermediate model for the many-to-many relationship between Playlist and Track.
    """
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(help_text="Order of the track in the playlist")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        unique_together = [
            ('playlist', 'track'),
            ('order', 'playlist')
        ]

    def __str__(self):
        return f'{self.playlist.name} - {self.track.title}'
