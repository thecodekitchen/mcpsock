"""
Standalone FastMCP Client

This client completely bypasses the FastMCP transport system and implements
direct WebSocket communication to ensure reliable interaction with the server.
"""

import asyncio
import json
import logging
import sys
import uuid
import websockets
from typing import Dict, Any, List, Optional, Union

# Setup enhanced logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("standalone_client")

class FastMCPTool:
    """Represents a tool available on the FastMCP server"""
    
    def __init__(self, name: str, description: str, parameters: Dict[str, Any], return_type: str):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.return_type = return_type
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FastMCPTool':
        """Create a tool from a dictionary representation"""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            parameters=data.get("parameters", {}),
            return_type=data.get("returnType", "object")
        )
        
    def __repr__(self) -> str:
        return f"<FastMCPTool name='{self.name}'>"

class FastMCPResource:
    """Represents a resource available on the FastMCP server"""
    
    def __init__(self, name: str, description: str, schema: Dict[str, Any], type_: str):
        self.name = name
        self.description = description
        self.schema = schema
        self.type = type_
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FastMCPResource':
        """Create a resource from a dictionary representation"""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            schema=data.get("schema", {}),
            type_=data.get("type", "string")
        )
        
    def __repr__(self) -> str:
        return f"<FastMCPResource name='{self.name}'>"

class FastMCPPrompt:
    """Represents a prompt available on the FastMCP server"""
    
    def __init__(self, name: str, description: str, parameters: Dict[str, Any], return_type: str):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.return_type = return_type
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FastMCPPrompt':
        """Create a prompt from a dictionary representation"""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            parameters=data.get("parameters", {}),
            return_type=data.get("returnType", "string")
        )
        
    def __repr__(self) -> str:
        return f"<FastMCPPrompt name='{self.name}'>"

class StandaloneClient:
    """
    A completely standalone FastMCP client that implements its own
    WebSocket communication layer.
    """
    
    def __init__(self, server_url: str):
        """Initialize with the server URL"""
        self.server_url = server_url
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.message_id = 0
        self.tools: List[FastMCPTool] = []
        self.resources: List[FastMCPResource] = []
        self.prompts: List[FastMCPPrompt] = []
        
    async def __aenter__(self):
        """Enter async context manager"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager"""
        await self.disconnect()
        
    async def connect(self):
        """Connect to the server and initialize"""
        logger.info(f"Connecting to server: {self.server_url}")
        
        # Connect to the WebSocket server
        self.websocket = await websockets.connect(self.server_url)
        logger.info("WebSocket connection established")
        
        # Initialize the connection
        await self.initialize()
        logger.info("Connection initialized")
        
    async def disconnect(self):
        """Disconnect from the server"""
        if self.websocket:
            logger.info("Disconnecting from server")
            await self.websocket.close()
            self.websocket = None
            logger.info("Disconnected from server")
            
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Send a request to the server and wait for the response.
        
        Args:
            method: The method to call
            params: The parameters to pass
            
        Returns:
            The result of the request
        """
        if not self.websocket:
            raise RuntimeError("Not connected to the server")
            
        # Increment message ID
        self.message_id += 1
        request_id = self.message_id
        
        # Create the request
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        # Send the request
        logger.info(f"Sending request: method={method}, id={request_id}")
        logger.debug(f"Request details: {json.dumps(request, indent=2)}")
        await self.websocket.send(json.dumps(request))
        
        # Wait for the response
        response_text = await self.websocket.recv()
        logger.debug(f"Received response: {response_text}")
        
        # Parse the response
        try:
            response = json.loads(response_text)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in response: {response_text}")
            raise ValueError(f"Invalid JSON in response")
            
        # Check if the response matches the request ID
        if "id" in response and response["id"] != request_id:
            logger.warning(f"Response ID {response['id']} does not match request ID {request_id}")
            
        # Check for errors
        if "error" in response:
            error = response["error"]
            error_msg = error.get("message", "Unknown error")
            error_code = error.get("code", -1)
            logger.error(f"Error response: {error_msg} (code: {error_code})")
            raise Exception(f"Error {error_code}: {error_msg}")
            
        # Return the result
        return response.get("result")
            
    async def initialize(self):
        """Initialize the connection with the server"""
        logger.info("Initializing connection")
        
        # Send initialize request
        result = await self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "clientInfo": {
                "name": "standalone-client",
                "version": "1.0.0"
            }
        })
        
        logger.info(f"Initialization result: {result}")
        return result
        
    async def list_tools(self) -> List[FastMCPTool]:
        """List available tools on the server"""
        logger.info("Listing available tools")
        
        # Send list_tools request
        result = await self.send_request("list_tools")
        
        # Parse tools
        tools = []
        for tool_data in result:
            tool = FastMCPTool.from_dict(tool_data)
            tools.append(tool)
            
        self.tools = tools
        logger.info(f"Found {len(tools)} tools")
        
        return tools
        
    async def list_resources(self) -> List[FastMCPResource]:
        """List available resources on the server"""
        logger.info("Listing available resources")
        
        # Send list_resources request
        result = await self.send_request("list_resources")
        
        # Parse resources
        resources = []
        for resource_data in result:
            resource = FastMCPResource.from_dict(resource_data)
            resources.append(resource)
            
        self.resources = resources
        logger.info(f"Found {len(resources)} resources")
        
        return resources
        
    async def list_prompts(self) -> List[FastMCPPrompt]:
        """List available prompts on the server"""
        logger.info("Listing available prompts")
        
        # Send list_prompts request
        result = await self.send_request("list_prompts")
        
        # Parse prompts
        prompts = []
        for prompt_data in result:
            prompt = FastMCPPrompt.from_dict(prompt_data)
            prompts.append(prompt)
            
        self.prompts = prompts
        logger.info(f"Found {len(prompts)} prompts")
        
        return prompts
        
    async def call_tool(self, tool_path: str, params: Dict[str, Any]) -> Any:
        """
        Call a tool on the server.
        
        Args:
            tool_path: The path of the tool to call
            params: The parameters to pass to the tool
            
        Returns:
            The result of the tool call
        """
        logger.info(f"Calling tool: {tool_path}")
        logger.debug(f"Tool parameters: {params}")
        
        # Send tool call request
        result = await self.send_request(tool_path, params)
        
        logger.info(f"Tool call completed")
        logger.debug(f"Tool result: {result}")
        
        return result
        
    async def get_resource(self, resource_path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Get a resource from the server.
        
        Args:
            resource_path: The path of the resource to get
            params: Optional parameters to customize the resource request
            
        Returns:
            The resource data
        """
        logger.info(f"Getting resource: {resource_path}")
        if params:
            logger.debug(f"Resource parameters: {params}")
        
        # Send resource get request
        result = await self.send_request(resource_path, params or {})
        
        logger.info(f"Resource retrieval completed")
        logger.debug(f"Resource data: {result}")
        
        return result
        
    async def call_prompt(self, prompt_path: str, params: Dict[str, Any]) -> str:
        """
        Call a prompt on the server.
        
        Args:
            prompt_path: The path of the prompt to call
            params: The parameters to pass to the prompt
            
        Returns:
            The generated prompt text
        """
        logger.info(f"Calling prompt: {prompt_path}")
        logger.debug(f"Prompt parameters: {params}")
        
        # Send prompt call request
        result = await self.send_request(prompt_path, params)
        
        logger.info(f"Prompt call completed")
        logger.debug(f"Prompt result: {result}")
        
        return result

