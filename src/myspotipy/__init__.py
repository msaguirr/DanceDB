"""Minimal Spotipy-like wrapper package (myspotipy).

This package provides a small, dependency-light wrapper around the
Spotify Web API for demonstration and local usage.
"""
from .client import Spotify
from .oauth import SpotifyOAuth
from .exceptions import SpotifyException

__all__ = ["Spotify", "SpotifyOAuth", "SpotifyException"]
__version__ = "0.1.0"
