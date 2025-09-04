# TapHome SDK

Python SDK for [TapHome](https://taphome.com) smart home systems.

## Description

This SDK provides Python bindings for communicating with TapHome smart home devices and hubs. It supports local and cloud connections, real-time updates via webhooks, and a comprehensive set of device types.

## Features

- **Device Support**: Binary sensors, buttons, climate control, covers, lights, switches, sensors, and more
- **Connection Types**: Local network, cloud, and local push (webhooks)
- **Real-time Updates**: Immediate status updates through TapHome webhooks
- **Async/Await**: Built with modern Python async/await patterns
- **Type Safety**: Full type hints for better development experience

## Installation

```bash
pip install taphome-sdk
```

## Supported Device Types

- Analog Output
- Bidirectional (covers, shutters)
- Buttons
- Digital Output
- Generic Output Adapter
- Lights (RGB, Dual White)
- Multi-value Switches
- Thermostats
- Variables and Session Duration Variables

## Usage

```python
from taphome_sdk import TapHomeHub, TapHomeHubFactory

# Create hub instance
hub = TapHomeHubFactory.create_hub(
    token="your_token",
    base_url="http://your-taphome-hub"
)

# Connect to hub
await hub.start()

# Get device
device = hub.get_device(device_id)

# Subscribe to device changes
def on_device_change(device):
    print(f"Device {device.device_id} changed")

device.state.subscribe(on_device_change)
```

## Requirements

- Python 3.10 or higher
- aiohttp

## License

This project is licensed under the GPL v3 or later. See the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.