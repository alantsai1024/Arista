"""
Arista eAPI client for device communication.
"""
import httpx
import json
from typing import Optional, Dict, Any
from app.utils.encryption import decrypt_password


async def test_connection(
    ip: str,
    port: int,
    username: str,
    password_enc: str,
    timeout: float = 5.0
) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Test connection to Arista device using eAPI.
    
    Calls 'show hostname' command to verify connectivity.
    
    Args:
        ip: Device IP address
        port: Device port (usually 443)
        username: Username for authentication
        password_enc: Encrypted password
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (success: bool, message: str, hostname: Optional[str])
    """
    try:
        # Decrypt password
        password = decrypt_password(password_enc)
        
        # Build eAPI URL
        base_url = f"https://{ip}:{port}"
        
        # eAPI command
        command = {
            "jsonrpc": "2.0",
            "method": "runCmds",
            "params": {
                "version": 1,
                "cmds": ["show hostname"],
                "format": "json"
            },
            "id": "1"
        }
        
        # Make request to eAPI
        async with httpx.AsyncClient(
            verify=False,  # For self-signed certs in dev
            timeout=timeout,
            auth=(username, password)
        ) as client:
            response = await client.post(
                f"{base_url}/command-api",
                json=command,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if "result" in data and len(data["result"]) > 0:
                    hostname = data["result"][0].get("hostname", "unknown")
                    return True, "Connection successful", hostname
                else:
                    return False, "Invalid response format", None
            else:
                error_msg = f"HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"].get("message", error_msg)
                except:
                    pass
                return False, error_msg, None
                
    except httpx.TimeoutException:
        return False, "Connection timeout", None
    except httpx.ConnectError:
        return False, "Connection refused or host unreachable", None
    except Exception as e:
        return False, f"Error: {str(e)}", None
