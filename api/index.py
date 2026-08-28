"""Vercel serverless entrypoint for the Flask application.

Vercel's Python runtime looks for a Flask instance named ``app`` in the
api/ directory (or an explicitly configured entrypoint). Create the app
from the factory in ``app/__init__.py`` and expose it as ``app``.

Vercel serverless functions have no persistent filesystem, so the database
is initialized here on every cold start. ``seed.run`` is idempotent (every
seed step skips rows that already exist), so repeated cold starts are safe.
"""
from app import create_app
from app.extensions import db

app = create_app()

with app.app_context():
    db.create_all()
    from app.seed import run as seed_run

    seed_run()