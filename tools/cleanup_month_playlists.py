#!/usr/bin/env python3
"""Delete obsolete Deezer playlists for a month while keeping the current generated set."""

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


def api_delete(path, access_token, params=None):
    query = {"access_token": access_token}
    if params:
        query.update(params)
    response = requests.delete(f"{API_BASE}{path}", params=query, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(payload["error"])
    return payload


def list_user_playlists(access_token):
    path = "/user/me/playlists"
    params = {"limit": 100}
    playlists = []
    while path:
        payload = api_get(path, access_token, params=params)
        playlists.extend(payload.get("data", []))
        next_url = payload.get("next")
        path = next_url.replace(API_BASE, "") if next_url and next_url.startswith(API_BASE) else None
        params = None
    return playlists


def delete_playlist(access_token, playlist_id):
    return api_delete(f"/playlist/{playlist_id}", access_token)


def main():
    parser = argparse.ArgumentParser(description="Delete obsolete Deezer playlists for a month")
    parser.add_argument("--input", default="monthly_playlists.json", help="Path to the current monthly playlists JSON")
    parser.add_argument("--prefix", default=None, help="Optional title prefix to restrict deletion")
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
    current_titles = {f"{month} - {playlist['profile']}" for playlist in payload.get("playlists", [])}
    if not month:
        print("Invalid playlist payload: month missing")
        sys.exit(1)

    prefix = args.prefix or f"{month} - "
    user_playlists = list_user_playlists(access_token)
    obsolete_playlists = [
        playlist
        for playlist in user_playlists
        if isinstance(playlist.get("title"), str)
        and playlist["title"].startswith(prefix)
        and playlist["title"] not in current_titles
    ]

    print(f"Obsolete playlists to delete: {len(obsolete_playlists)}")
    for playlist in obsolete_playlists:
        delete_playlist(access_token, playlist["id"])
        print(f"Deleted: {playlist['title']} (id={playlist['id']})")


if __name__ == "__main__":
    main()