"""
Collector service for polling Arista devices via eAPI.
"""
import httpx
from typing import Optional, Dict, Any, Tuple

from app.services.collector_profile import get_poll_commands as get_profile_poll_commands
from app.utils.encryption import decrypt_password


_POLL_COMMANDS = get_profile_poll_commands()


def get_poll_commands() -> list[str]:
    """Expose configured commands for tests and diagnostics."""
    return list(_POLL_COMMANDS)


async def poll_device(
    ip: str,
    port: int,
    username: str,
    password_enc: str,
    timeout: float = 5.0
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]], Optional[float]]:
    """
    Poll a device using configured eAPI command profile.
    
    Args:
        ip: Device IP address
        port: Device port (usually 443)
        username: Username for authentication
        password_enc: Encrypted password
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str], data: Optional[Dict], latency_ms: Optional[float])
        On success, data contains command results keyed by command
    """
    import time
    
    try:
        # Decrypt password
        password = decrypt_password(password_enc)
        
        # Build eAPI URL
        base_url = f"https://{ip}:{port}"
        
        commands = get_poll_commands()

        # eAPI command
        command = {
            "jsonrpc": "2.0",
            "method": "runCmds",
            "params": {
                "version": 1,
                "cmds": commands,
                "format": "json"
            },
            "id": "1"
        }
        
        # Make request and measure latency
        start_time = time.time()
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
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                if "result" in data and len(data["result"]) == len(commands):
                    # Parse results into dict
                    results = {}
                    for i, cmd in enumerate(commands):
                        results[cmd] = data["result"][i]
                    
                    return True, None, results, latency_ms
                else:
                    return False, "Invalid response format", None, latency_ms
            else:
                error_msg = f"HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"].get("message", error_msg)
                except:
                    pass
                return False, error_msg, None, latency_ms
                
    except httpx.TimeoutException:
        return False, "Connection timeout", None, None
    except httpx.ConnectError:
        return False, "Connection refused or host unreachable", None, None
    except Exception as e:
        return False, f"Error: {str(e)}", None, None


def calculate_backoff_delay(attempt: int, base_delay: int = 10, max_delay: int = 60) -> int:
    """
    Calculate exponential backoff delay.
    
    Args:
        attempt: Current attempt number (1-based)
        base_delay: Base delay in seconds (default 10)
        max_delay: Maximum delay in seconds (default 60)
        
    Returns:
        Delay in seconds: 10 -> 20 -> 40 -> 60 (capped)
    """
    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
    return delay
