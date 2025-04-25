"""
FastMCP WebSocket Router

A modular, extensible router for handling FastMCP WebSocket communications.
This package provides clean abstractions for routing FastMCP messages to handlers
and managing WebSocket connections.
"""

import asyncio
import inspect
import json
import logging
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, Type, Union

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

# Type definitions
Handler = Callable[[Dict[str, Any], WebSocket], Awaitable[Any]]
ToolDefinition = Dict[str, Any]
ResourceDefinition = Dict[str, Any]
PromptDefinition = Dict[str, Any]

# Setup logging
logger = logging.getLogger("fastmcp_websocket")


class MessageType(Enum):
    """Types of messages that can be processed by the router"""
    INITIALIZE = "initialize"
    LIST_TOOLS = "list_tools"
    LIST_RESOURCES = "list_resources"  # New: List available resources
    LIST_PROMPTS = "list_prompts"      # New: List available prompts
    TOOL_CALL = "tool_call"
    RESOURCE_CALL = "resource_call"    # New: Call to a resource
    PROMPT_CALL = "prompt_call"        # New: Call to a prompt
    METHOD_CALL = "method_call"
    NOTIFICATION = "notification"
    UNKNOWN = "unknown"


class FastMCPWebSocketRouter:
    """
    Router for handling FastMCP WebSocket communications.
    
    This class provides a structured way to route incoming WebSocket messages
    to the appropriate handlers, handle responses, and manage the WebSocket
    connection lifecycle.
    """
    
    def __init__(self):
        """Initialize the router with default handlers"""
        self.route_handlers: Dict[str, Handler] = {}
        self.tool_handlers: Dict[str, Handler] = {}
        self.resource_handlers: Dict[str, Handler] = {}  # New: Resource handlers
        self.prompt_handlers: Dict[str, Handler] = {}    # New: Prompt handlers
        self.method_handlers: Dict[str, Handler] = {}
        self.fallback_handler: Optional[Handler] = None
        self.initialize_handler: Optional[Handler] = None
        self.list_tools_handler: Optional[Handler] = None
        self.list_resources_handler: Optional[Handler] = None  # New: List resources handler
        self.list_prompts_handler: Optional[Handler] = None    # New: List prompts handler
        self.active_connections: Set[WebSocket] = set()
        
        # Register default handlers
        self.register_initialize_handler(self._default_initialize_handler)
        self.register_list_tools_handler(self._default_list_tools_handler)
        self.register_list_resources_handler(self._default_list_resources_handler)  # New
        self.register_list_prompts_handler(self._default_list_prompts_handler)      # New
    
    def register_initialize_handler(self, handler: Handler) -> None:
        """Register a handler for initialize requests"""
        self.initialize_handler = handler
    
    def register_list_tools_handler(self, handler: Handler) -> None:
        """Register a handler for list_tools requests"""
        self.list_tools_handler = handler
    
    def register_list_resources_handler(self, handler: Handler) -> None:
        """Register a handler for list_resources requests"""
        self.list_resources_handler = handler
    
    def register_list_prompts_handler(self, handler: Handler) -> None:
        """Register a handler for list_prompts requests"""
        self.list_prompts_handler = handler
    
    def register_tool_handler(self, tool_path: str, handler: Handler) -> None:
        """Register a handler for a specific tool path"""
        self.tool_handlers[tool_path] = handler
    
    def register_resource_handler(self, resource_path: str, handler: Handler) -> None:
        """Register a handler for a specific resource path"""
        self.resource_handlers[resource_path] = handler
    
    def register_prompt_handler(self, prompt_path: str, handler: Handler) -> None:
        """Register a handler for a specific prompt path"""
        self.prompt_handlers[prompt_path] = handler
    
    def register_method_handler(self, method_name: str, handler: Handler) -> None:
        """Register a handler for a specific method name"""
        self.method_handlers[method_name] = handler
    
    def register_fallback_handler(self, handler: Handler) -> None:
        """Register a fallback handler for unknown methods"""
        self.fallback_handler = handler
    
    def get_handler_for_message(self, message: Dict[str, Any]) -> tuple[Handler, MessageType]:
        """Get the appropriate handler for a message"""
        method = message.get("method", "")
        
        # Check for known system methods
        if method == "initialize" and self.initialize_handler:
            return self.initialize_handler, MessageType.INITIALIZE
        
        if method == "list_tools" and self.list_tools_handler:
            return self.list_tools_handler, MessageType.LIST_TOOLS
            
        if method == "list_resources" and self.list_resources_handler:
            return self.list_resources_handler, MessageType.LIST_RESOURCES
            
        if method == "list_prompts" and self.list_prompts_handler:
            return self.list_prompts_handler, MessageType.LIST_PROMPTS
        
        # Check for tool calls (methods starting with /tools/)
        if method.startswith("/tools/") and method in self.tool_handlers:
            return self.tool_handlers[method], MessageType.TOOL_CALL
            
        # Check for resource calls (methods starting with /resources/)
        if method.startswith("/resources/") and method in self.resource_handlers:
            return self.resource_handlers[method], MessageType.RESOURCE_CALL
            
        # Check for prompt calls (methods starting with /prompts/)
        if method.startswith("/prompts/") and method in self.prompt_handlers:
            return self.prompt_handlers[method], MessageType.PROMPT_CALL
        
        # Check for general method calls
        if method in self.method_handlers:
            return self.method_handlers[method], MessageType.METHOD_CALL
        
        # Use fallback handler if available
        if self.fallback_handler:
            return self.fallback_handler, MessageType.UNKNOWN
        
        # Default to raising an error
        raise ValueError(f"No handler registered for method: {method}")
    
    async def dispatch_message(self, message: Dict[str, Any], websocket: WebSocket) -> None:
        """Dispatch a message to the appropriate handler and send the response"""
        try:
            # Extract message information
            method = message.get("method", "")
            params = message.get("params", {})
            msg_id = message.get("id")
            
            logger.debug(f"Dispatching message: {method} (ID: {msg_id})")
            
            try:
                # Get the appropriate handler
                handler, msg_type = self.get_handler_for_message(message)
                
                # Call the handler and get the result
                result = await handler(message, websocket)
                
                # Only send a response if there was an ID (some messages may be notifications)
                if msg_id is not None:
                    response = {
                        "id": msg_id,
                        "result": result
                    }
                    logger.debug(f"Sending response for message ID: {msg_id}")
                    await websocket.send_json(response)
                    
            except ValueError as e:
                # Handle unknown methods
                logger.warning(f"Unknown method: {method}")
                if msg_id is not None:
                    error_response = {
                        "id": msg_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }
                    await websocket.send_json(error_response)
                    
            except Exception as e:
                # Handle other exceptions
                logger.error(f"Error handling method {method}: {str(e)}")
                if msg_id is not None:
                    error_response = {
                        "id": msg_id,
                        "error": {
                            "code": -32000,
                            "message": f"Error: {str(e)}"
                        }
                    }
                    await websocket.send_json(error_response)
                
        except Exception as e:
            # Handle dispatch errors
            logger.error(f"Error dispatching message: {str(e)}")
            import traceback
            traceback.print_exc()
    
    async def handle_websocket(self, websocket: WebSocket) -> None:
        """Handle a WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("WebSocket connection accepted")
        
        try:
            # Process client messages
            async for message in websocket.iter_text():
                logger.debug(f"Received message: {message}")
                
                try:
                    # Parse the message
                    data = json.loads(message)
                    await self.dispatch_message(data, websocket)
                    
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse message as JSON: {message}")
                    await websocket.send_json({
                        "error": {"message": "Invalid JSON"}
                    })
                    
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")
        except Exception as e:
            logger.error(f"Error handling WebSocket: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # Clean up
            self.active_connections.remove(websocket)
            logger.info("WebSocket connection removed")
    
    def attach_to_app(self, app: FastAPI, route: str = "/ws") -> None:
        """Attach the router to a FastAPI application"""
        
        @app.websocket(route)
        async def websocket_endpoint(websocket: WebSocket):
            await self.handle_websocket(websocket)
    
    # Default handlers
    
    async def _default_initialize_handler(self, message: Dict[str, Any], websocket: WebSocket) -> Dict[str, Any]:
        """Default handler for initialize requests"""
        logger.info("Handling initialize request")
        protocol_version = message.get("params", {}).get("protocolVersion", "2.0")
        return {
            "protocolVersion": protocol_version,
            "capabilities": {
                "sampling": {},
                "resources": {},  # Added resources capability
                "prompts": {}     # Added prompts capability
            },
            "roots": {"listChanged": True}
        }
    
    async def _default_list_tools_handler(self, message: Dict[str, Any], websocket: WebSocket) -> List[Dict[str, Any]]:
        """Default handler for list_tools requests"""
        logger.info("Handling list_tools request")
        
        # Get all tool handlers and extract their metadata
        tools = []
        for tool_path, handler in self.tool_handlers.items():
            # Try to get the docstring and signature
            doc = inspect.getdoc(handler) or ""
            sig = inspect.signature(handler)
            
            # Extract parameters
            parameters = {}
            for param_name, param in sig.parameters.items():
                if param_name == "message" or param_name == "websocket":
                    continue
                
                param_type = "string"  # Default type
                if param.annotation != inspect.Parameter.empty:
                    if param.annotation == str:
                        param_type = "string"
                    elif param.annotation == int:
                        param_type = "integer"
                    elif param.annotation == float:
                        param_type = "number"
                    elif param.annotation == bool:
                        param_type = "boolean"
                    elif param.annotation == dict:
                        param_type = "object"
                    elif param.annotation == list:
                        param_type = "array"
                
                parameters[param_name] = {
                    "type": param_type,
                    "description": ""  # Could parse from docstring in a more advanced implementation
                }
            
            # Create the tool definition
            tools.append({
                "name": tool_path,
                "description": doc,
                "parameters": parameters,
                "returnType": "object"  # Default return type
            })
        
        return tools
        
    async def _default_list_resources_handler(self, message: Dict[str, Any], websocket: WebSocket) -> List[Dict[str, Any]]:
        """Default handler for list_resources requests"""
        logger.info("Handling list_resources request")
        
        # Get all resource handlers and extract their metadata
        resources = []
        for resource_path, handler in self.resource_handlers.items():
            # Try to get the docstring
            doc = inspect.getdoc(handler) or ""
            
            # Create the resource definition
            resources.append({
                "name": resource_path,
                "description": doc,
                "schema": {},  # Resource schema could be defined more specifically
                "type": "string"  # Default resource type
            })
        
        return resources
        
    async def _default_list_prompts_handler(self, message: Dict[str, Any], websocket: WebSocket) -> List[Dict[str, Any]]:
        """Default handler for list_prompts requests"""
        logger.info("Handling list_prompts request")
        
        # Get all prompt handlers and extract their metadata
        prompts = []
        for prompt_path, handler in self.prompt_handlers.items():
            # Try to get the docstring and signature
            doc = inspect.getdoc(handler) or ""
            sig = inspect.signature(handler)
            
            # Extract parameters
            parameters = {}
            for param_name, param in sig.parameters.items():
                if param_name == "message" or param_name == "websocket":
                    continue
                
                param_type = "string"  # Default type
                if param.annotation != inspect.Parameter.empty:
                    if param.annotation == str:
                        param_type = "string"
                    elif param.annotation == int:
                        param_type = "integer"
                    elif param.annotation == float:
                        param_type = "number"
                    elif param.annotation == bool:
                        param_type = "boolean"
                    elif param.annotation == dict:
                        param_type = "object"
                    elif param.annotation == list:
                        param_type = "array"
                
                parameters[param_name] = {
                    "type": param_type,
                    "description": ""
                }
            
            # Create the prompt definition
            prompts.append({
                "name": prompt_path,
                "description": doc,
                "parameters": parameters,
                "returnType": "string"  # Default return type for prompts
            })
        
        return prompts


class DecoratorRouter(FastMCPWebSocketRouter):
    """
    A FastMCP WebSocket router that supports registration via decorators.
    
    This class extends the base router to provide decorator-based registration
    of handlers, similar to FastAPI's approach.
    """
    
    def initialize(self):
        """Decorator for registering initialize handlers"""
        def decorator(func: Handler):
            self.register_initialize_handler(func)
            return func
        return decorator
    
    def list_tools(self):
        """Decorator for registering list_tools handlers"""
        def decorator(func: Handler):
            self.register_list_tools_handler(func)
            return func
        return decorator
        
    def list_resources(self):
        """Decorator for registering list_resources handlers"""
        def decorator(func: Handler):
            self.register_list_resources_handler(func)
            return func
        return decorator
        
    def list_prompts(self):
        """Decorator for registering list_prompts handlers"""
        def decorator(func: Handler):
            self.register_list_prompts_handler(func)
            return func
        return decorator
    
    def tool(self, path: str):
        """Decorator for registering tool handlers"""
        def decorator(func: Handler):
            self.register_tool_handler(path, func)
            return func
        return decorator
        
    def resource(self, path: str):
        """Decorator for registering resource handlers"""
        def decorator(func: Handler):
            self.register_resource_handler(path, func)
            return func
        return decorator
        
    def prompt(self, path: str):
        """Decorator for registering prompt handlers"""
        def decorator(func: Handler):
            self.register_prompt_handler(path, func)
            return func
        return decorator
    
    def method(self, name: str):
        """Decorator for registering method handlers"""
        def decorator(func: Handler):
            self.register_method_handler(name, func)
            return func
        return decorator
    
    def fallback(self):
        """Decorator for registering fallback handlers"""
        def decorator(func: Handler):
            self.register_fallback_handler(func)
            return func
        return decorator

