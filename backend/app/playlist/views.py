"""
Views for playlist-related operations.
"""
from django.db import transaction
from django.db.models import Q, F

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import (
    viewsets,
    status
)

from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from core.models import (
    Genre,
    Artist,
    Track,
    Playlist,
    PlaylistTrack
)

from playlist import serializers


class BasePlaylistAttrViewSet(viewsets.ModelViewSet):
    """
    Base viewset for playlist attributes
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


class GenreViewSet(BasePlaylistAttrViewSet):
    """
    Manage genres in the database.
    """
    serializer_class = serializers.GenreSerializer
    queryset = Genre.objects.all()


class ArtistViewSet(BasePlaylistAttrViewSet):
    """
    Manage artists in the database.
    """
    serializer_class = serializers.ArtistSerializer
    queryset = Artist.objects.all()


class TrackViewSet(BasePlaylistAttrViewSet):
    """
    Manage tracks in the database.
    """
    serializer_class = serializers.TrackSerializer
    queryset = Track.objects.all()


class PlaylistViewSet(BasePlaylistAttrViewSet):
    """
    Manage tracks in the database.
    """
    serializer_class = serializers.PlaylistSerializer
    queryset = Playlist.objects.all()

    def get_serializer_class(self):
        """
        Return the serializer class for the request
        """
        if self.action == 'upload_cover':
            return serializers.PlaylistImageSerializer

        return self.serializer_class

    def get_queryset(self):
        """
        Filter the queryset to return only public playlists or
        the playlists for the authenticated user
        """
        user = self.request.user

        return self.queryset.filter(
            Q(created_by=user) | Q(is_public=True)
        ).distinct().order_by('-created_at')

    def perform_create(self, serializer):
        """
        Save the new playlist and automatically assign the
        current user as the creator
        """
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['POST'], url_path='add-track')
    def add_track(self, request, pk=None):
        """
        Add a single track to the playlist.
        """
        playlist = self.get_object()
        spotify_id = request.data.get('spotify_id')

        if not spotify_id:
            return Response(
                {'error': 'spotify_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            track = Track.objects.get(spotify_id=spotify_id)
        except Track.DoesNotExist:
            return Response(
                {'error': 'track not found in the database'},
                status=status.HTTP_404_NOT_FOUND
            )

        last_track = playlist.playlisttrack_set.order_by('-order').first()
        next_order = (last_track.order + 1) if last_track else 1

        playlist_track, created = PlaylistTrack.objects.get_or_create(
            playlist=playlist,
            track=track,
            defaults={'order': next_order}
        )

        if not created:
            return Response(
                {'error': 'track is alredy in the playlist'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({'status': 'Track added'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['DELETE'], url_path='remove-track')
    def remove_track(self, request, pk=None):
        """
        Remove a singel track in the playlist
        and reorder the remaining tracks to prevent gaps
        """
        playlist = self.get_object()
        spotify_id = request.data.get('spotify_id')

        if not spotify_id:
            return Response(
                {'error': 'spotify_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            playlist_track = PlaylistTrack.objects.get(
                playlist=playlist,
                track__spotify_id=spotify_id
            )

            removed_order = playlist_track.order
            playlist_track.delete()

            with transaction.atomic():
                PlaylistTrack.objects.filter(
                    playlist=playlist,
                    order__gt=removed_order
                ).update(order=F('order') - 1)

            return Response(
                {'status': 'track removed successfully'},
                status=status.HTTP_204_NO_CONTENT
            )

        except PlaylistTrack.DoesNotExist:
            return Response(
                {'error': 'track is not in this playlist'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['POST'], url_path='upload-cover')
    def upload_cover(self, request, pk=None):
        """
        Upload a cover to a playlist
        """
        playlist = self.get_object()
        serializer = self.get_serializer(playlist, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
