"""
Firebase Firestore client — replaces the SQLite/SQLAlchemy database layer.

Initialization priority:
  1. FIREBASE_SERVICE_ACCOUNT env var  → JSON string of the service-account key
     (set this in Vercel dashboard for production)
  2. GOOGLE_APPLICATION_CREDENTIALS env var → path to a local key file
  3. Falls back to "serviceAccountKey.json" in the project root
     (rename your downloaded Firebase key to this for local dev)

Usage in routers:
    from firebase_db import get_db
    db = get_db()
    db.collection("brand_configs").stream()
"""

from __future__ import annotations

import json
import os

import firebase_admin
from firebase_admin import credentials, firestore


def get_db() -> firestore.Client:
    """Return an initialised Firestore client (safe to call multiple times)."""
    if not firebase_admin._apps:
        sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT")
        if sa_json:
            # Production: key is stored as a JSON string in the env var
            cred = credentials.Certificate(json.loads(sa_json))
        else:
            # Local dev: point to a key file
            key_path = os.getenv(
                "GOOGLE_APPLICATION_CREDENTIALS",
                os.path.join(os.path.dirname(__file__), "..", "serviceAccountKey.json"),
            )
            cred = credentials.Certificate(os.path.abspath(key_path))
        firebase_admin.initialize_app(cred)
    return firestore.client()
