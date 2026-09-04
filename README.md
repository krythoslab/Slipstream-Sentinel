# Slipstream Sentinel

Production-ready Discord bot for the Slipstream Motorsport Discord server.

## Prerequisites

- Python 3.11+
- A Discord Application in the [Developer Portal](https://discord.com/developers/applications) (do not create a new one)
- The bot's Client ID and Token
- A server (guild) where the bot will operate

## Setup

1. Clone the repository.
2. Install dependencies:
   ```bash
   python3 -m pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your credentials.
4. Ensure the existing Discord application has the following intents enabled in the Developer Portal:
   - Presence Intent
   - Server Members Intent
   - Message Content Intent
5. Invite the bot to the server with the following scopes:
   - `bot`
   - `applications.commands`
   Required permissions:
   - Send Messages
   - Embed Links
   - Manage Messages
   - Kick Members
   - Ban Members
   - Moderate Members
   - Read Message History
   - Use Slash Commands
6. Run the bot:
   ```bash
   python3 run.py
   ```
7. Slash commands will sync automatically to the configured guild on startup.

## Environment Configuration

Create a `.env` file in the project root:

| Variable | Description | Required |
|----------|-------------|----------|
| `DISCORD_TOKEN` | Bot token from Developer Portal | Yes |
| `CLIENT_ID` | Application client ID | Yes |
| `GUILD_ID` | Server ID for command sync | Yes |
| `WELCOME_CHANNEL_ID` | Channel ID for welcome messages | No |
| `MODLOG_CHANNEL_ID` | Channel ID for moderation logs | No |
| `AUTOMOD_MENTION_THRESHOLD` | Max mentions before action (default: 8) | No |
| `AUTOMOD_URL_THRESHOLD` | Max URLs before action (default: 3) | No |
| `AUTOMOD_SPAM_THRESHOLD` | Messages in window to trigger spam (default: 5) | No |
| `AUTOMOD_SPAM_WINDOW` | Time window in seconds for spam (default: 5.0) | No |

### Persisted Configuration

Some settings are persisted in `data/config.json` and survive restarts:
- Welcome channel (set via `/welcome_set`)
- Modlog channel (set via `/admin modlog_set`)

Banned words are persisted in `data/banned_words.json`.

## Architecture

```
src/
  __init__.py
  bot.py              # Bot initialization, intents, event loop, DB init
  config.py           # Environment loading, validation, typed settings
  cogs/
    __init__.py
    admin.py          # Admin commands (reload, config)
    info.py           # /ping, /about
    moderation.py     # /mod warn, timeout, kick, ban, unban, purge, history
    automod.py        # AutoMod rules, spam detection, escalation
    welcome.py        # on_member_join, /welcome_set
  modules/
    __init__.py
    config_storage.py # Persistent JSON config for runtime settings
  utils/
    __init__.py
    automod_helpers.py  # URL/mention/word extraction, SpamTracker
    automod_storage.py  # JSON persistence for banned words
    errors.py           # Centralized error handling
    helpers.py          # Mod hierarchy checks, modlog channel, DB logging
tests/
  test_automod_helpers.py
  test_config_storage.py
```

## Commands

### General
- `/ping` - Check bot latency
- `/about` - Bot information, uptime, versions

### Moderation (`/mod`)
- `/mod warn <member> [reason]` - Warn a member
- `/mod timeout <member> <minutes> [reason]` - Timeout a member (max 40320 min)
- `/mod kick <member> [reason]` - Kick a member
- `/mod ban <member> [reason]` - Ban a member
- `/mod unban <user_id> [reason]` - Unban a user by ID
- `/mod purge <amount>` - Purge messages (1-100)
- `/mod history <user>` - View moderation history for a user

### AutoMod
- `/automod_add <word>` - Add a banned word
- `/automod_remove <word>` - Remove a banned word
- `/automod_list` - List banned words

### Welcome
- `/welcome_set <channel>` - Set the welcome channel for this server

### Admin
- `/admin reload <cog>` - Reload a cog (requires Manage Messages)

## AutoMod Rules

- **Banned Words**: Messages containing configured banned words are deleted.
- **Excessive Mentions**: More than `AUTOMOD_MENTION_THRESHOLD` mentions triggers deletion.
- **Suspicious Links**: More than `AUTOMOD_URL_THRESHOLD` URLs triggers deletion.
- **Spam/Flooding**: Sending `AUTOMOD_SPAM_THRESHOLD` messages within `AUTOMOD_SPAM_WINDOW` seconds triggers deletion.
- **Escalation**: Repeated offenses (3+) result in automatic timeout escalation.

All automated actions are logged to the configured modlog channel and the SQLite database.

## Database

Moderation actions are logged to `data/modlog.db` (SQLite). The schema is auto-created on first run.

## Testing

Run the test suite:

```bash
python3 -m unittest discover -s tests -v
```

## Discord Permissions & Intents

### Intents (Bot tab in Developer Portal)
- **Presence Intent**: Optional, for presence updates
- **Server Members Intent**: Required for member join events
- **Message Content Intent**: Required for AutoMod message scanning

### OAuth2 Scopes
- `bot`
- `applications.commands`

### Bot Permissions
- Send Messages
- Embed Links
- Manage Messages
- Kick Members
- Ban Members
- Moderate Members
- Read Message History
- Use Slash Commands

## Development

```bash
python3 -m pip install -r requirements.txt
python3 run.py
```

## Deployment

### Process Manager (systemd)

Create `/etc/systemd/system/slipstream-sentinel.service`:

```ini
[Unit]
Description=Slipstream Sentinel Discord Bot
After=network.target

[Service]
Type=simple
User=discordbot
WorkingDirectory=/opt/slipstream-sentinel
ExecStart=/usr/bin/python3 run.py
Restart=always
RestartSec=10
EnvironmentFile=/opt/slipstream-sentinel/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable slipstream-sentinel
sudo systemctl start slipstream-sentinel
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "run.py"]
```

```bash
docker build -t slipstream-sentinel .
docker run -d --env-file .env --name sentinel slipstream-sentinel
```

## Future Roadmap

- League management (seasons, events, calendars)
- Driver and team profiles
- Race results ingestion and standings
- Stewarding workflows
- Beta tester role management
- Announcement scheduling
- Metrics and analytics dashboards

## License

MIT
