"""
Exceptions for the FastAPI MCP Client.
"""

class MCPClientError(Exception):
    """Base exception for all MCP client errors."""
    pass


class MCPConnectionError(MCPClientError):
    """Exception raised when connection to MCP server fails."""
    pass


class MCPStreamError(MCPClientError):
    """Exception raised when stream operation fails."""
    pass 