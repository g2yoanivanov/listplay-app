"""
Serializer for the Playlist API.
"""
from rest_framework import serializers
from core.models import (
    Genre,
    Artist,
    Track,
    Playlist,
    PlaylistTrack
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
        genres_data = validated_data.pop('genres', [])
        artist = Artist.objects.create(**validated_data)

        self._get_or_create_genres(genres_data, artist)

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
        artists_data = validated_data.pop('artists', [])
        track = Track.objects.create(**validated_data)

        self._get_or_create_artists(artists_data, track)

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


class PlaylistTrackSerializer(serializers.ModelSerializer):
    """
    Serializer for the intermediate model to include the 'order'.
    """
    tracks = TrackSerializer(read_only=True)

    add_tracks = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = PlaylistTrack
        fields = ['track', 'order', 'added_at']


class PlaylistSerializer(serializers.ModelSerializer):
    tracks = PlaylistTrackSerializer(
        source='playlisttrack_set',
        many=True,
        read_only=True
    )

    add_tracks = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Playlist
        fields = [
            'id', 'name', 'description',
            'cover_img', 'is_public',
            'tracks', 'created_at',
            'add_tracks'
        ]
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        tracks_data = validated_data.pop('add_tracks', [])
        playlist = Playlist.objects.create(**validated_data)

        for track_obj in tracks_data:
            spotify_id = track_obj.get('spotify_id')
            order = track_obj.get('order')

            track = Track.objects.get(spotify_id=spotify_id)

            PlaylistTrack.objects.get_or_create(
                playlist=playlist,
                track=track,
                defaults={'order': order}
            )

        return playlist

    def update(self, instance, validated_data):
        tracks_data = validated_data.pop('add_tracks', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if tracks_data is not None:
            instance.playlisttrack_set.all().delete()

            for track_dict in tracks_data:
                spotify_id = track_dict.get('spotify_id')
                order = track_dict.get('order')

                try:
                    track = Track.objects.get(spotify_id=spotify_id)
                    PlaylistTrack.objects.get_or_create(
                        playlist=instance,
                        track=track,
                        defaults={'order': order}
                    )
                except Track.DoesNotExist:
                    continue

        return instance
