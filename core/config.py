"""Settings read from the config file (core/varreg.py).

[app] base_url        address the QR codes point to, e.g. http://hazbat.wmg.local:8000
[app] session_secret  key used to sign the login cookie
[app] max_2fa_interval_hours  longest time, in whole hours, a user may set between second-factor checks
The database settings are read in core/db.py.
"""

from core.varreg import settings

settings.require("app", "base_url", "session_secret", "max_2fa_interval_hours")

BASE_URL = settings.get("app", "base_url")
SESSION_SECRET = settings.get("app", "session_secret")
try:
    MAX_2FA_INTERVAL_HOURS = int(settings.get("app", "max_2fa_interval_hours"))
except ValueError:
    raise RuntimeError("[app] max_2fa_interval_hours must be a whole number of hours")
