"""Vercel serverless entrypoint for the Flask application.

Vercel's Python runtime looks for a Flask instance named ``app`` in the
api/ directory (or an explicitly configured entrypoint). Create the app
from the factory in ``app/__init__.py`` and expose it as ``app``.
"""
from app import create_app

app = create_app()