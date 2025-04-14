"""
FastAPI MCP Client

A specialized client library for interacting with FastAPI services 
that implement the Model Context Protocol (MCP) over Server-Sent Events (SSE).
"""

from fastapi_mcp_client.client import MCPClient, MCPClientConfig
from fastapi_mcp_client.exceptions import MCPClientError, MCPConnectionError, MCPStreamError

__version__ = "0.1.0"

__all__ = [
    "MCPClient",
    "MCPClientConfig",
    "MCPClientError",
    "MCPConnectionError", 
    "MCPStreamError",
] 