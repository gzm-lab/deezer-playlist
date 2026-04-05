#!/usr/bin/env python3
"""Récupère le dernier titre ajouté dans la playlist "Coup de coeur" d'un utilisateur Deezer.

Usage:
  - Remplir un fichier `.env` contenant: application_id, secret_key, application_domain
  - Lancer `python -m tools.deezer_latest_liked` puis autoriser l'application dans le navigateur

Le script démarre un petit serveur HTTP local pour recevoir le code OAuth, échange
le code contre un access token, trouve la playlist nommée (par défaut "Coup de coeur")
et affiche le dernier titre.

Crédits: conçu pour usage personnel.
"""

import os
import threading
import webbrowser
import http.server
import socketserver
import urllib.parse as urlparse
import requests
import json
import time
from dotenv import load_dotenv
import argparse


load_dotenv()

APP_ID = os.getenv("application_id")
SECRET = os.getenv("secret_key")
APPLICATION_DOMAIN = os.getenv("application_domain")
DEFAULT_PLAYLIST_NAME = "Coup de coeur"
CACHE_FILE = ".deezer_token.json"


class OAuthHandler(http.server.BaseHTTPRequestHandler):
    server_version = "DeezerOAuth/0.1"

    def do_GET(self):
        parsed = urlparse.urlparse(self.path)
        qs = urlparse.parse_qs(parsed.query)
        if "code" in qs:
            code = qs["code"][0]
            self.server.code = code
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Autorisation reussie. Vous pouvez fermer cette fenetre.</h2></body></html>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing code parameter")

    def log_message(self, format, *args):
        return


def start_local_server(host, port, path):
    class _Server(socketserver.TCPServer):
        allow_reuse_address = True

    handler = OAuthHandler
    httpd = _Server((host, port), handler)
    httpd.code = None
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def build_auth_url(app_id, redirect_uri, perms=None):
    base = "https://connect.deezer.com/oauth/auth.php"
    params = {
        "app_id": app_id,
        "redirect_uri": redirect_uri,
    }
    if perms:
        params["perms"] = perms
    return base + "?" + urlparse.urlencode(params)


def exchange_code_for_token(app_id, secret, code):
    url = "https://connect.deezer.com/oauth/access_token.php"
    params = {
        "app_id": app_id,
        "secret": secret,
        "code": code,
        "output": "json",
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def load_cached_token(path=CACHE_FILE):
    try:
        with open(path, "r", encoding="utf-8") as f:
            token = json.load(f)
        if isinstance(token, dict) and "retrieved_at" not in token:
            try:
                token["retrieved_at"] = int(os.path.getmtime(path))
            except Exception:
                token["retrieved_at"] = int(time.time())
        return token
    except Exception:
        return None


def token_is_valid(token_obj):
    if not token_obj:
        return False
    access = token_obj.get("access_token")
    if not access:
        return False
    expires = token_obj.get("expires")
    retrieved = token_obj.get("retrieved_at")
    try:
        expires_int = int(expires) if expires is not None else 0
    except Exception:
        expires_int = 0
    if expires_int == 0:
        return True
    if not retrieved:
        return False
    elapsed = int(time.time()) - int(retrieved)
    return elapsed < (expires_int - 60)


def save_token(token_obj, path=CACHE_FILE):
    if isinstance(token_obj, dict) and "retrieved_at" not in token_obj:
        token_obj["retrieved_at"] = int(time.time())
    with open(path, "w", encoding="utf-8") as f:
        json.dump(token_obj, f)


def find_playlist_by_name(access_token, name):
    url = "https://api.deezer.com/user/me/playlists"
    params = {"access_token": access_token}
    while url:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        for pl in data.get("data", []):
            if pl.get("title", "").lower() == name.lower() or name.lower() in pl.get("title", "").lower():
                return pl
        url = data.get("next")
        params = None
    return None


def get_last_liked_track(access_token):
    url = "https://api.deezer.com/user/me/tracks"
    params = {"access_token": access_token, "limit": 1}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json().get("data", [])
    if data:
        return data[0]

    r2 = requests.get(url, params={"access_token": access_token, "limit": 1}, timeout=10)
    r2.raise_for_status()
    info = r2.json()
    total = info.get("total", 0)
    if total == 0:
        return None
    offset = max(0, total - 1)
    r3 = requests.get(url, params={"access_token": access_token, "index": offset, "limit": 1}, timeout=10)
    r3.raise_for_status()
    data2 = r3.json().get("data", [])
    if data2:
        return data2[0]
    return None


def get_last_track_in_playlist(access_token, playlist_id):
    tracks_url = f"https://api.deezer.com/playlist/{playlist_id}/tracks"
    r = requests.get(tracks_url, params={"access_token": access_token, "limit": 1}, timeout=10)
    r.raise_for_status()
    info = r.json()
    total = info.get("total", 0)
    if total == 0:
        return None
    offset = max(0, total - 1)
    r2 = requests.get(tracks_url, params={"access_token": access_token, "index": offset, "limit": 1}, timeout=10)
    r2.raise_for_status()
    data = r2.json().get("data", [])
    if not data:
        return None
    return data[0]


def main():
    parser = argparse.ArgumentParser(description="Récupère le dernier titre ajouté dans une playlist Deezer")
    parser.add_argument("--playlist", "-p", default=DEFAULT_PLAYLIST_NAME, help='Nom de la playlist (défaut: "Coup de coeur")')
    parser.add_argument("--no-open", action="store_true", help="Ne pas ouvrir automatiquement le navigateur")
    parser.add_argument("--force-auth", action="store_true", help="Forcer une nouvelle authentification OAuth même si un token est en cache")
    parser.add_argument("--save-token", action="store_true", help="Sauvegarder l access token dans .deezer_token.json (obsolète, le token est sauvegardé par défaut)")
    parser.add_argument("--no-save", action="store_true", help="Ne pas sauvegarder l'access token sur disque")
    args = parser.parse_args()

    if not APP_ID or not SECRET or not APPLICATION_DOMAIN:
        print("Erreur: veuillez renseigner application_id, secret_key et application_domain dans votre .env")
        return

    env_token = os.getenv("DEEZER_ACCESS_TOKEN")
    cached = load_cached_token()
    if env_token:
        access_token = env_token
    elif (not args.force_auth) and cached and token_is_valid(cached):
        access_token = cached.get("access_token")
        print("Utilisation du token mis en cache.")
    else:
        parsed = urlparse.urlparse(APPLICATION_DOMAIN)
        host = parsed.hostname or "localhost"
        port = parsed.port or 8080
        path = parsed.path or "/"

        httpd = start_local_server(host, port, path)
        redirect_uri = f"{parsed.scheme}://{host}:{port}{path}" if parsed.scheme else f"http://{host}:{port}{path}"

        # Request offline_access so Deezer can return a long-lived token (expires may be 0).
        perms = "basic_access,manage_library,delete_library,offline_access"
        auth_url = build_auth_url(APP_ID, redirect_uri, perms=perms)

        print("Ouvrir la page d autorisation Deezer...")
        if not args.no_open:
            try:
                webbrowser.open(auth_url)
            except Exception:
                print("Impossible d ouvrir le navigateur automatiquement. Ouvrez manuellement:")
                print(auth_url)
        else:
            print("Ouvrez manuellement dans votre navigateur :")
            print(auth_url)

        print("En attente du code d autorisation...")
        waited = 0
        while getattr(httpd, "code", None) is None and waited < 300:
            time.sleep(0.5)
            waited += 0.5

        code = getattr(httpd, "code", None)
        httpd.shutdown()
        if not code:
            print("Timeout: aucun code reçu. Vérifiez que votre `application_domain` est accessible et correct.")
            return

        token_json = exchange_code_for_token(APP_ID, SECRET, code)
        access_token = token_json.get("access_token")
        if not access_token:
            print("Erreur lors de la récupération de l access token:", token_json)
            return
        expires = token_json.get("expires")
        print(f"Token reçu (expires={expires})")
        if not args.no_save:
            try:
                save_token(token_json)
                print(f"Access token sauvegardé dans {CACHE_FILE}")
            except Exception as e:
                print("Impossible de sauvegarder le token:", e)

    print("Recherche des titres likés (favorites)...")
    last_track = None
    try:
        last_track = get_last_liked_track(access_token)
    except Exception:
        last_track = None

    if last_track:
        artist = last_track.get("artist", {}).get("name")
        title = last_track.get("title")
        link = last_track.get("link")
        track_id = last_track.get("id")
        print("\nDernier titre liké:")
        print("-", title, "—", artist)
        print("Link:", link)
        print("Track id:", track_id)
        return

    print(f"Recherche de la playlist '{args.playlist}'...")
    playlist = find_playlist_by_name(access_token, args.playlist)
    if not playlist:
        print("Playlist non trouvée. Vérifiez le nom ou vos permissions.")
        return

    print("Playlist trouvée:", playlist.get("title"), "id=", playlist.get("id"))
    last_track = get_last_track_in_playlist(access_token, playlist.get("id"))
    if not last_track:
        print("Aucun titre trouvé dans la playlist.")
        return

    artist = last_track.get("artist", {}).get("name")
    title = last_track.get("title")
    link = last_track.get("link")
    track_id = last_track.get("id")

    print("\nDernier titre ajouté:")
    print("-", title, "—", artist)
    print("Link:", link)
    print("Track id:", track_id)


if __name__ == "__main__":
    main()