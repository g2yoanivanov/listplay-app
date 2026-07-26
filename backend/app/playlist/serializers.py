"""
Serializer for the Playlist API.
"""
from rest_framework import serializers
from core.models import (
    Genre,
    Artist,
    Track,
)


class GenreSerializer(serializers.ModelSerializer):
    """Serializer for the Genre object."""

    class Meta:
        model = Genre
        fields = ['id', 'name']
        read_only_fields = ['id']
        extra_kwargs = {
            'name': {
                'validators': []
            }
        }


class ArtistSerializer(serializers.ModelSerializer):
    """Serializer for the Artist object."""
    genres = GenreSerializer(many=True, required=False)

    class Meta:
        model = Artist
        fields = ['id', 'spotify_id', 'name', 'genres']
        read_only_fields = ['id']
        extra_kwargs = {
            'spotify_id': {'validators': []}
        }

    def _get_or_create_genres(self, genres, artist):
        """
        Handle getting or creating genres for the artists as needed.
        """
        for genre in genres:
            genre_obj, _ = Genre.objects.update_or_create(
                name=genre['name']
            )
            artist.genres.add(genre_obj)

    def create(self, validated_data):
        """Create a new artist."""
        genres = validated_data.pop('genres', [])
        artist = Artist.objects.create(**validated_data)

        self._get_or_create_genres(genres, artist)

        return artist

    def update(self, instance, validated_data):
        """Update an artist."""
        genres = validated_data.pop('genres', None)

        if genres is not None:
            instance.genres.clear()
            self._get_or_create_genres(genres, instance)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class TrackSerializer(serializers.ModelSerializer):
    """Serializer for the Track object."""
    artists = ArtistSerializer(many=True, required=False)

    class Meta:
        model = Track
        fields = [
            'id', 'spotify_id',
            'title', 'artists',
            'duration_ms', 'cover_url'
        ]
        read_only_fields = ['id']

    def _get_or_create_artists(self, artists, track):
        """
        Handle getting or creating artists for the tracks as needed.
        """
        for artist in artists:
            artist_obj, _ = Artist.objects.update_or_create(
                spotify_id=artist['spotify_id'],
                defaults={'name': artist.get('name', 'Unknown')}
            )
            track.artists.add(artist_obj)

    def create(self, validated_data):
        """
        Create a new track.
        """
        artists = validated_data.pop('artists', [])
        track = Track.objects.create(**validated_data)

        self._get_or_create_artists(artists, track)

        return track

    def update(self, instance, validated_data):
        """
        Update a track.
        """
        artists = validated_data.pop('artists', None)

        if artists is not None:
            instance.artists.clear()
            self._get_or_create_artists(artists, instance)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
