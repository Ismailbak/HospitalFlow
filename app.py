"""Point d'entrée : python app.py  →  http://127.0.0.1:8050"""
import os

from dashboard import create_app

app = create_app()
server = app.server  # pour un déploiement WSGI (gunicorn app:server)

if __name__ == "__main__":
    app.run(debug=os.environ.get("HDJ_DEBUG") == "1", port=int(os.environ.get("PORT", 8050)))
