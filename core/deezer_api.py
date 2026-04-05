"""Helpers for Deezer API lookups used across scripts."""

import requests


def get_track_preview(track_id):
    """Return the Deezer preview URL for a track id, or None."""
    try:
        response = requests.get(f"https://api.deezer.com/track/{track_id}", timeout=10)
        response.raise_for_status()
        return response.json().get("preview")
    except Exception:
        return None