import logging
import os
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Génère une clé aléatoire de 24 octets
secret_key = os.urandom(24).hex()
logger.debug(f"Secret key générée : {secret_key}")
print(f"Utilisez cette clé dans .env ou app.py : {secret_key}")