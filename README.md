# Bitcoin Knots Native Dashboard

A lightweight, self-hosted status dashboard for a **Bitcoin Knots** node. This is the native (non-Docker) version designed to run directly on the host.

## Features

- Real-time node status (sync progress, connections, mempool, fee estimates)
- **Latest Blocks** section with animated Umbrel-style cards (height, size, age)
- Light / Dark theme toggle with persistent preference
- System metrics (CPU temperature, load average)
- Tor onion address display
- Electrs sync status
- Clean, responsive interface
- Background auto-refresh

## Installation & Setup

### 1. Prepare the environment file

```bash
cp bitcoin-dashboard.env.example ~/.config/bitcoin-dashboard.env
nano ~/.config/bitcoin-dashboard.env
```

Set your RPC password (the plain-text password that matches your `rpcauth` line in `bitcoin.conf`).

### 2. Enable the user service

```bash
systemctl --user daemon-reload
systemctl --user enable --now bitcoin-dashboard.service
systemctl --user status bitcoin-dashboard.service
```

Access the dashboard at `http://your-pi-ip:8335`.

## Requirements

- Python 3.8+
- Running Bitcoin Knots node with RPC enabled
- The dashboard connects directly to the local `bitcoind` via JSON-RPC

### Environment Variables (required)

| Variable                  | Description                          | Default                  |
|---------------------------|--------------------------------------|--------------------------|
| `BITCOIN_RPC_URL`         | Bitcoin RPC endpoint                 | `http://127.0.0.1:8332` |
| `BITCOIN_RPC_USER`        | RPC username                         | `marian`                |
| `BITCOIN_RPC_PASSWORD`    | RPC password (or rpcauth equivalent) | *(required)*            |

### How RPC Authentication Works

The dashboard connects to your Bitcoin Knots node using HTTP Basic Auth.

- The dashboard reads a plain-text password from the `BITCOIN_RPC_PASSWORD` environment variable.
- Your `bitcoin.conf` must contain a matching `rpcauth` entry in the format `rpcauth=username:salt$hash`.
- The plain-text password in the dashboard's environment file must be the same password used to generate that `rpcauth` line.
- Never store the plain password in `bitcoin.conf` — only the salted hash belongs there.

This design keeps your node credentials secure while allowing the dashboard to authenticate locally.

## Running

### Manual start

```bash
BITCOIN_RPC_PASSWORD=yourpassword python3 app.py --host 0.0.0.0 --port 8335
```

Then open: `http://your-server:8335`

### Systemd (recommended)

Create the user service file at:

```bash
mkdir -p ~/.config/systemd/user
nano ~/.config/systemd/user/bitcoin-dashboard.service
```

**Example `bitcoin-dashboard.service`:**

```ini
[Unit]
Description=Bitcoin Dashboard
After=network.target

[Service]
Type=simple
EnvironmentFile=%h/.config/bitcoin-dashboard.env
WorkingDirectory=%h/bitcoin-dashboard
ExecStart=/usr/bin/python3 %h/bitcoin-dashboard/app.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
```

> **Note:** Adjust `WorkingDirectory` and `ExecStart` if you installed the dashboard in a different location.

Then enable and start it:

```bash
systemctl --user daemon-reload
systemctl --user enable --now bitcoin-dashboard.service
systemctl --user status bitcoin-dashboard.service
journalctl --user -u bitcoin-dashboard.service -f
```

## API Endpoints

| Endpoint       | Description                  |
|----------------|------------------------------|
| `/api/status`  | Full node + system status    |
| `/healthz`     | Simple health check          |

## Configuration

All sensitive configuration lives in the environment file:

```bash
~/.config/bitcoin-dashboard.env
```

**Important:**
- `BITCOIN_RPC_PASSWORD` must be the **plain-text** password that matches the `rpcauth` entry in your `bitcoin.conf`.
- If you change the password or regenerate the `rpcauth` line in `bitcoin.conf`, you **must restart `bitcoind`** for the new credentials to take effect.
- The dashboard never edits or stores credentials itself — it only reads from the environment at startup.

Default listening port: **8335**

## Project Structure

```
bitcoin-dashboard/
├── app.py          # Python backend (SimpleHTTPRequestHandler + status collector)
├── app.js          # Frontend logic + rendering
├── index.html      # Main UI
├── styles.css      # Styling + dark/light themes
├── icon.svg        # Node icon
├── VERSION         # Dashboard version shown in the page footer
└── README.md
```

## Notes

- This is the **native** version. A Docker-based variant will be created separately.
- The dashboard is read-only and safe to expose on your local network.

## License

MIT
