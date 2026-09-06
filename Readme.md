# Diamond's AI Assistant

Web app + Telegram bot, sharing one memory system (SQLite), with
conversation threads, a settings panel (rename assistant, clear
memory), and a voice mode using the browser's speech recognition.

## Files

- `assistant_core.py` — shared brain: database, memory, conversations, settings, Claude calls
- `app.py` — Flask web app (the one with the sidebar/voice UI)
- `bot.py` — Telegram bot (single continuous thread, no sidebar)
- `templates/index.html` — the web UI
- `static/manifest.json`, `static/sw.js`, `static/icons/` — PWA install support
- `requirements.txt`, `Procfile`, `.env.example` — deploy config

## Deploy on Railway

1. New Project → Deploy from GitHub repo → select this repo
2. Add environment variables:
   - `ANTHROPIC_API_KEY`
   - `FLASK_SECRET_KEY` (any random string)
   - `APP_PASSWORD` (optional)
3. Settings → Deploy → Start Command: `python app.py`
4. Open the live URL on your phone → Add to Home Screen

Optional: deploy `bot.py` as a second Railway service from the same
repo (Start Command: `python bot.py`, needs `ANTHROPIC_API_KEY` +
`TELEGRAM_BOT_TOKEN`).

## Note

Railway's free tier may reset local storage on redeploy — chat
history and settings could be lost on a redeploy unless a persistent
volume or Postgres is added later.