"""
Main MCP client implementation for SSE streaming.
"""

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union

import httpx

from fastapi_mcp_client.config import MCPClientConfig
from fastapi_mcp_client.exceptions import MCPClientError, MCPConnectionError, MCPStreamError
from fastapi_mcp_client.utils import (
    create_mcp_initialize_payload,
    create_mcp_tool_call_payload,
    generate_request_id,
    parse_json_data,
    parse_sse_line,
)


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastapi_mcp_client")


class MCPClient:
    """
    Client for interacting with FastAPI MCP-enabled APIs via Server-Sent Events (SSE).
    
    This client specializes in streaming operations through the Model Context Protocol
    over SSE. It handles the complete MCP session lifecycle:
    
    1. Establishing the SSE connection
    2. Extracting the session ID
    3. Initializing the MCP session
    4. Making tool calls
    5. Processing streaming responses
    
    The client supports both streaming and non-streaming operations, but is
    primarily designed for streaming use cases.
    """
    
    def __init__(
        self, 
        base_url: str, 
        config: Optional[MCPClientConfig] = None,
        log_level: Optional[str] = None,
    ):
        """
        Initialize the MCP client.
        
        Args:
            base_url: Base URL of the API (e.g., 'http://localhost:8000')
            config: Configuration options for the client. If None, uses default settings
            log_level: Override the logging level (e.g., 'DEBUG', 'INFO')
        """
        # Set the client configuration
        self.config = config or MCPClientConfig(base_url=base_url)
        
        # Set logging level
        if log_level:
            logger.setLevel(getattr(logging, log_level))
        else:
            logger.setLevel(getattr(logging, self.config.log_level))
        
        # HTTP clients
        self._async_client = httpx.AsyncClient(
            base_url=self.config.base_url, 
            timeout=self.config.timeout
        )
        self._sync_client = httpx.Client(
            base_url=self.config.base_url, 
            timeout=self.config.timeout
        )
        
        # Flag to track if MCP is available
        self._mcp_available = True
        
        logger.debug(f"MCPClient initialized with base URL: {base_url}")
    
    async def close(self):
        """Close the HTTP clients."""
        await self._async_client.aclose()
        self._sync_client.close()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    def __enter__(self):
        """Sync context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self._sync_client.close()
        
    async def call_operation(
        self, 
        operation_id: str, 
        params: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ) -> Union[Dict[str, Any], AsyncIterator[Dict[str, Any]]]:
        """
        Call an operation via MCP.
        
        Args:
            operation_id: The operation to call
            params: Parameters for the operation
            stream: Whether to stream the response (via SSE)
            
        Returns:
            If stream=False, returns the operation result as a dictionary
            If stream=True, returns an async iterator yielding operation results
            
        Raises:
            MCPClientError: If the operation fails
        """
        if stream and self._mcp_available:
            try:
                # Return an async iterator for streaming results
                return self._stream_operation(operation_id, params)
            except Exception as e:
                logger.warning(f"MCP streaming failed: {e}")
                self._mcp_available = False
                # Fall back to non-streaming operation
        
        # Non-streaming operation or fallback
        result = await self._call_operation_direct(operation_id, params)
        
        # Return a single-item async iterator if streaming was requested
        if stream:
            async def _single_result_iterator():
                yield result
            return _single_result_iterator()
        
        return result
    
    async def _stream_operation(
        self, 
        operation_id: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream operation results via MCP/SSE.
        
        Args:
            operation_id: The operation to call
            params: Parameters for the operation
            
        Returns:
            An async iterator yielding operation results
            
        Raises:
            MCPConnectionError: If connection to MCP server fails
            MCPStreamError: If streaming operation fails
        """
        # Generate request IDs
        request_id_initialize = generate_request_id()
        request_id_tool_call = generate_request_id()
        
        # Create payloads
        initialize_payload = create_mcp_initialize_payload(
            request_id_initialize, 
            self.config.client_info,
            self.config.protocol_version
        )
        
        tool_call_payload = create_mcp_tool_call_payload(
            request_id_tool_call,
            operation_id,
            params
        )
        
        # Event tracking
        session_id = None
        message_queue = asyncio.Queue()
        session_id_found = asyncio.Event()
        
        try:
            # Establish SSE connection
            logger.debug(f"Establishing SSE connection to {self.config.full_connection_url}")
            
            async with self._async_client.stream(
                "GET", 
                self.config.connection_path, 
                headers={"Accept": "text/event-stream", **self.config.default_headers}
            ) as response:
                if response.status_code != 200:
                    raise MCPConnectionError(f"Failed to connect to MCP server: {response.status_code}")
                
                # Start a background task to read from the SSE stream
                async def read_sse_stream():
                    nonlocal session_id
                    first_data_event = True
                    buffer = ""
                    
                    try:
                        async for line in response.aiter_lines():
                            line = line.strip()
                            
                            # Empty line marks the end of an event
                            if not line:
                                if buffer:
                                    event_data = buffer
                                    buffer = ""
                                    
                                    # Check for session ID in the first event
                                    if first_data_event:
                                        first_data_event = False
                                        
                                        # Check for session_id in URL format
                                        if event_data.startswith(self.config.messages_path):
                                            try:
                                                # Extract session_id from query string
                                                if "?session_id=" in event_data:
                                                    session_id = event_data.split("?session_id=")[1].split("&")[0]
                                                    logger.debug(f"Found session_id in event data: {session_id}")
                                                    session_id_found.set()
                                                    continue
                                            except Exception as e:
                                                logger.warning(f"Error extracting session_id from event data: {e}")
                                    
                                    # Process the event data
                                    try:
                                        message = parse_json_data(event_data)
                                        
                                        # Check for session_id in message
                                        if isinstance(message, dict) and not session_id:
                                            if "session_id" in message:
                                                session_id = message["session_id"]
                                                logger.debug(f"Found session_id in message: {session_id}")
                                                session_id_found.set()
                                            
                                        await message_queue.put(message)
                                    except Exception as e:
                                        logger.warning(f"Error processing event data: {e}")
                                        await message_queue.put({"error": str(e)})
                                
                                continue
                                
                            # Parse SSE line
                            parsed = parse_sse_line(line)
                            if not parsed:
                                continue
                                
                            # Check for session_id in "id:" field
                            if parsed["field"] == "id" and not session_id:
                                session_id = parsed["value"]
                                logger.debug(f"Found session_id in id field: {session_id}")
                                session_id_found.set()
                            
                            # Accumulate data fields
                            if parsed["field"] == "data":
                                buffer += parsed["value"]
                    
                    except Exception as e:
                        logger.error(f"Error reading SSE stream: {e}")
                        await message_queue.put({"error": f"SSE stream error: {str(e)}"})
                    finally:
                        # Signal end of stream
                        await message_queue.put(None)
                        # Ensure session_id_found is set to avoid blocking
                        if not session_id_found.is_set():
                            session_id_found.set()
                
                # Start the reader task
                reader_task = asyncio.create_task(read_sse_stream())
                
                # Wait for session ID with timeout
                try:
                    await asyncio.wait_for(session_id_found.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    raise MCPConnectionError("Timeout waiting for session ID")
                
                if not session_id:
                    # Check header as last resort
                    session_id = response.headers.get("X-MCP-Session-ID")
                    if not session_id:
                        raise MCPConnectionError("Failed to obtain session ID")
                
                # Send initialize request
                messages_url = f"{self.config.full_messages_url}?session_id={session_id}"
                logger.debug(f"Sending initialize request to {messages_url}")
                
                init_response = await self._async_client.post(
                    messages_url,
                    json=initialize_payload,
                    headers={"Content-Type": "application/json", **self.config.default_headers}
                )
                init_response.raise_for_status()
                
                # Send tool call request
                logger.debug(f"Sending tool call request to {messages_url}")
                tool_call_response = await self._async_client.post(
                    messages_url,
                    json=tool_call_payload,
                    headers={"Content-Type": "application/json", **self.config.default_headers}
                )
                tool_call_response.raise_for_status()
                
                # Yield messages from the queue
                while True:
                    message = await message_queue.get()
                    if message is None:  # End of stream
                        break
                    if "error" in message:
                        raise MCPStreamError(message["error"])
                    yield message
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during MCP operation: {e}")
            raise MCPConnectionError(f"HTTP error: {e.response.status_code}")
        except (httpx.RequestError, asyncio.TimeoutError) as e:
            logger.error(f"Connection error during MCP operation: {e}")
            raise MCPConnectionError(f"Connection error: {str(e)}")
        except Exception as e:
            logger.error(f"Error during MCP operation: {e}")
            raise MCPClientError(f"MCP operation failed: {str(e)}")
    
    async def _call_operation_direct(
        self, 
        operation_id: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Call an operation directly via HTTP (non-streaming).
        
        Args:
            operation_id: The operation to call
            params: Parameters for the operation
            
        Returns:
            The operation result as a dictionary
            
        Raises:
            MCPClientError: If the operation fails
        """
        try:
            # Determine the HTTP method, path, and data transformation for the operation
            method, path, data = self._get_operation_details(operation_id, params)
            
            logger.debug(f"Calling operation {operation_id} via HTTP {method} to {path}")
            
            # Make the HTTP request
            response = await self._async_client.request(
                method, 
                path, 
                json=data if method in ("POST", "PUT", "PATCH") else None,
                params=data if method in ("GET", "DELETE") else None,
                headers=self.config.default_headers
            )
            response.raise_for_status()
            
            # Parse the response
            if response.status_code == 204:  # No Content
                return {}
            
            try:
                return response.json()
            except json.JSONDecodeError:
                logger.warning(f"Response is not valid JSON: {response.text}")
                return {"text": response.text}
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during {operation_id} operation: {e}")
            error_msg = f"HTTP error: {e.response.status_code}"
            try:
                error_details = e.response.json()
                if "detail" in error_details:
                    error_msg = f"HTTP error: {e.response.status_code} - {error_details['detail']}"
            except Exception:
                pass
            
            raise MCPClientError(error_msg)
        except Exception as e:
            logger.error(f"Error during {operation_id} operation: {e}")
            raise MCPClientError(f"Operation {operation_id} failed: {str(e)}")
    
    def _get_operation_details(
        self, 
        operation_id: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> tuple[str, str, Optional[Dict[str, Any]]]:
        """
        Get the HTTP method, path, and transformed parameters for an operation.
        
        Args:
            operation_id: The operation to call
            params: Parameters for the operation
            
        Returns:
            Tuple of (HTTP method, path, transformed parameters)
            
        Raises:
            MCPClientError: If the operation is unknown
        """
        # This method maps operation IDs to HTTP endpoints
        # It can be extended with more operations as needed
        
        operation_details = {
            # Example mapping for some common operations
            "health_check": ("GET", "/health", None),
            "ground_query": ("POST", "/ground", None),
            "ingest_content": ("POST", "/ingest", None),
        }
        
        # Allow custom operations to be specified directly
        if ":" in operation_id:
            parts = operation_id.split(":", 1)
            if len(parts) == 2:
                method, path = parts
                return method.upper(), path, params
        
        # Check if operation is in the predefined mappings
        if operation_id in operation_details:
            method, path, param_transform = operation_details[operation_id]
            
            # Transform parameters if a transform function is provided
            transformed_params = params
            if param_transform is not None and params is not None:
                transformed_params = param_transform(params)
            
            return method, path, transformed_params
        
        # Default to a direct API call
        # This assumes the operation_id maps directly to an API endpoint
        return "POST", f"/{operation_id}", params 