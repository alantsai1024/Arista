"""
Validation utilities for device management.
"""
import ipaddress
from typing import Optional


def validate_ip_address(ip: str) -> bool:
    """
    Validate IP address format (IPv4 or IPv6).
    
    Args:
        ip: IP address string
        
    Returns:
        True if valid, False otherwise
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def validate_interval(interval: int) -> bool:
    """
    Validate polling interval (5-300 seconds).
    
    Args:
        interval: Polling interval in seconds
        
    Returns:
        True if valid, False otherwise
    """
    return 5 <= interval <= 300
