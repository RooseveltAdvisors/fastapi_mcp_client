"""
Unit tests for the MCPClient class.
"""

import json
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
import httpx
import respx
from fastapi_mcp_client import MCPClient, MCPClientConfig
from fastapi_mcp_client.exceptions import MCPClientError, MCPConnectionError


@pytest.fixture
def client():
    """Fixture that returns an MCPClient instance."""
    return MCPClient("http://localhost:8000")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_client_initialization():
    """Test that the client initializes correctly."""
    client = MCPClient("http://example.com")
    assert client.config.base_url == "http://example.com"
    assert client._mcp_available is True
    await client.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_context_manager():
    """Test that the client works as a context manager."""
    async with MCPClient("http://example.com") as client:
        assert client._mcp_available is True


@pytest.mark.unit
@pytest.mark.asyncio
@respx.mock
async def test_call_operation_direct(client):
    """Test direct API call without streaming."""
    respx.post("http://localhost:8000/ground").mock(
        return_value=httpx.Response(
            200,
            json={
                "context": [
                    {
                        "id": "1",
                        "source": "test",
                        "text": "This is a test",
                        "similarity": 0.95
                    }
                ]
            }
        )
    )
    
    result = await client._call_operation_direct("ground_query", {"query": "test", "top_k": 1})
    
    assert "context" in result
    assert len(result["context"]) == 1
    assert result["context"][0]["similarity"] == 0.95
    await client.close()


@pytest.mark.unit
@pytest.mark.asyncio
@respx.mock
async def test_call_operation_http_error(client):
    """Test HTTP error handling in direct API call."""
    respx.post("http://localhost:8000/ground").mock(
        return_value=httpx.Response(
            404,
            json={"detail": "Not found"}
        )
    )
    
    with pytest.raises(MCPClientError) as excinfo:
        await client._call_operation_direct("ground_query", {"query": "test", "top_k": 1})
    
    assert "HTTP error: 404" in str(excinfo.value)
    await client.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_operation_details(client):
    """Test mapping operation IDs to HTTP details."""
    # Test a predefined operation
    method, path, params = client._get_operation_details("ground_query", {"query": "test"})
    assert method == "POST"
    assert path == "/ground"
    assert params == {"query": "test"}
    
    # Test custom operation format
    method, path, params = client._get_operation_details("GET:/custom/path", {"param": "value"})
    assert method == "GET"
    assert path == "/custom/path"
    assert params == {"param": "value"}
    
    # Test fallback
    method, path, params = client._get_operation_details("unknown_operation", {"param": "value"})
    assert method == "POST"
    assert path == "/unknown_operation"
    assert params == {"param": "value"}
    
    await client.close() 