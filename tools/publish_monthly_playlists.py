#!/usr/bin/env python3
"""Create generated monthly playlists in Deezer from monthly_playlists.json."""

import argparse
import json
import os
import sys
from pathlib import Path

import requests


CACHE_FILE = ".deezer_token.json"
API_BASE = "https://api.deezer.com"


def load_cached_token(path=CACHE_FILE):
    token_path = Path(path)
    if not token_path.exists():
        return None
    try:
        return json.loads(token_path.read_text())
    except Exception:
        return None


def get_access_token():
    env_token = os.getenv("DEEZER_ACCESS_TOKEN")
    if env_token:
        return env_token
    cached = load_cached_token()
    if cached and "access_token" in cached:
        return cached["access_token"]
    return None


def api_get(path, access_token, params=None):
    query = {"access_token": access_token}
    if params:
        query.update(params)
    response = requests.get(f"{API_BASE}{path}", params=query, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(payload["error"])
    return payload


def api_post(path, access_token, params=None):
    query = {"access_token": access_token}
    if params:
        query.update(params)
    response = requests.post(f"{API_BASE}{path}", params=query, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(payload["error"])
    return payload


def find_playlist_by_title(access_token, title):
    path = "/user/me/playlists"
    params = {"limit": 100}
    while path:
        payload = api_get(path, access_token, params=params)
        for playlist in payload.get("data", []):
            if playlist.get("title") == title:
                return playlist
        next_url = payload.get("next")
        path = next_url.replace(API_BASE, "") if next_url and next_url.startswith(API_BASE) else None
        params = None
    return None


def get_playlist_track_ids(access_token, playlist_id):
    path = f"/playlist/{playlist_id}/tracks"
    params = {"limit": 100}
    track_ids = []
    while path:
        payload = api_get(path, access_token, params=params)
        track_ids.extend(track["id"] for track in payload.get("data", []) if track.get("id"))
        next_url = payload.get("next")
        path = next_url.replace(API_BASE, "") if next_url and next_url.startswith(API_BASE) else None
        params = None
    return track_ids


def create_playlist(access_token, title, public):
    payload = api_post(
        "/user/me/playlists",
        access_token,
        params={"title": title, "public": "true" if public else "false"},
    )
    playlist_id = payload.get("id")
    if not playlist_id:
        raise RuntimeError(f"Unable to create playlist '{title}': {payload}")
    return playlist_id


def add_tracks_to_playlist(access_token, playlist_id, track_ids):
    if not track_ids:
        return {"success": True}
    songs = ",".join(str(track_id) for track_id in track_ids)
    return api_post(f"/playlist/{playlist_id}/tracks", access_token, params={"songs": songs})


def publish_playlist(access_token, month, playlist_payload, public):
    title = f"{month} - {playlist_payload['profile']}"
    existing = find_playlist_by_title(access_token, title)
    if existing:
        playlist_id = existing["id"]
        print(f"Reuse existing playlist: {title} (id={playlist_id})")
    else:
        playlist_id = create_playlist(access_token, title, public=public)
        print(f"Created playlist: {title} (id={playlist_id})")

    existing_track_ids = set(get_playlist_track_ids(access_token, playlist_id))
    desired_track_ids = [track["id"] for track in playlist_payload.get("tracks", []) if track.get("id")]
    missing_track_ids = [track_id for track_id in desired_track_ids if track_id not in existing_track_ids]

    if missing_track_ids:
        add_tracks_to_playlist(access_token, playlist_id, missing_track_ids)
        print(f"  Added {len(missing_track_ids)} tracks")
    else:
        print("  No tracks to add")

    return {"title": title, "playlist_id": playlist_id, "added": len(missing_track_ids)}


def main():
    parser = argparse.ArgumentParser(description="Publish generated monthly playlists to Deezer")
    parser.add_argument("--input", default="monthly_playlists.json", help="Path to monthly playlists JSON")
    parser.add_argument("--public", action="store_true", help="Create public Deezer playlists")
    args = parser.parse_args()

    access_token = get_access_token()
    if not access_token:
        print("No Deezer token found. Run python -m tools.deezer_latest_liked first.")
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Missing playlist file: {input_path}")
        sys.exit(1)

    payload = json.loads(input_path.read_text())
    month = payload.get("month")
    playlists = payload.get("playlists", [])
    if not month or not playlists:
        print("Invalid playlist payload: month or playlists missing")
        sys.exit(1)

    print(f"Publishing {len(playlists)} playlists for {month}...")
    published = []
    for playlist_payload in playlists:
        published.append(publish_playlist(access_token, month, playlist_payload, public=args.public))

    print("\nDone.")
    for item in published:
        print(f"- {item['title']} -> id={item['playlist_id']} added={item['added']}")


if __name__ == "__main__":
    main()