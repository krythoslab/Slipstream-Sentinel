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
| `ANNOUNCEMENT_CHANNEL_ID` | Channel ID for announcements | No |
| `AUTOMOD_ALERT_CHANNEL_ID` | Channel ID for AutoMod alerts | No |
| `AUTOMOD_MENTION_THRESHOLD` | Max mentions before action (default: 8) | No |
| `AUTOMOD_URL_THRESHOLD` | Max URLs before action (default: 3) | No |
| `AUTOMOD_SPAM_THRESHOLD` | Messages in window to trigger spam (default: 5) | No |
| `AUTOMOD_SPAM_WINDOW` | Time window in seconds for spam (default: 5.0) | No |
| `AUTOMOD_RAID_THRESHOLD` | Joins in window to trigger raid (default: 10) | No |
| `AUTOMOD_RAID_WINDOW` | Time window in seconds for raid (default: 60.0) | No |

### Persisted Configuration

Some settings are persisted in `data/config.json` and survive restarts:
- Welcome/leave channels (set via `/config`)
- Modlog/announcement/AutoMod alert channels
- Welcome/leave message templates
- AutoMod thresholds
- Exempt channels and roles
- Staff IDs

Banned words are persisted in `data/banned_words.json`.

## Architecture

```
src/
  __init__.py
  bot.py              # Bot initialization, intents, event loop, DB init
  config.py           # Environment loading, validation, typed settings
  cogs/
    __init__.py
    admin.py          # Admin commands (reload)
    info.py           # /ping, /about, /help, /status
    moderation.py     # /mod warn, timeout, kick, ban, unban, purge, history, lock, unlock, slowmode
    automod.py        # AutoMod rules, spam detection, escalation, exemptions, config
    welcome.py        # on_member_join/leave, /welcome_set
    config.py         # /config group for channel and message settings
    announcements.py  # /announce for server announcements
    roles.py          # /role give, /role remove
    infoserver.py     # /serverinfo, /userinfo
    polls.py          # /poll for quick polls
    league.py         # /league register, /league team, /league standings
    racecontrol.py    # /steward report, /steward cases, /steward close
    automation.py     # /remind, scheduled tasks
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
  test_cog_loading.py
```

## Commands

### General
- `/ping` - Check bot latency
- `/about` - Bot information, uptime, versions
- `/help` - Show available commands
- `/status` - Set bot activity status

### Moderation (`/mod`)
- `/mod warn <member> [reason]` - Warn a member
- `/mod unwarn <member> [reason]` - Remove latest warning
- `/mod warnings <member>` - List warnings for a member
- `/mod timeout <member> <minutes> [reason]` - Timeout a member
- `/mod untimeout <member> [reason]` - Remove timeout
- `/mod kick <member> [reason]` - Kick a member
- `/mod ban <member> [reason]` - Ban a member
- `/mod unban <user_id> [reason]` - Unban a user
- `/mod purge <amount>` - Purge messages (1-100)
- `/mod lock [channel]` - Lock a channel
- `/mod unlock [channel]` - Unlock a channel
- `/mod slowmode <seconds> [channel]` - Set slowmode
- `/mod history <user>` - View moderation history

### AutoMod
- `/automod_add <word>` - Add a banned word
- `/automod_remove <word>` - Remove a banned word
- `/automod_list` - List banned words
- `/automod_exempt <add|remove> <channel|role> <id>` - Manage exemptions
- `/automod_config [setting] [value]` - View or update thresholds

### Welcome
- `/welcome_set <channel>` - Set welcome channel
- `/leave_set <channel>` - Set leave channel
- `/welcome_message_set <message>` - Set welcome message template
- `/leave_message_set <message>` - Set leave message template

### Config (`/config`)
- `/config welcome_channel <channel>` - Set welcome channel
- `/config leave_channel <channel>` - Set leave channel
- `/config modlog_channel <channel>` - Set modlog channel
- `/config announcement_channel <channel>` - Set announcement channel
- `/config automod_alert_channel <channel>` - Set AutoMod alert channel
- `/config welcome_message <message>` - Set welcome message
- `/config leave_message <message>` - Set leave message

### Announcements
- `/announce <title> <message>` - Send an announcement

### Roles (`/role`)
- `/role give <member> <role>` - Give a role
- `/role remove <member> <role>` - Remove a role

### Info
- `/serverinfo` - Show server information
- `/userinfo [user]` - Show user information

### Polls
- `/poll <question> <option1> <option2> [option3] [option4]` - Create a poll

### League (`/league`)
- `/league register <number>` - Register as a driver
- `/league team <name>` - Set your team
- `/league standings` - Show driver standings

### Stewarding (`/steward`)
- `/steward report <driver> <description> [evidence]` - File incident report
- `/steward cases` - List open cases
- `/steward close <incident_number> [penalty] [reason]` - Close a case

### Automation
- `/remind <seconds> <message>` - Set a reminder

### Admin (`/admin`)
- `/admin reload <cog>` - Reload a cog

## AutoMod Rules

- **Banned Words**: Messages containing configured banned words are deleted.
- **Excessive Mentions**: More than `AUTOMOD_MENTION_THRESHOLD` mentions triggers deletion.
- **Suspicious Links**: More than `AUTOMOD_URL_THRESHOLD` URLs triggers deletion.
- **Spam/Flooding**: Sending `AUTOMOD_SPAM_THRESHOLD` messages within `AUTOMOD_SPAM_WINDOW` seconds triggers deletion.
- **Repeated Messages**: Sending the same message 4+ times in 60s triggers deletion.
- **Raid Detection**: `AUTOMOD_RAID_THRESHOLD` joins in `AUTOMOD_RAID_WINDOW` seconds triggers an alert.
- **Exemptions**: Staff members, exempt roles, and exempt channels bypass AutoMod.
- **Escalation**: Repeated offenses (3+) result in automatic timeout escalation.

All automated actions are logged to the configured modlog channel and the SQLite database.

## Database

Moderation actions, league data, and race control cases are logged to `data/modlog.db` (SQLite). The schema is auto-created on first run.

## Testing

Run the test suite:

```bash
python3 -m unittest discover -s tests -v
```

## Discord Permissions & Intents

### Intents (Bot tab in Developer Portal)
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

### Oracle Cloud Always Free (Recommended)

Deploy Sentinel as a 24/7 background service using systemd on an Oracle Cloud Always Free VM.

#### 1. Provision the VM

- Create an **Oracle Linux 8/9** or **Ubuntu 22.04/24.04** instance in the Oracle Cloud Always Free tier.
- Open port **22** (SSH) in the VCN security list.
- (Optional) Open port **80/443** if you plan to expose a web dashboard later.

#### 2. Connect via SSH

```bash
ssh -i /path/to/your/key opc@<your-vm-ip>
```

For Oracle Linux, the default user is `opc`. For Ubuntu, it's `ubuntu`.

#### 3. Install System Dependencies

**Oracle Linux:**

```bash
sudo dnf update -y
sudo dnf install -y python3 python3-pip python3-venv git
```

**Ubuntu:**

```bash
sudo apt update -y
sudo apt install -y python3 python3-pip python3-venv git
```

#### 4. Create a Non-Root User

```bash
sudo useradd -m -s /bin/bash discordbot
sudo passwd discordbot
```

#### 5. Clone the Repository

```bash
sudo -u discordbot -H bash -c '
git clone https://github.com/krythoslab/Slipstream-Sentinel.git /opt/slipstream-sentinel &&
cd /opt/slipstream-sentinel &&
python3 -m venv .venv &&
source .venv/bin/activate &&
pip install --upgrade pip &&
pip install -r requirements.txt
'
```

#### 6. Configure Secrets

```bash
sudo -u discordbot bash -c '
cp .env.example .env
nano .env
```

Fill in:
- `DISCORD_TOKEN` (from Discord Developer Portal)
- `CLIENT_ID=1545238354302607450`
- `GUILD_ID=1545179492815741059`

**Security:** `.env` is gitignored and must never be committed.

#### 7. Install the systemd Service

```bash
sudo cp systemd/slipstream-sentinel.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable slipstream-sentinel
```

#### 8. Start the Bot

```bash
sudo systemctl start slipstream-sentinel
```

#### 9. Verify It's Running

```bash
sudo systemctl status slipstream-sentinel
journalctl -u slipstream-sentinel -f
```

#### 10. Common Operations

| Task | Command |
|------|---------|
| Check status | `sudo systemctl status slipstream-sentinel` |
| View logs | `sudo journalctl -u slipstream-sentinel -f` |
| Restart | `sudo systemctl restart slipstream-sentinel` |
| Stop | `sudo systemctl stop slipstream-sentinel` |
| Disable autostart | `sudo systemctl disable slipstream-sentinel` |
| Re-enable autostart | `sudo systemctl enable slipstream-sentinel` |

#### 11. Update Sentinel

```bash
sudo -u discordbot bash -c '
cd /opt/slipstream-sentinel &&
git pull origin main &&
source .venv/bin/activate &&
pip install -r requirements.txt &&
exit
'
sudo systemctl restart slipstream-sentinel
```

### Docker Deployment (Alternative)

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
docker run -d --env-file .env --name sentinel --restart unless-stopped slipstream-sentinel
```

### Security Notes

- Never commit `.env` or any file containing `DISCORD_TOKEN`.
- The systemd service file uses `ProtectSystem=full`, `ProtectHome=read-only`, and `NoNewPrivileges=true`.
- Run as a dedicated `discordbot` user, never as root.
- The `.env` file should have permissions `600` (`chmod 600 .env`).

## Roadmap

- Phase 1: Core moderation, welcome, AutoMod, utility (complete)
- Phase 2: Config system, announcements, polls, roles, server info (complete)
- Phase 3: League management (seasons, events, calendars, standings)
- Phase 4: Stewarding workflows
- Phase 5: Automation, external API integration, dashboard

## License

MIT
