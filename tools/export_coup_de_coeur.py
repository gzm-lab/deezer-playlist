#!/usr/bin/env python3
"""Exporte tous les titres de la playlist "Coups de coeur" (favoris) dans all_songs.json.

Sortie JSON: liste d'objets {id, title, artists, isrc}
"""

import os
import json
import time
import argparse
from pathlib import Path
import requests
from dotenv import load_dotenv


load_dotenv()

CACHE_FILE = ".deezer_token.json"
DEFAULT_PLAYLIST_NAME = "Coups de coeur"


def load_cached_token(path=CACHE_FILE):
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def get_access_token():
    env = os.getenv("DEEZER_ACCESS_TOKEN")
    if env:
        return env
    cached = load_cached_token()
    if cached and "access_token" in cached:
        return cached["access_token"]
    return None


def api_get(url, access_token, params=None):
    p = {"access_token": access_token}
    if params:
        p.update(params)
    r = requests.get(url, params=p, timeout=15)
    r.raise_for_status()
    return r.json()


def get_all_liked_tracks(access_token, max_tracks=None):
    url = "https://api.deezer.com/user/me/tracks"
    params = {"limit": 100}
    tracks = []
    while url:
        data = api_get(url, access_token, params=params)
        tracks.extend(data.get("data", []))
        if max_tracks and len(tracks) >= max_tracks:
            return tracks[:max_tracks]
        url = data.get("next")
        params = None
    return tracks


def find_playlist_by_name(access_token, name):
    url = "https://api.deezer.com/user/me/playlists"
    params = {"limit": 100}
    while url:
        data = api_get(url, access_token, params=params)
        for pl in data.get("data", []):
            title = pl.get("title", "")
            if title.lower() == name.lower():
                return pl
        url = data.get("next")
        params = None
    return None


def get_playlist_tracks(access_token, playlist_id):
    url = f"https://api.deezer.com/playlist/{playlist_id}/tracks"
    params = {"limit": 100}
    tracks = []
    while url:
        data = api_get(url, access_token, params=params)
        tracks.extend(data.get("data", []))
        url = data.get("next")
        params = None
    return tracks


def fetch_track_detail(access_token, track_id):
    url = f"https://api.deezer.com/track/{track_id}"
    return api_get(url, access_token)


def safe_fetch_track_detail(access_token, track_id, retries=2):
    for _ in range(retries):
        try:
            return fetch_track_detail(access_token, track_id)
        except Exception:
            time.sleep(0.5)
    return None


def extract_artists(track):
    artists = []
    contributors = track.get("contributors")
    if isinstance(contributors, list) and contributors:
        for c in contributors:
            name = c.get("name")
            if name and name not in artists:
                artists.append(name)
    artist = track.get("artist")
    if isinstance(artist, dict):
        name = artist.get("name")
        if name and name not in artists:
            artists.append(name)
    return artists


def extract_genres(track):
    genres = []
    album = track.get("album")
    if isinstance(album, dict):
        genres_data = (album.get("genres") or {}).get("data")
        if isinstance(genres_data, list):
            for g in genres_data:
                name = g.get("name")
                if name and name not in genres:
                    genres.append(name)
    return genres


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--playlist", "-p", default=DEFAULT_PLAYLIST_NAME, help="Nom de la playlist (par défaut: Coups de coeur)")
    parser.add_argument("--output", "-o", default="all_songs.json", help="Fichier JSON de sortie")
    parser.add_argument("--max", type=int, default=None, help="Nombre max de titres à récupérer (debug)")
    parser.add_argument("--no-liked", action="store_true", help="Ne pas utiliser /user/me/tracks et forcer recherche playlist")
    args = parser.parse_args()

    token = get_access_token()
    if not token:
        print("Aucun access token trouvé. Lancez l'auth Deezer ou définissez DEEZER_ACCESS_TOKEN.")
        return

    tracks = []
    if not args.no_liked:
        tracks = get_all_liked_tracks(token, max_tracks=args.max)
        if tracks:
            print(f"Titres likés récupérés: {len(tracks)}")

    if not tracks:
        print(f"Recherche de la playlist '{args.playlist}'...")
        playlist = find_playlist_by_name(token, args.playlist)
        if not playlist:
            print("Playlist non trouvée.")
            return
        tracks = get_playlist_tracks(token, playlist.get("id"))
        if args.max:
            tracks = tracks[: args.max]
        print(f"Tracks récupérés depuis playlist: {len(tracks)}")

    output_path = Path(args.output)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    output = []
    for idx, tr in enumerate(tracks, start=1):
        track_id = tr.get("id")
        if not track_id:
            continue
        detail = tr
        if not tr.get("isrc") or not tr.get("contributors"):
            fetched = safe_fetch_track_detail(token, track_id)
            if fetched:
                detail = fetched

        output.append(
            {
                "id": track_id,
                "title": detail.get("title"),
                "artists": extract_artists(detail),
                "isrc": detail.get("isrc"),
                "duration": detail.get("duration"),
                "genres": extract_genres(detail),
            }
        )
        if idx % 100 == 0:
            tmp_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))
            print(f"Progress: {idx}/{len(tracks)}")
        time.sleep(0.03)

    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    if tmp_path.exists():
        tmp_path.unlink()
    print(f"Sauvegardé {len(output)} titres dans {args.output}")


if __name__ == "__main__":
    main()