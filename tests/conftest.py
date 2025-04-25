"""
Shared test fixtures for mcpsock tests.
"""

import asyncio
import pytest
import pytest_asyncio
from fastapi import FastAPI
from mcpsock import WebSocketServer, WebSocketClient
import uvicorn
import threading
import time

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def app():
    """Create a FastAPI app with a WebSocketServer attached."""
    app = FastAPI()
    router = WebSocketServer()
    router.attach_to_app(app, "/ws")
    return app, router

@pytest.fixture
def server(app):
    """Start a test server in a separate thread."""
    app_instance, _ = app

    # Create a server in a separate thread
    server_thread = threading.Thread(
        target=lambda: uvicorn.run(
            app_instance,
            host="127.0.0.1",
            port=8000,
            log_level="error"
        )
    )

    # Start the server
    server_thread.daemon = True
    server_thread.start()

    # Give the server time to start
    time.sleep(1)

    yield "ws://127.0.0.1:8000/ws"

    # No need to stop the server as it's in a daemon thread

@pytest_asyncio.fixture
async def client():
    """Create a WebSocketClient connected to the test server."""
    # Use a different port to avoid conflicts
    server_url = "ws://127.0.0.1:8001/ws"

    # Start a new server on a different port
    app = FastAPI()
    router = WebSocketServer()

    # Register test handlers for resources and prompts
    @router.resource("/resources/test/resource")
    async def test_resource(message, websocket):
        return {"data": "resource data"}

    @router.prompt("/prompts/test/prompt")
    async def test_prompt(message, websocket):
        params = message.get("params", {})
        return f"This is a test prompt with param: {params.get('param', 'none')}"

    @router.tool("/tools/test/echo")
    async def echo_tool(message, websocket):
        params = message.get("params", {})
        return {"echo": params}

    router.attach_to_app(app, "/ws")

    # Create a server in a separate thread
    server_thread = threading.Thread(
        target=lambda: uvicorn.run(
            app,
            host="127.0.0.1",
            port=8001,
            log_level="error"
        )
    )

    # Start the server
    server_thread.daemon = True
    server_thread.start()

    # Give the server time to start
    time.sleep(1)

    # Connect the client
    client = WebSocketClient(server_url)
    await client.connect()

    yield client

    # Disconnect the client
    await client.disconnect()
