"""
Mock Arista eAPI server for testing.
"""
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import uvicorn
from typing import Dict, Any
import json

app = FastAPI()
security = HTTPBasic()

# Mock responses for eAPI commands
MOCK_RESPONSES = {
    "show clock": {
        "timeSource": "local",
        "clockTime": "2024-01-01T12:00:00Z",
        "uptime": 86400
    },
    "show hostname": {
        "hostname": "mock-switch-01"
    },
    "show interfaces status": {
        "interfaceStatuses": {
            "Ethernet1": {
                "interfaceStatus": "connected",
                "linkStatus": "up",
                "lineProtocolStatus": "up"
            },
            "Ethernet2": {
                "interfaceStatus": "notconnect",
                "linkStatus": "down",
                "lineProtocolStatus": "down"
            }
        }
    }
}


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> bool:
    """Verify basic auth credentials (accepts any for testing)."""
    return True


@app.post("/command-api")
async def command_api(request: Request, credentials: HTTPBasicCredentials = Depends(security)):
    """Mock eAPI command endpoint."""
    try:
        body = await request.json()
        
        # Verify it's an eAPI request
        if body.get("jsonrpc") != "2.0" or body.get("method") != "runCmds":
            raise HTTPException(status_code=400, detail="Invalid eAPI request")
        
        commands = body.get("params", {}).get("cmds", [])
        
        # Build response
        results = []
        for cmd in commands:
            if cmd in MOCK_RESPONSES:
                results.append(MOCK_RESPONSES[cmd])
            else:
                results.append({"error": f"Unknown command: {cmd}"})
        
        return {
            "jsonrpc": "2.0",
            "result": results,
            "id": body.get("id", "1")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def run_mock_server(port: int = 8443, host: str = "0.0.0.0"):
    """Run the mock eAPI server."""
    uvicorn.run(app, host=host, port=port, log_level="error")


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8443
    run_mock_server(port)
