"""
Tests for the connection tracking functionality in the WebSocketServer.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from mcpsock.server import ConnectionManager, DecoratorRouter as WebSocketServer


class TestConnectionManager:
    """Tests for the ConnectionManager class."""

    def test_init(self):
        """Test initialization of ConnectionManager."""
        manager = ConnectionManager()
        assert manager.connections == {}
        assert manager.connection_data == {}

    def test_add_connection(self):
        """Test adding a connection."""
        manager = ConnectionManager()
        mock_websocket = MagicMock()

        connection_id = manager.add_connection(mock_websocket)

        assert connection_id in manager.connections
        assert manager.connections[connection_id] == mock_websocket
        assert manager.connection_data[connection_id] == {}
        assert hasattr(mock_websocket, "connection_id")
        assert mock_websocket.connection_id == connection_id

    def test_remove_connection(self):
        """Test removing a connection."""
        manager = ConnectionManager()
        mock_websocket = MagicMock()

        connection_id = manager.add_connection(mock_websocket)
        manager.connection_data[connection_id]["test_key"] = "test_value"

        manager.remove_connection(connection_id)

        assert connection_id not in manager.connections
        assert connection_id not in manager.connection_data

    def test_remove_nonexistent_connection(self):
        """Test removing a connection that doesn't exist."""
        manager = ConnectionManager()
        manager.remove_connection("nonexistent_id")
        # Should not raise an exception

    def test_get_connection_data(self):
        """Test getting connection data."""
        manager = ConnectionManager()
        mock_websocket = MagicMock()

        connection_id = manager.add_connection(mock_websocket)
        manager.connection_data[connection_id]["test_key"] = "test_value"

        data = manager.get_connection_data(connection_id)

        assert data == {"test_key": "test_value"}

        # Test getting data for nonexistent connection
        assert manager.get_connection_data("nonexistent_id") == {}

    def test_set_connection_data(self):
        """Test setting connection data."""
        manager = ConnectionManager()
        mock_websocket = MagicMock()

        connection_id = manager.add_connection(mock_websocket)
        manager.set_connection_data(connection_id, "test_key", "test_value")

        assert manager.connection_data[connection_id]["test_key"] == "test_value"

        # Test setting data for nonexistent connection (should be a no-op)
        manager.set_connection_data("nonexistent_id", "test_key", "test_value")
        assert "nonexistent_id" not in manager.connection_data


class TestWebSocketServerConnectionTracking:
    """Tests for the connection tracking functionality in WebSocketServer."""

    def test_init_with_tracking_enabled(self):
        """Test initialization with connection tracking enabled."""
        router = WebSocketServer(enable_connection_tracking=True)
        assert router.enable_connection_tracking is True
        assert router.connection_manager is not None

    def test_init_with_tracking_disabled(self):
        """Test initialization with connection tracking disabled."""
        router = WebSocketServer(enable_connection_tracking=False)
        assert router.enable_connection_tracking is False
        assert router.connection_manager is None

    def test_get_connection_id(self):
        """Test getting a connection ID."""
        router = WebSocketServer(enable_connection_tracking=True)
        mock_websocket = MagicMock()

        # Ensure the mock doesn't have a connection_id attribute initially
        if hasattr(mock_websocket, 'connection_id'):
            delattr(mock_websocket, 'connection_id')

        # Test with no connection ID
        assert router.get_connection_id(mock_websocket) is None

        # Test with connection ID
        mock_websocket.connection_id = "test_id"
        assert router.get_connection_id(mock_websocket) == "test_id"

        # Test with tracking disabled
        router = WebSocketServer(enable_connection_tracking=False)
        assert router.get_connection_id(mock_websocket) is None

    def test_get_connection_data(self):
        """Test getting connection data."""
        router = WebSocketServer(enable_connection_tracking=True)
        mock_websocket = MagicMock()
        mock_websocket.connection_id = "test_id"

        # Mock the connection manager
        router.connection_manager.get_connection_data = MagicMock(
            return_value={"test_key": "test_value"}
        )

        # Test getting all data
        data = router.get_connection_data(mock_websocket)
        assert data == {"test_key": "test_value"}
        router.connection_manager.get_connection_data.assert_called_with("test_id")

        # Test getting specific key
        value = router.get_connection_data(mock_websocket, "test_key")
        assert value == "test_value"

        # Test with tracking disabled
        router = WebSocketServer(enable_connection_tracking=False)
        assert router.get_connection_data(mock_websocket) is None
        assert router.get_connection_data(mock_websocket, "test_key") is None

    def test_get_connection_data_no_connection_id(self):
        """Test getting connection data when there is no connection ID."""
        router = WebSocketServer(enable_connection_tracking=True)
        mock_websocket = MagicMock()

        # Ensure the mock doesn't have a connection_id attribute
        if hasattr(mock_websocket, 'connection_id'):
            delattr(mock_websocket, 'connection_id')

        # Test getting data with no connection ID
        data = router.get_connection_data(mock_websocket)
        assert data is None

        # Test getting specific key with no connection ID
        value = router.get_connection_data(mock_websocket, "test_key")
        assert value is None

    def test_set_connection_data(self):
        """Test setting connection data."""
        router = WebSocketServer(enable_connection_tracking=True)
        mock_websocket = MagicMock()
        mock_websocket.connection_id = "test_id"

        # Mock the connection manager
        router.connection_manager.set_connection_data = MagicMock()

        # Test setting data
        router.set_connection_data(mock_websocket, "test_key", "test_value")
        router.connection_manager.set_connection_data.assert_called_with(
            "test_id", "test_key", "test_value"
        )

        # Test with tracking disabled
        router = WebSocketServer(enable_connection_tracking=False)
        router.set_connection_data(mock_websocket, "test_key", "test_value")
        # Should be a no-op, no exception

    @pytest.mark.asyncio
    async def test_handle_websocket_with_tracking(self):
        """Test handling a WebSocket connection with tracking enabled."""
        router = WebSocketServer(enable_connection_tracking=True)
        mock_websocket = AsyncMock()

        # Mock the connection manager
        router.connection_manager.add_connection = MagicMock(return_value="test_id")
        router.connection_manager.remove_connection = MagicMock()

        # Set the connection_id on the websocket to match what add_connection would do
        mock_websocket.connection_id = "test_id"

        # Mock the receive_json method to return a message and then raise WebSocketDisconnect
        mock_websocket.receive_json.side_effect = [
            {"jsonrpc": "2.0", "id": 1, "method": "test_method", "params": {}},
            Exception("WebSocket disconnected")
        ]

        # Register a method handler
        @router.method("test_method")
        async def test_method(message, websocket):
            return {"result": "success"}

        # Register an on_disconnect handler
        disconnect_handler_called = False
        @router.on_disconnect()
        async def on_disconnect(message, websocket):
            nonlocal disconnect_handler_called
            disconnect_handler_called = True

        # Handle the WebSocket connection
        with patch('mcpsock.server.logger'):
            await router.handle_websocket(mock_websocket)

        # Check that the connection was tracked
        router.connection_manager.add_connection.assert_called_once_with(mock_websocket)

        # Check that the connection was removed
        router.connection_manager.remove_connection.assert_called_once_with("test_id")

        # Check that the disconnect handler was called
        assert disconnect_handler_called is True

    @pytest.mark.asyncio
    async def test_integration_with_connection_data(self):
        """Integration test for using connection data during a session."""
        router = WebSocketServer(enable_connection_tracking=True)
        mock_websocket = AsyncMock()

        # Set up the connection
        connection_id = router.connection_manager.add_connection(mock_websocket)
        setattr(mock_websocket, "connection_id", connection_id)

        # Register handlers that use connection data
        @router.method("store_data")
        async def store_data(message, websocket):
            data = message.get("params", {}).get("data")
            router.set_connection_data(websocket, "stored_data", data)
            return {"success": True}

        @router.method("retrieve_data")
        async def retrieve_data(message, websocket):
            data = router.get_connection_data(websocket, "stored_data")
            return {"data": data}

        # Process a message to store data
        store_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "store_data",
            "params": {"data": "test_value"}
        }
        await router._process_message(json.dumps(store_message), mock_websocket)

        # Check that the data was stored
        assert router.get_connection_data(mock_websocket, "stored_data") == "test_value"

        # Process a message to retrieve data
        retrieve_message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "retrieve_data",
            "params": {}
        }
        await router._process_message(json.dumps(retrieve_message), mock_websocket)

        # Check that the response contained the stored data
        # The actual response might not include the jsonrpc field, so we'll check just the id and result
        last_call_args = mock_websocket.send_json.call_args[0][0]
        assert last_call_args.get("id") == 2
        assert last_call_args.get("result", {}).get("data") == "test_value"

        # Clean up
        router.connection_manager.remove_connection(connection_id)

        # Check that the data was cleaned up
        assert connection_id not in router.connection_manager.connection_data