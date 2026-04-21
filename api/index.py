"""
Vercel serverless entry point.
Adds the backend/ directory to sys.path so all relative imports work,
then re-exports the FastAPI `app` object which Vercel's Python runtime picks up.
"""
import sys
import os

# Make backend/ importable by absolute path so Vercel can find it
_BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, os.path.abspath(_BACKEND))

from main import app  # noqa: F401  – re-exported for Vercel
