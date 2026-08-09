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

## Requirements

- Python 3.8+
- Running Bitcoin Knots node with RPC enabled (`rpcuser` / `rpcpassword` configured)
- The dashboard connects directly to the local `bitcoind` via JSON-RPC

## Running

### Manual start

```bash
python3 app.py --host 0.0.0.0 --port 8335
```

Then open: `http://your-server:8335`

### Systemd (recommended)

A user service is provided:

```bash
systemctl --user status bitcoin-dashboard.service
systemctl --user restart bitcoin-dashboard.service
journalctl --user -u bitcoin-dashboard.service -f
```

The service file is located at:
`~/.config/systemd/user/bitcoin-dashboard.service`

## API Endpoints

| Endpoint       | Description                  |
|----------------|------------------------------|
| `/api/status`  | Full node + system status    |
| `/healthz`     | Simple health check          |

## Configuration

The dashboard reads Bitcoin RPC credentials directly from the `bitcoin_rpc()` function inside `app.py`. Update the credentials there if your `rpcuser`/`rpcpassword` differ.

Default port: **8335**

## Project Structure

```
bitcoin-dashboard/
├── app.py          # Python backend (SimpleHTTPRequestHandler + status collector)
├── app.js          # Frontend logic + rendering
├── index.html      # Main UI
├── styles.css      # Styling + dark/light themes
├── icon.svg        # Node icon
└── README.md
```

## Notes

- This is the **native** version. A Docker-based variant will be created separately.
- The dashboard is read-only and safe to expose on your local network.

## License

MIT
