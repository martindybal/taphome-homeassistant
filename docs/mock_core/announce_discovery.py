"""Announce a TapHome core via mDNS to test the zeroconf discovery flow.

Real cores announce ``_th-discovery._tcp.local.`` themselves, but LAN
multicast usually does not reach a Home Assistant instance running in Docker
Desktop / WSL2. Running this script *inside the same environment as Home
Assistant* (e.g. in the HA container) replays the announcement there; the
discovery card appears and confirming it connects to the announced IP over
plain HTTP, which works even where multicast does not.

Announce a real core (Home Assistant then talks to the real API):

    python docs/mock_core/announce_discovery.py \
        --ip 192.168.1.3 --name "Moderní Jeskyně" \
        --location-id 9b9f22c5-241b-4c84-ab63-d27f48b3b4ce

Or pair it with mock_taphome_api.py (defaults match its fixtures):

    python docs/mock_core/announce_discovery.py --ip 127.0.0.1
"""

from __future__ import annotations

import argparse
import socket
import time

from zeroconf import ServiceInfo, Zeroconf

SERVICE_TYPE = "_th-discovery._tcp.local."
# The port real cores advertise; it belongs to the TapHome app protocol and
# the integration ignores it (the HTTP API stays on port 80).
ADVERTISED_PORT = 11764


def main() -> None:
    """Register the announcement and keep it alive until interrupted."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ip", required=True, help="IP address the core (or mock) API listens on")
    parser.add_argument("--name", default="Mock Home", help="location name shown on the discovery card")
    parser.add_argument(
        "--location-id",
        default="11111111-2222-3333-4444-555555555555",
        help="location id (the config-entry unique id); default matches the mock fixtures",
    )
    args = parser.parse_args()

    slug = args.name.replace(" ", "-")
    info = ServiceInfo(
        SERVICE_TYPE,
        f"th-{slug}.{SERVICE_TYPE}",
        addresses=[socket.inet_aton(args.ip)],
        port=ADVERTISED_PORT,
        server=f"{slug}.local.",
        properties={
            "Name": args.name,
            "LocationId": args.location_id,
            "IpOnLocalNetwork": args.ip,
            # The app pairing token; the integration must never use it.
            "AccessToken": "mock-pairing-token",
        },
    )

    zeroconf = Zeroconf()
    zeroconf.register_service(info)
    print(f"Announcing {args.name} ({args.location_id}) at {args.ip} — Ctrl+C to stop")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        zeroconf.unregister_service(info)
        zeroconf.close()


if __name__ == "__main__":
    main()
