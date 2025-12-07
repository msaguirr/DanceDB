from dataclasses import dataclass
from typing import Optional


@dataclass
class Song:
    """Plain data object representing a song."""
    name: str
    artist: str
    bpm: Optional[float] = None
    play_frequency: Optional[int] = 0
    rating: Optional[int] = None

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("`name` must be a non-empty string")
        if not isinstance(self.artist, str) or not self.artist.strip():
            raise ValueError("`artist` must be a non-empty string")
        # bpm is optional: if provided, it must be a positive number.
        if self.bpm is not None:
            try:
                self.bpm = float(self.bpm)
            except Exception:
                raise ValueError("`bpm` must be a number")
            if self.bpm <= 0:
                raise ValueError("`bpm` must be a positive number")


def create_song(name: str, artist: str, bpm=None) -> Song:
    """Create and return a `Song` instance.

    Parameters
    - name: song title (required, non-empty string)
    - artist: artist name (required, non-empty string)
    - bpm: beats-per-minute (number, optional, positive if provided)

    Returns
    - Song: newly created Song object

    Raises
    - ValueError: if required fields are missing or invalid
    """
    return Song(name=name, artist=artist, bpm=bpm)


def create_from_spotify(track_obj, sp=None) -> Song:
    """Create a Song from a Spotify track object or simplified track dict.

    - `sp` may be an instance of `myspotipy.Spotify` (or compatible client). If
      omitted, this function will attempt to use the module-global Spotify client
      (see `myspotipy.client.get_global_spotify()`).
    - `track_obj` can be the raw track JSON returned by Spotify or the simplified
      dict returned by `Spotify.search_tracks` (which includes a `raw` key).

    This function will fetch the audio-features for BPM. It does not attempt to
    infer genres (genre will be set to "Unknown").
    """
    if sp is None:
        try:
            from myspotipy.client import get_global_spotify

            sp = get_global_spotify(create_if_missing=True)
        except Exception:
            sp = None

    # accept simplified dict produced by search_tracks
    if isinstance(track_obj, dict) and "raw" in track_obj:
        track = track_obj.get("raw", {})
    else:
        track = track_obj

    track_id = track.get("id")
    name = track.get("name")
    artist_objs = track.get("artists", []) or []
    primary_artist_name = artist_objs[0].get("name") if artist_objs else "Unknown"
    artist_ids = [a.get("id") for a in artist_objs if a.get("id")]

    # fetch tempo (BPM) from Copperknob (line dance database)
    bpm = None
    try:
        from copperknob_scraper import get_bpm_from_copperknob
        bpm = get_bpm_from_copperknob(name, primary_artist_name)
    except Exception:
        bpm = None

    # Per request: do not attempt to infer genre from artist data.
    # pass bpm through (may be None). Song will accept missing bpm as unknown.
    return create_song(name or "Unknown", primary_artist_name or "Unknown", bpm)
