"""
Utility functions for the FastAPI MCP Client.
"""

import json
import uuid
from typing import Any, Dict, List, Optional, Union


def generate_request_id() -> str:
    """Generate a unique request ID for MCP."""
    return str(uuid.uuid4())


def parse_sse_line(line: str) -> Optional[Dict[str, str]]:
    """
    Parse a single SSE line into its components.
    
    Args:
        line: The SSE line to parse
        
    Returns:
        Dictionary with event fields or None if the line is empty or invalid
    """
    if not line or not line.strip():
        return None
    
    line = line.strip()
    if not line:
        return None
        
    if ":" not in line:
        return {"field": "message", "value": line}
        
    field, value = line.split(":", 1)
    if value.startswith(" "):
        value = value[1:]
        
    return {"field": field, "value": value}


def parse_json_data(data: str) -> Union[Dict[str, Any], List[Any], str]:
    """
    Parse JSON data, returning the original string if parsing fails.
    
    Args:
        data: String to parse as JSON
        
    Returns:
        Parsed JSON object or the original string if parsing fails
    """
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return data


def create_mcp_initialize_payload(request_id: str, client_info: Dict[str, str], protocol_version: str) -> Dict[str, Any]:
    """
    Create an MCP initialize payload.
    
    Args:
        request_id: Unique request ID
        client_info: Client information
        protocol_version: MCP protocol version
        
    Returns:
        Dictionary containing the initialize payload
    """
    return {
        "id": request_id,
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "traceId": generate_request_id(),
            "clientInfo": client_info,
            "protocolVersion": protocol_version,
            "capabilities": {}
        }
    }


def create_mcp_tool_call_payload(request_id: str, operation_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create an MCP tool call payload.
    
    Args:
        request_id: Unique request ID
        operation_id: The operation to call
        params: Parameters for the operation
        
    Returns:
        Dictionary containing the tool call payload
    """
    return {
        "id": request_id,
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": operation_id,
            "arguments": params or {}
        }
    } 