"""
Tests for the package's __init__.py file.
"""

import pytest
from mcpsock import WebSocketClient, WebSocketServer

def test_exports():
    """Test that the package exports the expected classes."""
    assert WebSocketClient is not None
    assert WebSocketServer is not None
    
    # Check that the classes have the expected methods
    assert hasattr(WebSocketClient, 'connect')
    assert hasattr(WebSocketClient, 'disconnect')
    assert hasattr(WebSocketClient, 'send_request')
    
    assert hasattr(WebSocketServer, 'attach_to_app')
    assert hasattr(WebSocketServer, 'handle_websocket')
    assert hasattr(WebSocketServer, 'tool')
    assert hasattr(WebSocketServer, 'resource')
    assert hasattr(WebSocketServer, 'prompt')
