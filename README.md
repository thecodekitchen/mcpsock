# MCPSock

MCPSock is a Python library that provides WebSocket client and server implementations for the FastMCP framework. It offers a clean, easy-to-use API for building WebSocket-based applications that communicate using the FastMCP framework.

## Features

- **WebSocketClient**: A standalone client for connecting to FastMCP WebSocket servers
- **WebSocketServer**: A decorator-based router for handling FastMCP WebSocket communications
- Support for tools, resources, and prompts
- Easy integration with FastAPI applications
- Async/await support

## Installation
with pip

```bash
pip install mcpsock
```
or with uv (recommended)
```bash
uv add mcpsock
```

## Quick Start

### Client Example

```python
import asyncio
from mcpsock import WebSocketClient

async def main():
    # Connect to a FastMCP WebSocket server
    async with WebSocketClient("ws://localhost:8000/ws") as client:
        # List available tools
        tools = await client.list_tools()
        print(f"Available tools: {tools}")

        # Call a tool
        result = await client.call_tool("example/tool", {"param": "value"})
        print(f"Tool result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Server Example

```python
from fastapi import FastAPI
from mcpsock import WebSocketServer
import uvicorn

# Create a FastAPI app
app = FastAPI()

# Create a WebSocketServer
router = WebSocketServer()

# Register a tool handler
@router.tool("example/tool")
async def example_tool(message, websocket):
    params = message.get("params", {})
    return {"result": f"Processed: {params}"}

# Register a resource handler
@router.resource("example/resource")
async def example_resource(message, websocket):
    return {"data": "This is example resource data"}

# Attach the router to the app
router.attach_to_app(app, "/ws")

# Run the server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```


### WebSocketClient

The `WebSocketClient` class provides methods for connecting to a FastMCP WebSocket server and interacting with it.

```python
client = WebSocketClient("ws://localhost:8000/ws")
await client.connect()
```

### WebSocketServer

The `WebSocketServer` class provides a decorator-based API for registering handlers for FastMCP messages.

```python
router = WebSocketServer()

@router.tool("example/tool")
async def example_tool(message, websocket):
    # Handle tool call
    return {"result": "success"}
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/thecodekitchen/mcpsock.git
cd mcpsock

# Install development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

## License

This project is licensed under the Apache 2.0 License - see the LICENSE file for details.