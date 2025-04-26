from fastapi import FastAPI
from mcpsock import WebSocketServer
import uvicorn

# Create a FastAPI app
app = FastAPI()

# Create a WebSocketServer with connection tracking enabled
router = WebSocketServer(enable_connection_tracking=True)

# Register an initialize handler that stores user info
@router.initialize()
async def handle_initialize(message, websocket):
    # Store user info from the initialize request
    params = message.get("params", {})
    user_info = params.get("clientInfo", {})
    
    # Store the user info in the connection data
    router.set_connection_data(websocket, "user_info", user_info)
    
    # Return standard initialize response
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "sampling": {},
            "resources": {},
            "prompts": {}
        },
        "roots": {"listChanged": True}
    }

# Register a tool that uses the stored user info
@router.tool("user/info")
async def get_user_info(message, websocket):
    # Get the user info from the connection data
    user_info = router.get_connection_data(websocket, "user_info")
    
    return {
        "user_info": user_info,
        "connection_id": router.get_connection_id(websocket)
    }

# Register a disconnect handler to clean up
@router.on_disconnect()
async def handle_disconnect(message, websocket):
    # Log the disconnection with the connection ID
    connection_id = router.get_connection_id(websocket)
    print(f"Connection {connection_id} disconnected")
    
    # Any additional cleanup can be done here
    # The connection data will be automatically removed

# Attach the router to the app
router.attach_to_app(app, "/ws")

# Run the server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)