#!/bin/bash
set -e
# Création des tables + seeds
python -c "
from app import create_app, db
from app.core.seeds import init_db
app = create_app()
with app.app_context():
    db.create_all()
    init_db()
"
gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 4 --timeout 120 run:app