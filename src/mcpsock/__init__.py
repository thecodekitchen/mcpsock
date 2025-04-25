# Export the main classes for easy import
from .client import StandaloneClient as WebSocketClient
from .server import FastMCPWebSocketRouter as WebSocketServer

__all__ = ['WebSocketClient', 'WebSocketServer']
