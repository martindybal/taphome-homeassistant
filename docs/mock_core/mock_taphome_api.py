"""Mock TapHome core API server for local development and testing.

Run with:
    python docs/mock_core/mock_taphome_api.py --port 8123 --token secret

Then add the integration with API URL http://127.0.0.1:8123/api/TapHomeApi/v1
and the chosen token. Requests with a different token get HTTP 401, which
exercises the invalid_auth and reauth flows.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time

from aiohttp import web

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    """Load a JSON fixture and stamp the current timestamp."""
    data = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    data["timestamp"] = int(time.time())
    return data


def create_app(token: str) -> web.Application:
    """Create the mock TapHome API application."""

    @web.middleware
    async def check_token(request: web.Request, handler):
        if request.headers.get("Authorization") != f"TapHome {token}":
            raise web.HTTPUnauthorized(reason="Invalid token")
        return await handler(request)

    async def location(_: web.Request) -> web.Response:
        return web.json_response(_load("location.json"))

    async def discovery(_: web.Request) -> web.Response:
        return web.json_response(_load("discovery.json"))

    async def all_values(_: web.Request) -> web.Response:
        return web.json_response(_load("values.json"))

    async def device_values(request: web.Request) -> web.Response:
        device_id = int(request.match_info["device_id"])
        values = _load("values.json")
        for device in values["devices"]:
            if device["deviceId"] == device_id:
                device["timestamp"] = values["timestamp"]
                return web.json_response(device)
        raise web.HTTPNotFound

    async def set_device_value(request: web.Request) -> web.Response:
        body = await request.json()
        return web.json_response(
            {
                "deviceId": body["deviceId"],
                "valuesChanged": [
                    {"typeId": value["valueTypeId"], "result": "CHANGED"}
                    for value in body["values"]
                ],
                "timestamp": int(time.time()),
            }
        )

    app = web.Application(middlewares=[check_token])
    prefix = "/api/TapHomeApi/v1"
    app.add_routes(
        [
            web.get(f"{prefix}/location", location),
            web.get(f"{prefix}/discovery", discovery),
            web.get(f"{prefix}/getAllDevicesValues", all_values),
            web.get(f"{prefix}/getDeviceValue/{{device_id}}", device_values),
            web.post(f"{prefix}/setDeviceValue", set_device_value),
        ]
    )
    return app


def main() -> None:
    """Run the mock server from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8123)
    parser.add_argument("--token", default="secret")
    args = parser.parse_args()
    web.run_app(create_app(args.token), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
