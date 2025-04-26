import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from mcpsock.server import FastMCPWebSocketRouter

@pytest.mark.asyncio
async def test_handle_websocket_with_traceback():
    """Test that the exception handling in handle_websocket works correctly."""
    # Create a router
    router = FastMCPWebSocketRouter()

    # Create a mock WebSocket
    mock_websocket = AsyncMock()

    # Set up the websocket to raise a general exception during accept
    # This will trigger the outer exception handler in handle_websocket
    mock_websocket.accept.side_effect = RuntimeError("Test exception for traceback")

    # Mock the logger to verify it's called
    with patch('mcpsock.server.logger') as mock_logger, patch('mcpsock.server.traceback.print_exc'):
        try:
            # The exception should be caught in handle_websocket, but we need to catch it here
            # because it's happening in the accept method which is called directly
            await router.handle_websocket(mock_websocket)
        except RuntimeError:
            # This is expected, the test is to verify the error is logged
            pass

        # Verify that the error was logged
        mock_logger.error.assert_any_call("Error handling WebSocket: Test exception for traceback")
