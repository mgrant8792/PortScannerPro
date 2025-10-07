#!/usr/bin/env python3
"""
PortScannerPro
Simple, respectful TCP port scanner using threads.

Usage examples:
    python port_scanner.py --host 192.168.1.10 --ports 1-1024 --timeout 0.5 --workers 200
    python port_scanner.py --host example.com --ports 22,80,443 --json results.json

IMPORTANT: Only scan hosts you own or have permission to scan.
"""

import socket
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import json
from common_ports import COMMON_PORTS
import csv

def parse_ports(ports_str):
    """Parse ports like '1-1024' or '22,80,443' into a sorted list of ints."""
    ports = set()
    for part in ports_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = part.split('-', 1)
            ports.update(range(int(start), int(end) + 1))
        else:
            if part:
                ports.add(int(part))
    return sorted(ports)

def scan_port(host, port, timeout=0.5):
    """Try to connect. Return (port, open_bool)"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        result = s.connect_ex((host, port))
        s.close()
        return port, (result == 0)
    except Exception:
        return port, False

def scan_host(host, ports, timeout=0.5, workers=100):
    results = {}
    start = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(scan_port, host, p, timeout): p for p in ports}
        for fut in as_completed(futures):
            port, is_open = fut.result()
            svc = COMMON_PORTS.get(port, "")
            results[port] = {"open": is_open, "service_guess": svc}
    elapsed = time.time() - start
    return results, elapsed

def pretty_print(results, host, elapsed):
    open_ports = [p for p, info in results.items() if info["open"]]
    print(f"\nScan results for {host} (elapsed {elapsed:.2f}s):")
    if not open_ports:
        print("  No open ports found (in scanned range).")
        return
    print("  Open ports:")
    for p in sorted(open_ports):
        svc = results[p]["service_guess"]
        svc_str = f" ({svc})" if svc else ""
        print(f"   - {p}{svc_str}")

def write_json(path, host, results, elapsed):
    out = {"host": host, "elapsed": elapsed, "ports": results}
    with open(path, "w", encoding="utf8") as f:
        json.dump(out, f, indent=2)

def write_csv(path, host, results, elapsed):
    with open(path, "w", newline='', encoding="utf8") as f:
        writer = csv.writer(f)
        writer.writerow(["host", host])
        writer.writerow(["elapsed_seconds", f"{elapsed:.4f}"])
        writer.writerow([])
        writer.writerow(["port", "open", "service_guess"])
        for p in sorted(results.keys()):
            info = results[p]
            writer.writerow([p, info["open"], info["service_guess"]])

def main():
    parser = argparse.ArgumentParser(description="PortScannerPro — polite threaded TCP port scanner")
    parser.add_argument("--host", required=True, help="Target hostname or IP")
    parser.add_argument("--ports", default="1-1024",
                        help="Ports to scan: single (22), comma list (22,80,443) or range (1-1024)")
    parser.add_argument("--timeout", type=float, default=0.5, help="Socket timeout (seconds)")
    parser.add_argument("--workers", type=int, default=200, help="Thread pool size")
    parser.add_argument("--json", help="Save JSON results here")
    parser.add_argument("--csv", help="Save CSV results here")
    args = parser.parse_args()

    try:
        ports = parse_ports(args.ports)
    except Exception as e:
        print("Error parsing ports:", e)
        return

    print(f"Scanning {args.host} : {len(ports)} ports (timeout={args.timeout}, workers={args.workers})...")
    results, elapsed = scan_host(args.host, ports, timeout=args.timeout, workers=args.workers)
    pretty_print(results, args.host, elapsed)

    if args.json:
        write_json(args.json, args.host, results, elapsed)
        print(f"Saved JSON -> {args.json}")
    if args.csv:
        write_csv(args.csv, args.host, results, elapsed)
        print(f"Saved CSV -> {args.csv}")

if __name__ == "__main__":
    main()
