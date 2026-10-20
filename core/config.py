"""Settings read from environment variables (or a .env file in the repo folder).

BASE_URL        address the QR codes point to, e.g. http://hazbat.wmg.local:8000
SESSION_SECRET  key used to sign the login cookie
DATABASE_URL    read in core/db.py
"""

import os

from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-secret-change-this-later")
