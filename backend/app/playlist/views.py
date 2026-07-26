"""
Views for playlist-related operations.
"""
from rest_framework import (
    viewsets
)

from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from core.models import (
    Genre,
    Artist,
    Track,
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
