import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration pour Uvicorn
host = "0.0.0.0"
port = int(os.getenv("PORT", 5000))
reload = os.getenv("DEBUG", "False").lower() == "true"
workers = int(os.getenv("WORKERS", 1))
log_level = os.getenv("LOG_LEVEL", "info")

# Paramètres SSL (si nécessaire)
# ssl_keyfile = os.getenv("SSL_KEYFILE", None)
# ssl_certfile = os.getenv("SSL_CERTFILE", None)
