"""
Configuration for the FastAPI MCP Client.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class MCPClientConfig:
    """Configuration for the MCP client."""
    
    base_url: str
    """Base URL of the MCP API (e.g., 'http://localhost:8000')."""
    
    connection_path: str = "/mcp"
    """Path for establishing MCP SSE connection."""
    
    messages_path: str = "/mcp/messages/"
    """Path for sending MCP messages."""
    
    timeout: float = 30.0
    """Default timeout for HTTP requests in seconds."""
    
    default_headers: Dict[str, str] = field(default_factory=dict)
    """Default headers to include in all requests."""
    
    client_info: Dict[str, str] = field(default_factory=lambda: {
        "name": "FastAPI MCP Client",
        "version": "0.1.0"
    })
    """Client information to send in MCP initialize requests."""
    
    protocol_version: str = "0.1.0"
    """MCP protocol version."""
    
    max_retries: int = 3
    """Maximum number of retry attempts for failed requests."""
    
    retry_delay: float = 1.0
    """Delay between retry attempts in seconds."""
    
    log_level: str = "INFO"
    """Logging level for the client."""
    
    @property
    def full_connection_url(self) -> str:
        """Return the full URL for MCP connection."""
        return f"{self.base_url.rstrip('/')}{self.connection_path}"
    
    @property
    def full_messages_url(self) -> str:
        """Return the base URL for MCP messages (without session ID)."""
        return f"{self.base_url.rstrip('/')}{self.messages_path}" 