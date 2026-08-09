#!/usr/bin/env python3
import argparse
import json
import subprocess
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

def bitcoin_rpc(method, params=None):
    import urllib.request
    import json
    import base64
    url = "http://127.0.0.1:8332"
    user = "marian"
    password = "M@rianB0ricean2503"
    auth = base64.b64encode(f"{user}:{password}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    data = json.dumps({"jsonrpc": "1.0", "id": "dashboard", "method": method, "params": params or []}).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            if "error" in result and result["error"]:
                raise RuntimeError(result["error"])
            return result.get("result")
    except Exception as e:
        raise RuntimeError(str(e))


APP_DIR = Path(__file__).resolve().parent
CACHE = None
CACHE_LOCK = threading.Lock()
REFRESHING = False
REFRESH_INTERVAL_SECONDS = 30


def get_electrs_status():
    try:
        with urllib.request.urlopen("http://127.0.0.1:4224", timeout=5) as resp:
            data = resp.read().decode("utf-8")
        height = None
        for line in data.splitlines():
            if line.startswith('electrs_index_height{type="tip"}'):
                height = int(line.split()[-1])
                break
        return {
            "running": True,
            "height": height,
        }
    except Exception as e:
        return {"running": False, "error": str(e)}

def get_system_metrics():
    metrics = {
        "cpu_temp_c": None,
        "load_1m": None,
        "load_5m": None,
        "load_15m": None,
    }

    # CPU temperature - try multiple methods (Pi 5 friendly)
    try:
        # Preferred on modern Raspberry Pi OS
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            temp_raw = int(f.read().strip())
            metrics["cpu_temp_c"] = round(temp_raw / 1000.0, 1)
    except Exception:
        pass

    if metrics["cpu_temp_c"] is None:
        try:
            result = subprocess.run(
                ["vcgencmd", "measure_temp"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                output = result.stdout.strip()
                if "=" in output:
                    temp_str = output.split("=")[1].replace("'C", "")
                    metrics["cpu_temp_c"] = float(temp_str)
        except Exception:
            pass

    # Load average (very reliable)
    try:
        with open("/proc/loadavg") as f:
            parts = f.read().strip().split()
            metrics["load_1m"] = float(parts[0])
            metrics["load_5m"] = float(parts[1])
            metrics["load_15m"] = float(parts[2])
    except Exception:
        pass

    return metrics


def get_tor_status():
    try:
        # Check if service is active
        active_result = subprocess.run(
            ["systemctl", "is-active", "tor"],
            capture_output=True,
            text=True,
            timeout=3
        )
        running = active_result.stdout.strip() == "active"

        started_at = None
        uptime_seconds = None

        if running:
            # Get when the service entered active state
            ts_result = subprocess.run(
                ["systemctl", "show", "tor", "--property=ActiveEnterTimestamp", "--value"],
                capture_output=True,
                text=True,
                timeout=3
            )
            timestamp_str = ts_result.stdout.strip()
            if timestamp_str:
                # Parse systemd timestamp (e.g. "Thu 2026-08-06 16:51:02 EDT")
                try:
                    dt = datetime.strptime(timestamp_str, "%a %Y-%m-%d %H:%M:%S %Z")
                    started_at = int(dt.replace(tzinfo=timezone.utc).timestamp())
                    uptime_seconds = int(time.time()) - started_at
                except Exception:
                    pass

        return {
            "name": "tor",
            "running": running,
            "status": "native",
            "health": None,
            "started_at": started_at,
            "uptime_seconds": uptime_seconds,
        }
    except Exception:
        return {
            "name": "tor",
            "running": None,
            "status": "native",
            "health": None,
            "started_at": None,
            "uptime_seconds": None,
        }

def collect_status():
    started = time.time()
    errors = []

    try:
        blockchain = bitcoin_rpc("getblockchaininfo")
    except Exception as e:
        blockchain = {}
        errors.append({"source": "getblockchaininfo", "message": str(e)})

    # Recent blocks (last 8) for mini-list
    recent_blocks = []
    try:
        height = blockchain.get("blocks")
        if height is not None:
            for i in range(8):
                h = height - i
                if h < 0:
                    break
                try:
                    block_hash = bitcoin_rpc("getblockhash", [h])
                    header = bitcoin_rpc("getblockheader", [block_hash])
                    stats = bitcoin_rpc("getblockstats", [h])
                    recent_blocks.append({
                        "height": header.get("height"),
                        "time": header.get("time"),
                        "tx_count": stats.get("txs"),
                        "size": stats.get("total_size"),
                        "hash": header.get("hash"),
                    })
                except Exception as e:
                    errors.append({"source": "recent_block_" + str(h), "message": str(e)})
                    # skip bad block instead of breaking the whole collection
    except Exception as e:
        errors.append({"source": "recent_blocks", "message": str(e)})

    try:
        network = bitcoin_rpc("getnetworkinfo")
    except Exception as e:
        network = {}
        errors.append({"source": "getnetworkinfo", "message": str(e)})

    try:
        mempool = bitcoin_rpc("getmempoolinfo")
    except Exception as e:
        mempool = {}
        errors.append({"source": "getmempoolinfo", "message": str(e)})

    # Fee estimates (targets 1 = next block, 3 ≈30min, 6 ≈1h)
    fee_estimates = {}
    for target_blocks, label in [(1, "next_block"), (3, "30min"), (6, "1h")]:
        try:
            est = bitcoin_rpc("estimatesmartfee", [target_blocks])
            fee_estimates[label] = {
                "feerate": est.get("feerate"),
                "blocks": est.get("blocks"),
            }
        except Exception as e:
            errors.append({"source": f"estimatesmartfee {target_blocks}", "message": str(e)})
            fee_estimates[label] = None

    try:
        uptime = bitcoin_rpc("uptime")
    except Exception as e:
        uptime = None
        errors.append({"source": "uptime", "message": str(e)})

    try:
        peerinfo = bitcoin_rpc("getpeerinfo")
    except Exception:
        peerinfo = []

    electrs = get_electrs_status()
    if electrs.get("running") and electrs.get("height") is not None:
        node_height = blockchain.get("blocks")
        if node_height:
            progress = min(100.0, (electrs["height"] / node_height) * 100)
            electrs["progress_percent"] = round(progress, 2)

    tor = get_tor_status()

    peers = []
    inbound = outbound = 0
    onion_peers = clearnet_peers = 0
    for peer in peerinfo:
        is_inbound = bool(peer.get("inbound"))
        inbound += int(is_inbound)
        outbound += int(not is_inbound)
        network_name = peer.get("network") or "unknown"
        onion_peers += int(network_name == "onion")
        clearnet_peers += int(network_name != "onion")
        peers.append({
            "id": peer.get("id"),
            "addr": peer.get("addr"),
            "network": network_name,
            "inbound": is_inbound,
            "connection_type": peer.get("connection_type"),
            "subver": peer.get("subver"),
            "startingheight": peer.get("startingheight"),
            "synced_blocks": peer.get("synced_blocks"),
            "synced_headers": peer.get("synced_headers"),
            "pingtime_ms": round(peer.get("pingtime", 0) * 1000, 0) if peer.get("pingtime") is not None else None,
        })

    verification_progress = blockchain.get("verificationprogress")
    progress_percent = round(verification_progress * 100, 2) if verification_progress is not None else None

    warnings = []
    for source in (blockchain, network):
        item = source.get("warnings")
        if isinstance(item, list):
            warnings.extend(str(w) for w in item if w)
        elif item:
            warnings.append(str(item))

    # Custom warnings
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        if free < 5 * 1024**3:  # less than 5 GB free on root
            warnings.append(f"Low disk space on /: only {free // (1024**3)} GB free")

        total2, used2, free2 = shutil.disk_usage("/data")
        if free2 < 100 * 1024**3:  # less than 100 GB free on /data
            warnings.append(f"Low disk space on /data: only {free2 // (1024**3)} GB free")
    except Exception:
        pass

    # High mempool warning
    try:
        mempool_bytes = mempool.get("bytes") or 0
        if mempool_bytes > 300 * 1024**2:  # > 300 MB
            warnings.append(f"Large mempool: {mempool_bytes // (1024**2)} MB")
    except Exception:
        pass

    networks = network.get("networks", [])
    network_reachability = {item.get("name"): bool(item.get("reachable")) for item in networks if item.get("name")}

    # Extract onion hostname for the Tor row
    onion_hostname = None
    for item in network.get("localaddresses", []):
        addr = item.get("address", "")
        if addr.endswith(".onion"):
            onion_hostname = f"{addr}:{item.get('port', 8333)}"
            break

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": round((time.time() - started) * 1000),
       "chain": blockchain.get("chain"),
        "sync": {
            "blocks": blockchain.get("blocks"),
            "headers": blockchain.get("headers"),
            "progress_percent": progress_percent,
            "initial_block_download": blockchain.get("initialblockdownload"),
            "best_block_time": blockchain.get("time"),
            "size_on_disk_bytes": blockchain.get("size_on_disk"),
            "pruned": blockchain.get("pruned"),
        },
        "connections": {
            "total": network.get("connections"),
            "in": network.get("connections_in", inbound),
            "out": network.get("connections_out", outbound),
            "onion_peers": onion_peers,
            "clearnet_peers": clearnet_peers,
        },
        "network": {
            "version": network.get("version"),
            "subversion": network.get("subversion"),
            "protocolversion": network.get("protocolversion"),
            "localaddresses": network.get("localaddresses", []),
            "reachable": network_reachability,
        },
        "mempool": {
            "loaded": mempool.get("loaded"),
            "size": mempool.get("size"),
            "bytes": mempool.get("bytes"),
            "usage": mempool.get("usage"),
            "mempoolminfee": mempool.get("mempoolminfee"),
            "minrelaytxfee": mempool.get("minrelaytxfee"),
            "fee_estimates": fee_estimates,
        },
        "services": {
            "knots": {"name": "bitcoind", "running": True, "status": "native", "health": None, "started_at": None, "uptime_seconds": uptime},
            "tor": tor,
            "electrs": electrs,
            "knots_uptime_seconds": uptime,
            "onion_hostname": onion_hostname,
        },
        "system": get_system_metrics(),
        "warnings": warnings,
        "errors": errors,
        "peers": peers,
        "recent_blocks": recent_blocks,
        "cache": {"fresh": True, "refresh_interval_seconds": REFRESH_INTERVAL_SECONDS},
    }

def empty_status():
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "duration_ms": 0,
        "chain": None,
        "sync": {},
        "connections": {},
        "network": {"localaddresses": [], "reachable": {}},
        "mempool": {},
        "services": {},
        "warnings": [],
        "errors": [{"source": "dashboard", "message": "Status collection is starting."}],
        "peers": [],
        "cache": {"fresh": False, "refreshing": True, "refresh_interval_seconds": REFRESH_INTERVAL_SECONDS},
    }

def refresh_cache():
    global CACHE, REFRESHING
    try:
        status = collect_status()
        with CACHE_LOCK:
            CACHE = status
    finally:
        with CACHE_LOCK:
            REFRESHING = False

def ensure_refresh():
    global REFRESHING
    with CACHE_LOCK:
        if REFRESHING:
            return
        if CACHE is not None:
            generated_at = datetime.fromisoformat(CACHE["generated_at"])
            age = (datetime.now(timezone.utc) - generated_at).total_seconds()
            if age < REFRESH_INTERVAL_SECONDS:
                return
        REFRESHING = True
    threading.Thread(target=refresh_cache, daemon=True).start()

def refresh_loop():
    while True:
        ensure_refresh()
        time.sleep(REFRESH_INTERVAL_SECONDS)

def cached_status():
    with CACHE_LOCK:
        if CACHE is None:
            return empty_status()
        status = dict(CACHE)
        status["cache"] = dict(status.get("cache", {}))
        status["cache"]["fresh"] = (datetime.now(timezone.utc) - datetime.fromisoformat(status["generated_at"])).total_seconds() < REFRESH_INTERVAL_SECONDS * 2
        status["cache"]["refreshing"] = REFRESHING
        return status

class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=APP_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/status":
            self.send_json(cached_status())
            return
        if path == "/healthz":
            self.send_json({"ok": True})
            return
        super().do_GET()

    def send_json(self, payload, status=200):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8335, type=int)
    args = parser.parse_args()

    hosts = [host.strip() for host in args.host.split(",") if host.strip()]
    servers = [ThreadingHTTPServer((host, args.port), DashboardHandler) for host in hosts]
    for server in servers:
        host, port = server.server_address[:2]
        print(f"Knots dashboard listening on http://{host}:{port}", flush=True)
    threading.Thread(target=refresh_loop, daemon=True).start()
    for server in servers[1:]:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    servers[0].serve_forever()

if __name__ == "__main__":
    main()
