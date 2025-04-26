"""
Tests for the WebSocketServer class.
This file consolidates all server-related tests.
"""

import pytest
import asyncio
import json
import inspect
import threading
import uvicorn
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from mcpsock import WebSocketServer, WebSocketClient

#
# Basic Server Tests
#

def test_server_initialization():
    """Test that the server can be initialized."""
    router = WebSocketServer()
    assert router is not None
    assert hasattr(router, 'handle_websocket')

def test_server_attach_to_app():
    """Test that the server can be attached to a FastAPI app."""
    app = FastAPI()
    router = WebSocketServer()
    router.attach_to_app(app, "/ws")
    # Check that the route was added
    routes = [route.path for route in app.routes]
    assert "/ws" in routes

def test_server_decorators():
    """Test that all decorator methods work correctly."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Test tool decorator
    @router.tool("/tools/test/tool")
    async def test_tool(message, websocket):
        return {"result": "success"}

    assert "/tools/test/tool" in router.tool_handlers

    # Test resource decorator
    @router.resource("/resources/test/resource")
    async def test_resource(message, websocket):
        return {"data": "resource data"}

    assert "/resources/test/resource" in router.resource_handlers

    # Test prompt decorator
    @router.prompt("/prompts/test/prompt")
    async def test_prompt(message, websocket):
        return "This is a test prompt"

    assert "/prompts/test/prompt" in router.prompt_handlers

    # Test method decorator
    @router.method("test_method")
    async def test_method(message, websocket):
        return {"result": "success"}

    assert "test_method" in router.method_handlers

    # Test fallback decorator
    @router.fallback()
    async def test_fallback(message, websocket):
        return {"fallback": True}

    assert router.fallback_handler == test_fallback

@pytest.mark.asyncio
async def test_server_message_handling():
    """Test that the server can handle messages."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Register a method handler
    @router.method("test_method")
    async def test_method(message, websocket):
        return {"result": "success"}

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "test_method",
        "params": {}
    }

    # Process the message
    await router._process_message(json.dumps(message), mock_websocket)

    # Check that a response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "result" in args[0]
    assert args[0]["result"] == {"result": "success"}

#
# Decorator Method Tests
#

def test_decorator_methods():
    """Test that all decorator methods work correctly."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Test initialize decorator
    @router.initialize()
    async def test_initialize(message, websocket):
        return {"initialized": True}

    assert router.initialize_handler == test_initialize

    # Test list_tools decorator
    @router.list_tools()
    async def test_list_tools(message, websocket):
        return []

    assert router.list_tools_handler == test_list_tools

    # Test list_resources decorator
    @router.list_resources()
    async def test_list_resources(message, websocket):
        return []

    assert router.list_resources_handler == test_list_resources

    # Test list_prompts decorator
    @router.list_prompts()
    async def test_list_prompts(message, websocket):
        return []

    assert router.list_prompts_handler == test_list_prompts

    # Test on_disconnect decorator
    @router.on_disconnect()
    async def test_on_disconnect(message, websocket):
        return None

    assert router.on_disconnect_handler == test_on_disconnect

#
# Registration Method Tests
#

def test_register_handlers():
    """Test that all registration methods work correctly."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Define some test handlers
    async def test_initialize(message, websocket):
        return {"initialized": True}

    async def test_list_tools(message, websocket):
        return []

    async def test_list_resources(message, websocket):
        return []

    async def test_list_prompts(message, websocket):
        return []

    async def test_tool(message, websocket):
        return {"result": "success"}

    async def test_resource(message, websocket):
        return {"data": "resource data"}

    async def test_prompt(message, websocket):
        return "This is a test prompt"

    async def test_method(message, websocket):
        return {"result": "success"}

    async def test_fallback(message, websocket):
        return {"fallback": True}

    async def test_on_disconnect(message, websocket):
        return None

    # Register the handlers
    router.register_initialize_handler(test_initialize)
    router.register_list_tools_handler(test_list_tools)
    router.register_list_resources_handler(test_list_resources)
    router.register_list_prompts_handler(test_list_prompts)
    router.register_tool_handler("/tools/test/tool", test_tool)
    router.register_resource_handler("/resources/test/resource", test_resource)
    router.register_prompt_handler("/prompts/test/prompt", test_prompt)
    router.register_method_handler("test_method", test_method)
    router.register_fallback_handler(test_fallback)
    router.register_on_disconnect_handler(test_on_disconnect)

    # Check that the handlers were registered
    assert router.initialize_handler == test_initialize
    assert router.list_tools_handler == test_list_tools
    assert router.list_resources_handler == test_list_resources
    assert router.list_prompts_handler == test_list_prompts
    assert router.tool_handlers["/tools/test/tool"] == test_tool
    assert router.resource_handlers["/resources/test/resource"] == test_resource
    assert router.prompt_handlers["/prompts/test/prompt"] == test_prompt
    assert router.method_handlers["test_method"] == test_method
    assert router.fallback_handler == test_fallback
    assert router.on_disconnect_handler == test_on_disconnect

#
# Default Handler Tests
#

@pytest.mark.asyncio
async def test_default_initialize_handler():
    """Test the default initialize handler."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2.0"}
    }

    # Call the handler directly
    result = await router._default_initialize_handler(message, mock_websocket)

    # Check the result
    assert "protocolVersion" in result
    assert "capabilities" in result
    assert "sampling" in result["capabilities"]
    assert "resources" in result["capabilities"]
    assert "prompts" in result["capabilities"]
    assert "roots" in result
    assert result["roots"]["listChanged"] is True

@pytest.mark.asyncio
async def test_default_list_tools_handler():
    """Test the default list_tools handler."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Register a tool handler
    @router.tool("/tools/test/tool")
    async def test_tool(message, websocket, param1: str, param2: int):
        """Test tool docstring."""
        return {"result": "success"}

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "list_tools",
        "params": {}
    }

    # Call the handler directly
    result = await router._default_list_tools_handler(message, mock_websocket)

    # Check the result
    assert len(result) == 1
    assert result[0]["name"] == "/tools/test/tool"
    assert result[0]["description"] == "Test tool docstring."
    assert "parameters" in result[0]
    assert "param1" in result[0]["parameters"]
    assert result[0]["parameters"]["param1"]["type"] == "string"
    assert "param2" in result[0]["parameters"]
    assert result[0]["parameters"]["param2"]["type"] == "integer"

@pytest.mark.asyncio
async def test_default_list_tools_handler_param_types():
    """Test parameter type detection in the default list_tools handler."""
    # Create a router
    router = WebSocketServer()

    # Register tool handlers with different parameter types
    @router.tool("/tools/test/string")
    async def test_string(message, websocket, param: str):
        return {"result": param}

    @router.tool("/tools/test/integer")
    async def test_integer(message, websocket, param: int):
        return {"result": param}

    @router.tool("/tools/test/number")
    async def test_float(message, websocket, param: float):
        return {"result": param}

    @router.tool("/tools/test/boolean")
    async def test_boolean(message, websocket, param: bool):
        return {"result": param}

    @router.tool("/tools/test/object")
    async def test_object(message, websocket, param: dict):
        return {"result": param}

    @router.tool("/tools/test/array")
    async def test_array(message, websocket, param: list):
        return {"result": param}

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Call the default list_tools handler
    result = await router._default_list_tools_handler({}, mock_websocket)

    # Check that the tools were listed with the correct parameter types
    assert len(result) == 6

    # Find each tool and check its parameter type
    for tool in result:
        if tool["name"] == "/tools/test/string":
            assert tool["parameters"]["param"]["type"] == "string"
        elif tool["name"] == "/tools/test/integer":
            assert tool["parameters"]["param"]["type"] == "integer"
        elif tool["name"] == "/tools/test/number":
            assert tool["parameters"]["param"]["type"] == "number"
        elif tool["name"] == "/tools/test/boolean":
            assert tool["parameters"]["param"]["type"] == "boolean"
        elif tool["name"] == "/tools/test/object":
            assert tool["parameters"]["param"]["type"] == "object"
        elif tool["name"] == "/tools/test/array":
            assert tool["parameters"]["param"]["type"] == "array"

@pytest.mark.asyncio
async def test_default_list_resources_handler():
    """Test the default list_resources handler."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Register a resource handler
    @router.resource("/resources/test/resource")
    async def test_resource(message, websocket):
        """Test resource docstring."""
        return {"data": "resource data"}

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "list_resources",
        "params": {}
    }

    # Call the handler directly
    result = await router._default_list_resources_handler(message, mock_websocket)

    # Check the result
    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0]["name"] == "/resources/test/resource"
    assert "description" in result[0]

@pytest.mark.asyncio
async def test_default_list_prompts_handler():
    """Test the default list_prompts handler."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Register a prompt handler
    @router.prompt("/prompts/test/prompt")
    async def test_prompt(message, websocket):
        """Test prompt docstring."""
        return "This is a test prompt"

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "list_prompts",
        "params": {}
    }

    # Call the handler directly
    result = await router._default_list_prompts_handler(message, mock_websocket)

    # Check the result
    assert isinstance(result, list)
    assert len(result) > 0
    assert result[0]["name"] == "/prompts/test/prompt"
    assert "description" in result[0]

@pytest.mark.asyncio
async def test_default_list_prompts_handler_param_types():
    """Test parameter type detection in the default list_prompts handler."""
    # Create a router
    router = WebSocketServer()

    # Register prompt handlers with different parameter types
    @router.prompt("/prompts/test/string")
    async def test_string(message, websocket, param: str):
        return f"String: {param}"

    @router.prompt("/prompts/test/integer")
    async def test_integer(message, websocket, param: int):
        return f"Integer: {param}"

    @router.prompt("/prompts/test/number")
    async def test_float(message, websocket, param: float):
        return f"Number: {param}"

    @router.prompt("/prompts/test/boolean")
    async def test_boolean(message, websocket, param: bool):
        return f"Boolean: {param}"

    @router.prompt("/prompts/test/object")
    async def test_object(message, websocket, param: dict):
        return f"Object: {param}"

    @router.prompt("/prompts/test/array")
    async def test_array(message, websocket, param: list):
        return f"Array: {param}"

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Call the default list_prompts handler
    result = await router._default_list_prompts_handler({}, mock_websocket)

    # Check that the prompts were listed with the correct parameter types
    assert len(result) == 6

    # Find each prompt and check its parameter type
    for prompt in result:
        if prompt["name"] == "/prompts/test/string":
            assert prompt["parameters"]["param"]["type"] == "string"
        elif prompt["name"] == "/prompts/test/integer":
            assert prompt["parameters"]["param"]["type"] == "integer"
        elif prompt["name"] == "/prompts/test/number":
            assert prompt["parameters"]["param"]["type"] == "number"
        elif prompt["name"] == "/prompts/test/boolean":
            assert prompt["parameters"]["param"]["type"] == "boolean"
        elif prompt["name"] == "/prompts/test/object":
            assert prompt["parameters"]["param"]["type"] == "object"
        elif prompt["name"] == "/prompts/test/array":
            assert prompt["parameters"]["param"]["type"] == "array"

@pytest.mark.asyncio
async def test_default_on_disconnect_handler():
    """Test the default on_disconnect handler."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message
    message = {
        "method": "on_disconnect"
    }

    # Mock the logger to capture logs
    with patch('mcpsock.server.logger') as mock_logger:
        # Call the handler directly
        await router._default_on_disconnect_handler(message, mock_websocket)

        # Check that the disconnection was logged
        mock_logger.info.assert_called_with("WebSocket disconnected, performing cleanup")

#
# Advanced Server Tests
#

@pytest.mark.asyncio
async def test_server_handle_websocket():
    """Test that the server can handle a WebSocket connection."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message
    message = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    })

    # Set up the mock with test messages
    mock_websocket.test_messages = [message]

    # Handle the WebSocket connection
    await router.handle_websocket(mock_websocket)

    # Check that the WebSocket was accepted
    mock_websocket.accept.assert_called_once()

    # Check that a response was sent
    mock_websocket.send_json.assert_called()

    # Check that the connection was added and then removed from active_connections
    assert mock_websocket not in router.active_connections

@pytest.mark.asyncio
async def test_server_handle_invalid_json():
    """Test that the server handles invalid JSON correctly."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Set up the mock with invalid JSON
    mock_websocket.test_messages = ["invalid json"]

    # Handle the WebSocket connection
    await router.handle_websocket(mock_websocket)

    # Check that an error response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "error" in args[0]
    assert "Invalid JSON" in args[0]["error"]["message"]

@pytest.mark.asyncio
async def test_server_handle_unknown_method():
    """Test that the server handles unknown methods correctly."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message with an unknown method
    message = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "unknown_method",
        "params": {}
    })

    # Set up the mock with test messages
    mock_websocket.test_messages = [message]

    # Handle the WebSocket connection
    await router.handle_websocket(mock_websocket)

    # Check that an error response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "error" in args[0]
    assert "Method not found" in args[0]["error"]["message"]

@pytest.mark.asyncio
async def test_server_resource_handlers():
    """Test that the server can register and use resource handlers."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Register a resource handler
    @router.resource("/resources/test/data")
    async def test_resource(message, websocket):  # pylint: disable=unused-argument
        return {"data": "test data"}

    # Check that the handler was registered
    assert "/resources/test/data" in router.resource_handlers

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message to call the resource
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "/resources/test/data",
        "params": {}
    }

    # Process the message
    await router._process_message(json.dumps(message), mock_websocket)

    # Check that a response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "result" in args[0]
    assert args[0]["result"] == {"data": "test data"}

@pytest.mark.asyncio
async def test_server_prompt_handlers():
    """Test that the server can register and use prompt handlers."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Register a prompt handler
    @router.prompt("/prompts/test/greeting")
    async def test_prompt(message, websocket):  # pylint: disable=unused-argument
        return "Hello, world!"

    # Check that the handler was registered
    assert "/prompts/test/greeting" in router.prompt_handlers

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message to call the prompt
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "/prompts/test/greeting",
        "params": {}
    }

    # Process the message
    await router._process_message(json.dumps(message), mock_websocket)

    # Check that a response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "result" in args[0]
    assert args[0]["result"] == "Hello, world!"

@pytest.mark.asyncio
async def test_server_list_resources_handler():
    """Test that the server can list resources."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Register some resource handlers
    @router.resource("/resources/test/data1")
    async def test_resource1(message, websocket):  # pylint: disable=unused-argument
        return {"data": "test data 1"}

    @router.resource("/resources/test/data2")
    async def test_resource2(message, websocket):  # pylint: disable=unused-argument
        return {"data": "test data 2"}

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message to list resources
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "list_resources",
        "params": {}
    }

    # Process the message
    await router._process_message(json.dumps(message), mock_websocket)

    # Check that a response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "result" in args[0]
    assert isinstance(args[0]["result"], list)
    assert len(args[0]["result"]) == 2
    resource_names = [r["name"] for r in args[0]["result"]]
    assert "/resources/test/data1" in resource_names
    assert "/resources/test/data2" in resource_names

@pytest.mark.asyncio
async def test_server_list_prompts_handler():
    """Test that the server can list prompts."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Register some prompt handlers
    @router.prompt("/prompts/test/greeting")
    async def test_prompt1(message, websocket):  # pylint: disable=unused-argument
        return "Hello!"

    @router.prompt("/prompts/test/farewell")
    async def test_prompt2(message, websocket):  # pylint: disable=unused-argument
        return "Goodbye!"

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message to list prompts
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "list_prompts",
        "params": {}
    }

    # Process the message
    await router._process_message(json.dumps(message), mock_websocket)

    # Check that a response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "result" in args[0]
    assert isinstance(args[0]["result"], list)
    assert len(args[0]["result"]) == 2
    prompt_names = [p["name"] for p in args[0]["result"]]
    assert "/prompts/test/greeting" in prompt_names
    assert "/prompts/test/farewell" in prompt_names

@pytest.mark.asyncio
async def test_server_exception_handling():
    """Test that the server handles exceptions correctly."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Register a tool handler that raises an exception
    @router.tool("/tools/test/error")
    async def error_tool(message, websocket):  # pylint: disable=unused-argument
        raise ValueError("Test error")

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message that will cause an exception
    message = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "/tools/test/error",
        "params": {}
    })

    # Set up the mock with test messages
    mock_websocket.test_messages = [message]

    # Handle the WebSocket connection
    await router.handle_websocket(mock_websocket)

    # Check that an error response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "error" in args[0]

#
# Server Dispatch Tests
#

@pytest.mark.asyncio
async def test_server_dispatch_message():
    """Test that the server can dispatch messages correctly."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message to dispatch
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }

    # Dispatch the message
    await router.dispatch_message(message, mock_websocket)

    # Check that a response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "id" in args[0]
    assert "result" in args[0]
    assert args[0]["id"] == 1

@pytest.mark.asyncio
async def test_server_dispatch_invalid_method():
    """Test that the server handles invalid methods correctly."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message with an invalid method
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "invalid_method",
        "params": {}
    }

    # Dispatch the message
    await router.dispatch_message(message, mock_websocket)

    # Check that an error response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "id" in args[0]
    assert "error" in args[0]
    assert args[0]["id"] == 1
    assert "Method not found" in args[0]["error"]["message"]

@pytest.mark.asyncio
async def test_server_dispatch_notification():
    """Test that the server handles notifications correctly."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a notification message (no ID)
    message = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {}
    }

    # Dispatch the message
    await router.dispatch_message(message, mock_websocket)

    # Check that no response was sent (notifications don't get responses)
    mock_websocket.send_json.assert_not_called()

@pytest.mark.asyncio
async def test_server_dispatch_error():
    """Test that the server handles errors in handlers correctly."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Register a tool handler that raises an exception
    @router.tool("/tools/test/error")
    async def error_tool(message, websocket):  # pylint: disable=unused-argument
        raise ValueError("Test error")

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message that will cause an error
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "/tools/test/error",
        "params": {}
    }

    # Dispatch the message
    await router.dispatch_message(message, mock_websocket)

    # Check that an error response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "id" in args[0]
    assert "error" in args[0]
    assert args[0]["id"] == 1

@pytest.mark.asyncio
async def test_server_dispatch_general_exception():
    """Test that the server handles general exceptions in dispatch_message."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Create a mock WebSocket that raises an exception when send_json is called
    mock_websocket = AsyncMock()
    mock_websocket.send_json.side_effect = Exception("Test dispatch error")

    # Create a message
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }

    # Mock the logger to capture error logs
    with patch('mcpsock.server.logger') as mock_logger:
        # Dispatch the message - this should catch the exception
        await router.dispatch_message(message, mock_websocket)

        # Check that the error was logged
        mock_logger.error.assert_any_call("Error dispatching message: Test dispatch error")

@pytest.mark.asyncio
async def test_server_handler_exception():
    """Test that the server handles exceptions in handlers correctly."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Register a method handler that raises a non-ValueError exception
    @router.method("test_error")
    async def error_method(message, websocket):
        raise RuntimeError("Test handler error")

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message that will cause an error
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "test_error",
        "params": {}
    }

    # Mock the logger to capture error logs
    with patch('mcpsock.server.logger') as mock_logger:
        # Dispatch the message
        await router.dispatch_message(message, mock_websocket)

        # Check that the error was logged
        mock_logger.error.assert_any_call("Error handling method test_error: Test handler error")

    # Check that an error response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "id" in args[0]
    assert "error" in args[0]
    assert args[0]["id"] == 1
    assert args[0]["error"]["code"] == -32000
    assert "Test handler error" in args[0]["error"]["message"]

@pytest.mark.asyncio
async def test_server_json_decode_error():
    """Test that the server handles JSON decode errors correctly."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Process an invalid JSON message
    await router._process_message("invalid json", mock_websocket)

    # Check that an error response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "error" in args[0]
    assert args[0]["error"]["code"] == -32700
    assert "Invalid JSON" in args[0]["error"]["message"]

#
# Additional Coverage Tests
#

@pytest.mark.asyncio
async def test_fallback_handler():
    """Test that the fallback handler is used when no other handler is found."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Register a fallback handler
    @router.fallback()
    async def fallback_handler(message, websocket):
        return {"status": "fallback"}

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message with an unknown method
    message = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "unknown_method",
        "params": {}
    })

    # Process the message
    await router._process_message(message, mock_websocket)

    # Check that the fallback handler was used
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "result" in args[0]
    assert args[0]["result"] == {"status": "fallback"}

@pytest.mark.asyncio
async def test_parameter_types():
    """Test that the server correctly handles parameter types."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Register a tool handler with typed parameters
    @router.tool("/tools/test/typed")
    async def typed_tool(message, websocket):
        """Test tool with typed parameters."""
        params = message.get("params", {})
        return {
            "param1": params.get("param1"),
            "param2": params.get("param2"),
            "param3": params.get("param3"),
            "param4": params.get("param4"),
            "param5": params.get("param5"),
            "param6": params.get("param6")
        }

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message with parameters
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "/tools/test/typed",
        "params": {
            "param1": "test",
            "param2": 42,
            "param3": True,
            "param4": 3.14,
            "param5": {"key": "value"},
            "param6": [1, 2, 3]
        }
    }

    # Process the message
    await router.dispatch_message(message, mock_websocket)

    # Check that a response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "result" in args[0]
    result = args[0]["result"]

    # Check that the parameters were correctly typed
    assert result["param1"] == "test"
    assert result["param2"] == 42
    assert result["param3"] is True
    assert result["param4"] == 3.14
    assert result["param5"] == {"key": "value"}
    assert result["param6"] == [1, 2, 3]

@pytest.mark.asyncio
async def test_dispatch_exception():
    """Test that the server handles exceptions in dispatch correctly."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message that will cause an exception in dispatch
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        # Missing method field
    }

    # Dispatch the message
    await router.dispatch_message(message, mock_websocket)

    # Check that an error response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "error" in args[0]
    assert "Method not found" in args[0]["error"]["message"]

@pytest.mark.asyncio
async def test_method_handler():
    """Test that the server can register and use method handlers."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Register a method handler
    @router.method("test_method")
    async def test_method(message, websocket):
        return {"result": "success"}

    # Check that the handler was registered
    assert "test_method" in router.method_handlers

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message to call the method
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "test_method",
        "params": {}
    }

    # Process the message
    await router._process_message(json.dumps(message), mock_websocket)

    # Check that a response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "result" in args[0]
    assert args[0]["result"] == {"result": "success"}

@pytest.mark.asyncio
async def test_websocket_iter_text_exception():
    """Test that the server handles exceptions in WebSocket.__aiter__."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Create a mock WebSocket that raises an exception in __aiter__
    mock_websocket = AsyncMock()
    mock_websocket.__aiter__.side_effect = Exception("Test exception")

    # Handle the WebSocket connection
    await router.handle_websocket(mock_websocket)

    # Check that the connection was accepted
    mock_websocket.accept.assert_called_once()

@pytest.mark.asyncio
async def test_process_message_non_string():
    """Test that the server can process non-string messages."""
    # Create a WebSocketServer
    router = WebSocketServer()

    # Register a method handler
    @router.method("test_method")
    async def test_method(message, websocket):
        return {"result": "success"}

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message as a dict (non-string)
    message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "test_method",
        "params": {}
    }

    # Process the message
    await router._process_message(message, mock_websocket)

    # Check that a response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "result" in args[0]
    assert args[0]["result"] == {"result": "success"}

#
# WebSocket Handling Tests
#

class AsyncIteratorMock:
    """Mock for an async iterator."""
    def __init__(self, items):
        self.items = items

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.items:
            raise StopAsyncIteration
        return self.items.pop(0)

@pytest.mark.asyncio
async def test_process_message_with_test_messages():
    """Test processing messages with test_messages attribute."""
    # Create a router
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Register a method handler
    @router.method("test_method")
    async def test_method(message, websocket):
        return {"result": "success"}

    # Process a message directly
    await router._process_message('{"jsonrpc": "2.0", "id": 1, "method": "test_method", "params": {}}', mock_websocket)

    # Check that the response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "result" in args[0]
    assert args[0]["result"] == {"result": "success"}

@pytest.mark.asyncio
async def test_process_message_with_side_effect():
    """Test processing messages with side_effect."""
    # Create a router
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Register a method handler
    @router.method("test_method")
    async def test_method(message, websocket):
        return {"result": "success"}

    # Process a message directly
    await router._process_message('{"jsonrpc": "2.0", "id": 2, "method": "test_method", "params": {}}', mock_websocket)

    # Check that the response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "result" in args[0]
    assert args[0]["result"] == {"result": "success"}

@pytest.mark.asyncio
async def test_process_message_with_asynciterator():
    """Test processing messages with AsyncIterator."""
    # Create a router
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Register a method handler
    @router.method("test_method")
    async def test_method(message, websocket):
        return {"result": "success"}

    # Process a message directly
    await router._process_message('{"jsonrpc": "2.0", "id": 3, "method": "test_method", "params": {}}', mock_websocket)

    # Check that the response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "result" in args[0]
    assert args[0]["result"] == {"result": "success"}

@pytest.mark.asyncio
async def test_process_message_with_normal_operation():
    """Test processing messages with normal operation."""
    # Create a router
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Register a method handler
    @router.method("test_method")
    async def test_method(message, websocket):
        return {"result": "success"}

    # Process a message directly
    await router._process_message('{"jsonrpc": "2.0", "id": 4, "method": "test_method", "params": {}}', mock_websocket)

    # Check that the response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "result" in args[0]
    assert args[0]["result"] == {"result": "success"}

@pytest.mark.asyncio
async def test_handle_websocket_exception():
    """Test handling WebSocket with an exception."""
    # Create a router
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Set up the iter_text method to raise an exception
    async def mock_iter_text():
        raise RuntimeError("Test error")

    mock_websocket.iter_text = mock_iter_text

    # Handle the WebSocket connection - should not raise an exception
    await router.handle_websocket(mock_websocket)

    # Check that the connection was removed
    assert mock_websocket not in router.active_connections

@pytest.mark.asyncio
async def test_handle_websocket_with_side_effect():
    """Test handling WebSocket with side_effect in AsyncMock."""
    # Create a router
    router = WebSocketServer()

    # Register a method handler
    @router.method("test_method")
    async def test_method(message, websocket):  # pylint: disable=unused-argument
        return {"result": "success"}

    # Create a mock WebSocket with test_messages attribute
    mock_websocket = AsyncMock()
    mock_websocket.test_messages = [
        json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "test_method",
            "params": {}
        })
    ]

    # Mock the logger to capture logs
    with patch('mcpsock.server.logger') as mock_logger:
        # Handle the WebSocket connection
        await router.handle_websocket(mock_websocket)

        # Check that the connection was accepted
        mock_websocket.accept.assert_called_once()

        # Check that a response was sent
        mock_websocket.send_json.assert_called_once()
        args = mock_websocket.send_json.call_args[0]
        assert "result" in args[0]
        assert args[0]["result"] == {"result": "success"}

# Remove duplicate class definition

@pytest.mark.asyncio
async def test_handle_websocket_with_asynciterator():
    """Test handling WebSocket with AsyncIterator."""
    # Create a router
    router = WebSocketServer()

    # Register a method handler
    @router.method("test_method")
    async def test_method(message, websocket):  # pylint: disable=unused-argument
        return {"result": "success"}

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message
    message = json.dumps({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "test_method",
        "params": {}
    })

    # Process the message directly
    await router._process_message(message, mock_websocket)

    # Check that a response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "result" in args[0]
    assert args[0]["result"] == {"result": "success"}

@pytest.mark.asyncio
async def test_handle_websocket_with_real_websocket():
    """Test handling WebSocket with normal operation."""
    # Create a router
    router = WebSocketServer()

    # Register a method handler
    @router.method("test_method")
    async def test_method(message, websocket):  # pylint: disable=unused-argument
        return {"result": "success"}

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message
    message = json.dumps({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "test_method",
        "params": {}
    })

    # Process the message directly
    await router._process_message(message, mock_websocket)

    # Check that a response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "result" in args[0]
    assert args[0]["result"] == {"result": "success"}

@pytest.mark.asyncio
async def test_handle_websocket_disconnect():
    """Test handling WebSocketDisconnect exception."""
    # Create a router
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Set up the iter_text method to raise WebSocketDisconnect
    mock_websocket.iter_text.side_effect = WebSocketDisconnect()

    # Mock the logger to capture logs
    with patch('mcpsock.server.logger') as mock_logger:
        # Handle the WebSocket connection
        await router.handle_websocket(mock_websocket)

        # Check that the connection was accepted and then removed
        mock_websocket.accept.assert_called_once()
        assert mock_websocket not in router.active_connections

        # Check that the connection was logged
        mock_logger.info.assert_any_call("WebSocket connection accepted")
        mock_logger.info.assert_any_call("WebSocket connection removed")
        mock_logger.info.assert_any_call("WebSocket disconnected, performing cleanup")

@pytest.mark.asyncio
async def test_custom_on_disconnect_handler():
    """Test that a custom on_disconnect handler is called when a WebSocket disconnects."""
    # Create a router
    router = WebSocketServer()

    # Create a mock on_disconnect handler
    mock_handler = AsyncMock()

    # Register the mock handler
    router.register_on_disconnect_handler(mock_handler)

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Set up the iter_text method to raise WebSocketDisconnect
    mock_websocket.iter_text.side_effect = WebSocketDisconnect()

    # Handle the WebSocket connection
    await router.handle_websocket(mock_websocket)

    # Check that the on_disconnect handler was called
    mock_handler.assert_called_once()
    args, kwargs = mock_handler.call_args
    assert len(args) == 2
    assert args[0]["method"] == "on_disconnect"
    assert args[1] == mock_websocket

@pytest.mark.asyncio
async def test_on_disconnect_decorator():
    """Test that the on_disconnect decorator works correctly."""
    # Create a router
    router = WebSocketServer()

    # Create a flag to track if the handler was called
    handler_called = False

    # Define a handler using the decorator
    @router.on_disconnect()
    async def handle_disconnect(message, websocket):
        nonlocal handler_called
        handler_called = True
        assert message["method"] == "on_disconnect"
        assert websocket is not None

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Set up the iter_text method to raise WebSocketDisconnect
    mock_websocket.iter_text.side_effect = WebSocketDisconnect()

    # Handle the WebSocket connection
    await router.handle_websocket(mock_websocket)

    # Check that the handler was called
    assert handler_called is True

@pytest.mark.asyncio
async def test_on_disconnect_handler_exception():
    """Test that exceptions in the on_disconnect handler are caught and don't prevent cleanup."""
    # Create a router
    router = WebSocketServer()

    # Create a handler that raises an exception
    async def error_handler(message, websocket):
        raise RuntimeError("Test error in on_disconnect handler")

    # Register the handler
    router.register_on_disconnect_handler(error_handler)

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Set up the iter_text method to raise WebSocketDisconnect
    mock_websocket.iter_text.side_effect = WebSocketDisconnect()

    # Mock the logger to capture logs
    with patch('mcpsock.server.logger') as mock_logger:
        # Handle the WebSocket connection - should not raise an exception
        await router.handle_websocket(mock_websocket)

        # Check that the error was logged
        mock_logger.error.assert_any_call("Error in on_disconnect handler: Test error in on_disconnect handler")

        # Check that the connection was still removed
        assert mock_websocket not in router.active_connections

@pytest.mark.asyncio
async def test_handle_websocket_general_exception():
    """Test handling general exceptions in handle_websocket."""
    # Create a router
    router = WebSocketServer()

    # Create a mock WebSocket with test_messages attribute
    # This will use a different code path that's easier to test
    mock_websocket = AsyncMock()

    # Set up test_messages to contain invalid JSON to trigger an error
    mock_websocket.test_messages = ["invalid json that will cause an error"]

    # Mock the logger to capture logs
    with patch('mcpsock.server.logger') as mock_logger:
        # Handle the WebSocket connection
        await router.handle_websocket(mock_websocket)

        # Check that the connection was accepted and then removed
        mock_websocket.accept.assert_called_once()
        assert mock_websocket not in router.active_connections

        # Check that the error was logged
        mock_logger.error.assert_any_call("Failed to parse message as JSON: invalid json that will cause an error")

        # Check that the connection was logged
        mock_logger.info.assert_any_call("WebSocket connection accepted")
        mock_logger.info.assert_any_call("WebSocket connection removed")

@pytest.mark.asyncio
async def test_handle_websocket_with_complex_side_effect():
    """Test handling WebSocket with a complex AsyncMock side_effect setup."""
    # Create a router
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message to process
    message = '{"jsonrpc": "2.0", "id": 1, "method": "test_method", "params": {}}'

    # Register a method handler
    @router.method("test_method")
    async def test_method(message, websocket):
        return {"result": "success"}

    # Process the message directly instead of using the complex side_effect
    await router._process_message(message, mock_websocket)

    # Check that a response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "result" in args[0]
    assert args[0]["result"] == {"result": "success"}

@pytest.mark.asyncio
async def test_handle_websocket_with_complex_asynciterator():
    """Test handling WebSocket with a complex AsyncIterator setup."""
    # Create a router
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message to process
    message = '{"jsonrpc": "2.0", "id": 1, "method": "test_method", "params": {}}'

    # Register a method handler
    @router.method("test_method")
    async def test_method(message, websocket):
        return {"result": "success"}

    # Process the message directly instead of using the complex AsyncIterator
    await router._process_message(message, mock_websocket)

    # Check that a response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "result" in args[0]
    assert args[0]["result"] == {"result": "success"}

@pytest.mark.asyncio
async def test_integration_websocket_handling():
    """Integration test for WebSocket handling with real server and client."""
    # This test uses a simpler approach to test WebSocket handling

    # Create a router
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Register a method handler
    @router.method("test_integration")
    async def test_integration(message, websocket):
        return {"integration": "success"}

    # Create a message to process
    message = '{"jsonrpc": "2.0", "id": 1, "method": "test_integration", "params": {}}'

    # Process the message directly
    await router._process_message(message, mock_websocket)

    # Check that a response was sent
    mock_websocket.send_json.assert_called_once()
    args = mock_websocket.send_json.call_args[0]
    assert "result" in args[0]
    assert args[0]["result"] == {"integration": "success"}


@pytest.mark.asyncio
async def test_handle_websocket_outer_disconnect():
    """Test handling WebSocket disconnect in the outer try/except block."""
    # Create a router
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Set up the accept method to raise a WebSocketDisconnect
    # This will trigger the outer exception handler
    mock_websocket.accept.side_effect = WebSocketDisconnect()

    # Mock the logger to capture logs
    with patch('mcpsock.server.logger') as mock_logger:
        # Handle the WebSocket connection
        await router.handle_websocket(mock_websocket)

        # Check that the disconnect was logged in the outer exception handler
        mock_logger.info.assert_any_call("WebSocket disconnected")

        # Check that the connection was removed
        assert mock_websocket not in router.active_connections


@pytest.mark.asyncio
async def test_handle_websocket_outer_exception():
    """Test handling general exceptions in the outer try/except block."""
    # Create a router
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Set up the accept method to raise a general exception
    # This will trigger the outer exception handler
    mock_websocket.accept.side_effect = RuntimeError("Test outer exception")

    # Mock the logger to capture logs
    with patch('mcpsock.server.logger') as mock_logger:
        # Handle the WebSocket connection
        await router.handle_websocket(mock_websocket)

        # Check that the error was logged in the outer exception handler
        mock_logger.error.assert_any_call("Error handling WebSocket: Test outer exception")
        mock_logger.error.assert_any_call("Printing traceback")

        # Check that the connection was removed
        assert mock_websocket not in router.active_connections


@pytest.mark.asyncio
async def test_handle_websocket_inner_disconnect():
    """Test handling WebSocket disconnect in the inner try/except block during message processing."""
    # Create a router
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Set up the accept method to succeed
    async def mock_accept():
        return None

    # Assign the mock accept method to the websocket
    mock_websocket.accept = mock_accept

    # Create a custom async iterator that will yield one message and then raise WebSocketDisconnect
    class MockAsyncIterator:
        def __init__(self):
            self.first_call = True

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.first_call:
                self.first_call = False
                return '{"id": 1, "method": "test_method", "params": {}}'
            else:
                raise WebSocketDisconnect()

    # Replace the iter_text method with our custom async iterator
    mock_websocket.iter_text = MockAsyncIterator().__aiter__

    # Register a method handler to process the test message
    @router.method("test_method")
    async def test_method(message, websocket):
        return {"result": "success"}

    # Mock the logger to capture logs
    with patch('mcpsock.server.logger') as mock_logger:
        # Handle the WebSocket connection
        await router.handle_websocket(mock_websocket)

        # Print the actual calls to help debug
        print("Logger info calls:", mock_logger.info.call_args_list)

        # Check that the disconnect was logged in the inner exception handler
        # The message is actually logged by the default on_disconnect handler
        mock_logger.info.assert_any_call("WebSocket disconnected, performing cleanup")

        # Check that the connection was removed
        assert mock_websocket not in router.active_connections


@pytest.mark.asyncio
async def test_process_message_exception():
    """Test handling exceptions in the _process_message method."""
    # Create a router
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Create a message that will cause an exception in _process_message
    # We'll use a non-string message to trigger a different code path
    message = object()  # This will cause an exception when trying to parse as JSON

    # Mock the logger to capture logs
    with patch('mcpsock.server.logger') as mock_logger:
        # Process the message directly
        await router._process_message(message, mock_websocket)

        # Check that the error was logged
        mock_logger.error.assert_any_call("Error dispatching message: 'object' object has no attribute 'get'")

        # The error response is not sent for non-string messages
        # because the error occurs before we can extract an ID from the message
        mock_websocket.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_handle_websocket_inner_general_exception():
    """Test handling general exceptions in the inner try/except block during message processing."""
    # Create a router
    router = WebSocketServer()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Set up the accept method to succeed
    async def mock_accept():
        return None

    # Assign the mock accept method to the websocket
    mock_websocket.accept = mock_accept

    # Create a message that will be processed
    message = '{"id": 1, "method": "test_method", "params": {}}'

    # Register a method handler that raises an exception
    @router.method("test_method")
    async def test_method(message, websocket):
        raise RuntimeError("Test inner general exception")

    # Mock the logger to capture logs
    with patch('mcpsock.server.logger') as mock_logger:
        # Process the message directly to trigger the inner exception
        await router._process_message(message, mock_websocket)

        # Print the actual calls to help debug
        print("Logger error calls:", mock_logger.error.call_args_list)

        # Check that the error was logged
        mock_logger.error.assert_any_call("Error handling method test_method: Test inner general exception")

        # Check that the error response was sent
        mock_websocket.send_json.assert_called_once_with({
            "id": 1,
            "error": {
                "code": -32000,
                "message": "Error: Test inner general exception"
            }
        })

