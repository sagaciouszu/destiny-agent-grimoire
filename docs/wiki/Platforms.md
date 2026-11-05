# Platform Notes

The archive is portable Python plus SQLite. Platform differences are mostly
package installation, config paths and directory links.

## Linux

### Debian / Ubuntu

```bash
sudo apt update
sudo apt install -y git python3 python3-venv curl
```

### Fedora

```bash
sudo dnf install -y git python3 python3-pip curl
```

### Arch Linux

```bash
sudo pacman -Syu
sudo pacman -S --needed git python python-pip curl base-devel
```

### Alpine Linux

```bash
sudo apk add git python3 py3-pip curl build-base
```

Then, for any distribution:

```bash
git clone https://github.com/sagaciouszu/destiny-agent-grimoire.git
cd destiny-agent-grimoire
python3 db/migrate.py
bash scripts/sync-live-agents.sh
bash mcp-server/install.sh
```

Notes:

- Config lives under `~/.config/opencode/`.
- MCP needs Python 3.10+.
- The current sync script does not require `rsync`.

## macOS

```bash
brew install git python curl
```

```bash
git clone https://github.com/sagaciouszu/destiny-agent-grimoire.git
cd destiny-agent-grimoire
python3 db/migrate.py
bash scripts/sync-live-agents.sh
bash mcp-server/install.sh
```

Notes:

- Use `~/.config/opencode/`.
- Python 3.10+ is required for the MCP adapter.
- Apple Silicon and Intel use the same commands.

## Windows

Prerequisites:

- Git for Windows
- Python 3.10+
- Git Bash or PowerShell

Clone and build:

```bat
git clone https://github.com/sagaciouszu/destiny-agent-grimoire.git
cd destiny-agent-grimoire
python3 db/migrate.py
bash scripts/sync-live-agents.sh
```

MCP:

```bat
cd mcp-server
python3 -m venv .venv
.venv\Scripts\pip.exe install --require-hashes -r requirements.lock.txt
```

Run it with either launcher:

```bat
mcp-server\run.cmd
```

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File mcp-server\run.ps1
```

Notes:

- Use `curl.exe`, not the PowerShell `curl` alias.
- Use `python3` from Git Bash or `py -3` from PowerShell if that is how Python
  is installed.
- If `ln -s` fails, create a junction: `mklink /J lore path\to\archive`.
- Paths in MCP client config must be absolute.

## Containers and CI

The project runs on a stock Python image with `git`, `curl` and `sqlite3`
available. CI uses Python 3.12 on Ubuntu. No service, database server or API key
is required.
