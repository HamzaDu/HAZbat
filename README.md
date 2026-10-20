BMAC by HAZbat

Working on the standardisation and capture of battery data 
during the manufacturing and subsequent testing stages.

## Run it

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Settings come from environment variables or a `.env` file: `DATABASE_URL`, `BASE_URL`, `SESSION_SECRET`
(see `core/config.py`). In GitHub Codespaces these are set up for you; see `.devcontainer/README.md`.

## Code layout

`main.py` only builds the app. Pages and endpoints are in `routers/`, the logic behind them in `services/`,
and shared basics (settings, database, templates, login checks) in `core/`.
See [CONTRIBUTING.md](CONTRIBUTING.md) for where new code goes and how to run the tests.
