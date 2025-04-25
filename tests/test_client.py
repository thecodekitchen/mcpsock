"""
Tests for the WebSocketClient class.
This file consolidates all client-related tests.
"""

import pytest
import asyncio
import json
import websockets
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from mcpsock import WebSocketClient
from mcpsock.client import FastMCPTool, FastMCPResource, FastMCPPrompt

#
# Basic Client Tests
#

@pytest.mark.asyncio
async def test_client_connect(server):
    """Test that the client can connect to the server."""
    client = WebSocketClient(server)
    await client.connect()
    assert client.websocket is not None
    await client.disconnect()

@pytest.mark.asyncio
async def test_client_context_manager(server):
    """Test that the client works as a context manager."""
    async with WebSocketClient(server) as client:
        assert client.websocket is not None

@pytest.mark.asyncio
async def test_client_initialize(client):
    """Test that the client can initialize the connection."""
    # The initialize method is called automatically when connecting
    # We can verify that the connection is initialized by checking if
    # we can perform operations that require initialization
    result = await client.list_tools()
    assert isinstance(result, list)

@pytest.mark.asyncio
async def test_client_send_request(client):
    """Test that the client can send a request to the server."""
    # Send a simple request to list tools
    result = await client.send_request("list_tools")
    assert isinstance(result, list)

#
# Advanced Client Tests
#

@pytest.mark.asyncio
async def test_client_list_resources(client):
    """Test that the client can list resources."""
    resources = await client.list_resources()
    assert isinstance(resources, list)

@pytest.mark.asyncio
async def test_client_list_prompts(client):
    """Test that the client can list prompts."""
    prompts = await client.list_prompts()
    assert isinstance(prompts, list)

@pytest.mark.asyncio
async def test_client_get_resource(client):
    """Test that the client can get a resource."""
    resource = await client.get_resource("/resources/test/resource")
    assert resource == {"data": "resource data"}

@pytest.mark.asyncio
async def test_client_get_resource_with_params():
    """Test that the client can get a resource with parameters."""
    # Create a mock websocket
    mock_ws = AsyncMock()
    mock_ws.recv.return_value = json.dumps({
        "id": 1,
        "result": {"data": "resource data with params"}
    })

    # Create a client and replace its websocket with our mock
    client = WebSocketClient("ws://localhost:8000/ws")
    client.websocket = mock_ws
    client.message_id = 0  # Reset message ID

    # Mock the logger to capture all log calls
    with patch('mcpsock.client.logger') as mock_logger:
        # Get a resource with parameters
        params = {"filter": "test"}
        resource = await client.get_resource("/resources/test/resource", params)

        # Verify the result
        assert resource == {"data": "resource data with params"}

        # Check that all expected log messages were called
        mock_logger.info.assert_any_call('Getting resource: /resources/test/resource')
        mock_logger.debug.assert_any_call('Resource parameters: {\'filter\': \'test\'}')
        mock_logger.info.assert_any_call('Resource retrieval completed')
        mock_logger.debug.assert_any_call('Resource data: {\'data\': \'resource data with params\'}')

@pytest.mark.asyncio
async def test_client_call_prompt(client):
    """Test that the client can call a prompt."""
    result = await client.call_prompt("/prompts/test/prompt", {"param": "test"})
    assert "This is a test prompt with param: test" == result

@pytest.mark.asyncio
async def test_client_call_tool_with_params(client):
    """Test that the client can call a tool with parameters."""
    params = {"test": "value"}
    result = await client.call_tool("/tools/test/echo", params)
    assert result == {"echo": params}

#
# Client Class Tests
#

def test_fastmcp_tool_repr():
    """Test the string representation of FastMCPTool."""
    tool = FastMCPTool(
        name="test_tool",
        description="A test tool",
        parameters={},
        return_type="object"
    )

    # Test the __repr__ method
    repr_str = repr(tool)
    assert repr_str == "<FastMCPTool name='test_tool'>"

def test_fastmcp_resource_repr():
    """Test the string representation of FastMCPResource."""
    resource = FastMCPResource(
        name="test_resource",
        description="A test resource",
        schema={},
        type_="string"
    )

    # Test the __repr__ method
    repr_str = repr(resource)
    assert repr_str == "<FastMCPResource name='test_resource'>"

def test_fastmcp_prompt_repr():
    """Test the string representation of FastMCPPrompt."""
    prompt = FastMCPPrompt(
        name="test_prompt",
        description="A test prompt",
        parameters={},
        return_type="string"
    )

    # Test the __repr__ method
    repr_str = repr(prompt)
    assert repr_str == "<FastMCPPrompt name='test_prompt'>"

#
# Error Handling Tests
#

@pytest.mark.asyncio
async def test_client_error_handling():
    """Test that the client handles connection errors."""
    client = WebSocketClient("ws://localhost:9999/nonexistent")
    with pytest.raises(Exception):
        await client.connect()

@pytest.mark.asyncio
async def test_send_request_not_connected():
    """Test that send_request raises RuntimeError when not connected."""
    client = WebSocketClient("ws://localhost:8000/ws")
    # Don't connect the client
    with pytest.raises(RuntimeError) as excinfo:
        await client.send_request("test_method")
    assert "Not connected to the server" in str(excinfo.value)

@pytest.mark.asyncio
async def test_client_json_error():
    """Test that the client handles JSON errors correctly."""
    # Create a mock websocket that returns invalid JSON
    mock_ws = AsyncMock()
    mock_ws.recv.return_value = "invalid json"

    # Create a client and replace its websocket with our mock
    client = WebSocketClient("ws://localhost:8000/ws")
    client.websocket = mock_ws

    # Attempt to send a request should raise a ValueError
    with pytest.raises(ValueError):
        await client.send_request("test_method")

@pytest.mark.asyncio
async def test_client_response_id_mismatch():
    """Test that the client handles response ID mismatches correctly."""
    # Create a mock websocket that returns a response with a mismatched ID
    mock_ws = AsyncMock()
    mock_ws.recv.return_value = json.dumps({
        "id": 999,  # This doesn't match the request ID
        "result": "test result"
    })

    # Create a client and replace its websocket with our mock
    client = WebSocketClient("ws://localhost:8000/ws")
    client.websocket = mock_ws
    client.message_id = 0  # Reset message ID

    # Mock the logger to capture the warning
    with patch('mcpsock.client.logger') as mock_logger:
        # Send a request - this should log a warning but not fail
        result = await client.send_request("test_method")

        # Check that the warning was logged
        mock_logger.warning.assert_called_once_with("Response ID 999 does not match request ID 1")

    # Check that the result was still returned
    assert result == "test result"

    # Verify that the request was sent with ID 1
    call_args = mock_ws.send.call_args[0][0]
    sent_request = json.loads(call_args)
    assert sent_request["id"] == 1

@pytest.mark.asyncio
async def test_client_server_error():
    """Test that the client handles server errors correctly."""
    # Create a mock websocket that returns an error response
    mock_ws = AsyncMock()
    mock_ws.recv.return_value = json.dumps({
        "id": 1,
        "error": {
            "code": -32601,
            "message": "Method not found"
        }
    })

    # Create a client and replace its websocket with our mock
    client = WebSocketClient("ws://localhost:8000/ws")
    client.websocket = mock_ws
    client.message_id = 0  # Reset message ID

    # Attempt to send a request should raise an Exception
    with pytest.raises(Exception) as excinfo:
        await client.send_request("test_method")

    # Check that the error message is correct
    assert "Method not found" in str(excinfo.value)

#
# Logging Tests
#

@pytest.mark.asyncio
async def test_client_list_tools_logging():
    """Test that list_tools logs correctly."""
    # Create a mock websocket
    mock_ws = AsyncMock()
    mock_ws.recv.return_value = json.dumps({
        "id": 1,
        "result": [
            {
                "name": "test_tool",
                "description": "A test tool",
                "parameters": {},
                "returnType": "object"
            }
        ]
    })

    # Create a client and replace its websocket with our mock
    client = WebSocketClient("ws://localhost:8000/ws")
    client.websocket = mock_ws
    client.message_id = 0  # Reset message ID

    # Mock the logger
    with patch('mcpsock.client.logger') as mock_logger:
        # Call list_tools
        tools = await client.list_tools()

        # Check that the debug log was called
        mock_logger.debug.assert_any_call('Request details: {\n  "jsonrpc": "2.0",\n  "id": 1,\n  "method": "list_tools",\n  "params": {}\n}')
        mock_logger.info.assert_any_call('Found 1 tools')

@pytest.mark.asyncio
async def test_client_call_prompt_logging():
    """Test that call_prompt logs correctly."""
    # Create a mock websocket
    mock_ws = AsyncMock()
    mock_ws.recv.return_value = json.dumps({
        "id": 1,
        "result": "This is a test prompt result"
    })

    # Create a client and replace its websocket with our mock
    client = WebSocketClient("ws://localhost:8000/ws")
    client.websocket = mock_ws
    client.message_id = 0  # Reset message ID

    # Mock the logger
    with patch('mcpsock.client.logger') as mock_logger:
        # Call a prompt
        result = await client.call_prompt("/prompts/test", {"param": "value"})

        # Check that the debug logs were called
        mock_logger.debug.assert_any_call('Prompt parameters: {\'param\': \'value\'}')
        mock_logger.debug.assert_any_call('Prompt result: This is a test prompt result')
        mock_logger.info.assert_any_call('Prompt call completed')

@pytest.mark.asyncio
async def test_client_call_prompt_detailed():
    """Test that call_prompt handles all logging details."""
    # Create a mock websocket
    mock_ws = AsyncMock()
    mock_ws.recv.return_value = json.dumps({
        "id": 1,
        "result": "This is a test prompt result"
    })

    # Create a client and replace its websocket with our mock
    client = WebSocketClient("ws://localhost:8000/ws")
    client.websocket = mock_ws
    client.message_id = 0  # Reset message ID

    # Mock the logger to capture all log calls
    with patch('mcpsock.client.logger') as mock_logger:
        # Call a prompt
        prompt_result = await client.call_prompt("/prompts/test/detailed", {"param": "test_value"})

        # Verify the result
        assert prompt_result == "This is a test prompt result"

        # Check that all expected log messages were called
        mock_logger.info.assert_any_call('Calling prompt: /prompts/test/detailed')
        mock_logger.debug.assert_any_call('Prompt parameters: {\'param\': \'test_value\'}')
        mock_logger.info.assert_any_call('Prompt call completed')
        mock_logger.debug.assert_any_call('Prompt result: This is a test prompt result')

        # Verify the request was sent correctly
        call_args = mock_ws.send.call_args[0][0]
        sent_request = json.loads(call_args)
        assert sent_request["method"] == "/prompts/test/detailed"
        assert sent_request["params"] == {"param": "test_value"}
