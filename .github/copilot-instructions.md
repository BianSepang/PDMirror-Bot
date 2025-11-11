## PDMirror-bot — Copilot / AI-assistant instructions

Quick, actionable notes to help an AI assistant be immediately productive in this repo.

- Project type: a Telegram bot built on Pyrogram that orchestrates aria2 downloads and uploads to Pixeldrain.
- Start point: `python -m bot` (the package has `bot/__main__.py`).

Key files and components
- `bot/__init__.py` — loads `config.toml`, sets up `LOGGER`, creates `DOWNLOAD_DIR` and enforces required config fields (exit if any required field empty).
- `bot/bot_client.py` — main `BotClient` (subclass of `pyrogram.Client`). Handles plugin registration, TinyDB state (`db.json` table `bot_settings`), active download mappings, and recover_state (GetDifference replay logic).
- `bot/plugins/*.py` — plugin handlers. Example: `bot/plugins/download.py` shows pattern for commands `/download`, `/cancel`, `/status`, `/pd` (pixeldrain).
- `bot/utils/aioaria.py` — `AioAria` wrapper for aria2 JSON-RPC. Connects to `http://localhost:6800/jsonrpc` and will spawn `aria2c` with `--enable-rpc` if not available.
- `bot/utils/pixeldrain.py` — streaming upload with progress callback. Used by `/pd` command.
- `config.toml` / `sample_config.toml` — runtime configuration; `required` section must be filled.

Run & debug notes
- Install deps: `pip install -r requirements.txt`.
- Fill `config.toml` `required` fields (api_id, api_hash, bot_token, owner_id). The bot exits early if these are empty.
- Start the bot in foreground: `python -m bot` (logs to `bot.log` by default). Use `OWNER_ONLY` commands from the owner account to control the process: `/restart`, `/shutdown`, `/raw`, `/ping`.
- Aria2: the code expects an aria2 JSON-RPC at `http://localhost:6800/jsonrpc`. If not present, `AioAria.initialize()` will attempt to run `aria2c --enable-rpc=true --daemon=true --quiet` (so `aria2c` must be installed and on PATH for that fallback to work).
- State: `TinyDB('db.json').table('bot_settings')` stores a saved `state` (pts/qts/date) used by `recover_state()` to replay missed updates. Deleting that entry forces no recovery.

Plugin & coding conventions (concrete patterns)
- Plugins live under `bot/plugins` and register handlers using the `BotClient` decorator style. Example:
  - `@BotClient.on_message(AUTHORIZED_ONLY & filters.command(["download", "dl"]))`
  - Use `client.aioaria.client` for aria2 operations (`addUri`, `tellStatus`, `remove`, `tellActive`).
- Filters: see `bot/utils/filters.py` — `OWNER_ONLY` and `AUTHORIZED_ONLY` are `pyrogram.filters.create(...)` wrappers that read IDs from `client.config`.
- Uploads: use `upload_file_to_pixeldrain(file_path, file_name, api_key, message)` for progress-enabled uploads.

Important repo-specific quirks and gotchas (documented, not aspirational)
- Config key name mismatch: `sample_config.toml` uses `authorized_user` / `authorized_chat` (singular), but `bot/utils/filters.py` expects `authorized_users` / `authorized_chats` (plural, space-separated IDs). Prefer following the code: add `authorized_users` and `authorized_chats` keys with space-separated IDs in `config.toml`.
- `bot/__init__.py` will exit the process if any value under `required` is falsy — fill them before running.
- `AioAria.initialize()` uses `Aria2WebsocketClient.new` and then `changeGlobalOption(...)` to set many aria2 options (download dir set from `DOWNLOAD_DIR`). Editing aria2 behavior should be done in `bot/utils/aioaria.py`.

Examples to copy/paste
- Minimal `config.toml` (fill secrets):
  ```toml
  [required]
  api_id = "<YOUR_API_ID>"
  api_hash = "<YOUR_API_HASH>"
  bot_token = "<BOT_TOKEN>"
  owner_id = "<OWNER_USER_ID>"

  [general]
  download_dir = "downloads"
  pixeldrain_api_key = "<PIXELDRAIN_KEY>"

  [users]
  authorized_users = "12345678 23456789"
  authorized_chats = "-1001122334455"
  ```

What to change when adding features
- Put new command handlers in `bot/plugins/` and follow the `@BotClient.on_message(...)` pattern.
- Use `client.logger` for logs so they appear in `bot.log` and stdout.
- For long-running background loops, create tasks and store them in `client.status_messages` or a new mapping so owner commands can cancel/clean them.

Quick checklist for PR reviewers / assistants
- Ensure `config.toml` keys referenced in code exist and are used consistently.
- Keep changes to aria2 options in `bot/utils/aioaria.py` only; tests expect the download dir to be `DOWNLOAD_DIR`.
- Verify new dependencies are added to `requirements.txt`.

If anything above is unclear or you want more examples (e.g., adding a new plugin with a unit-style harness), tell me what area to expand and I will iterate.
