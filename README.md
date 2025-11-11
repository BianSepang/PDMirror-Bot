# PDMirror-bot

A small Telegram bot (Pyrogram) that orchestrates aria2 downloads and uploads files to Pixeldrain.

Core idea
- The bot accepts commands from authorized Telegram users to add and manage downloads in aria2, shows status, and can upload completed files to Pixeldrain.

Quick start
1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Fill `config.toml` (see `sample_config.toml`) — the `required` section must be filled (api_id, api_hash, bot_token, owner_id), otherwise the bot exits on start.

Important note: the code expects `authorized_users` and `authorized_chats` (space-separated IDs) under `[users]` in `config.toml`. The sample file may use singular keys — prefer the plural keys used in `bot/utils/filters.py`.

3. Start the bot:

```bash
python -m bot
```

What it does (commands)
- /download <url> (or /dl) — add a download to aria2 and show a status message that updates.
- /cancel <gid> (or /c) — cancel and remove a download by aria2 GID.
- /status — create a live status message listing active downloads.
- /pd <file_path> — upload an existing file to Pixeldrain with progress updates.
- Owner-only commands: /restart, /shutdown, /raw, /ping.

Architecture & key files
- `bot/__init__.py` — config loading, logging setup, creates `DOWNLOAD_DIR` and validates required config.
- `bot/bot_client.py` — `BotClient` (Pyrogram Client subclass) that wires up plugins, TinyDB state (`db.json`), and aria2 wrapper initialization.
- `bot/plugins/` — plugin handlers; `download.py` is the main example showing how commands are implemented.
- `bot/utils/aioaria.py` — wrapper to connect to aria2 JSON-RPC or spawn `aria2c` if missing and set aria2 options.
- `bot/utils/pixeldrain.py` — streaming upload helper that edits a Telegram message with progress.

Integration notes / gotchas
- Aria2 integration: `AioAria` connects to `http://localhost:6800/jsonrpc`. If aria2 is not running, the bot will try to spawn `aria2c` via the PATH. Make sure `aria2c` is installed if you rely on that behavior.
- State recovery: `BotClient.recover_state()` stores Telegram state (pts/qts/date) in TinyDB to replay missed updates. Removing the `state` entry from `db.json` disables recovery.
- Logs: both stdout and `bot.log` are used; use `client.logger` inside plugins.
- Downloads folder: configured via `config.toml` `general.download_dir` (default `downloads`). `AioAria` sets aria2's `dir` option to this path.

Development notes
- Add plugins under `bot/plugins` using the decorator pattern used in existing files, e.g. `@BotClient.on_message(AUTHORIZED_ONLY & filters.command(["download", "dl"]))`.
- Use `client.aioaria.client` to call aria2 RPC methods like `addUri`, `tellStatus`, `remove`, `tellActive`.
- For long-running periodic updates create tasks and store references on the client (see `client.status_messages`) so they can be canceled.

License
- See `LICENSE`.
