"""
URL Mappings for the Spotify API.
"""

from django.urls import path
from spotify import views

app_name = 'spotify'

urlpatterns = [
    path('get-auth-url/', views.AuthURLView.as_view(), name='get-auth-url'),
    path('callback/', views.SpotifyCallbackView.as_view(), name='spotify-callback'),
]
