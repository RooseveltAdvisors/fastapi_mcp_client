"""
Example for using FastAPI MCP Client with Server-Sent Events (SSE).

This example demonstrates how to connect to a FastAPI MCP server,
establish an SSE connection, and process streaming responses.

Usage:
    python -m fastapi_mcp_client.examples.sse_example
"""

import asyncio
import json
import os
import signal
import sys
from typing import Dict, Any

from fastapi_mcp_client import MCPClient, MCPClientConfig


async def handle_stream_event(event: Dict[str, Any]):
    """
    Process a stream event. This function demonstrates handling different event types
    that might be received from a FastAPI MCP server.
    
    Args:
        event: The event data from the stream
    """
    if "type" in event:
        # Handle typed events like those from search_documents
        if event["type"] == "partial_result":
            doc = event.get("document", {})
            print(f"\n🔍 Found document {event['result_number']}: {doc.get('title')}")
            print(f"   Similarity: {doc.get('similarity', 0.0):.4f}")
            print(f"   Snippet: {doc.get('snippet', '')}")
        elif event["type"] == "complete":
            print(f"\n✅ Search complete! Found {len(event.get('results', []))} results total.")
    elif "number" in event:
        # Handle events from generate_numbers
        print(f"📊 Generated number: {event['number']}")
    elif "message" in event:
        # Handle events from echo
        print(f"🔊 Echo response: {event['message']}")
    elif "status" in event:
        # Handle status updates
        print(f"📢 Status update: {event['status']} - {event.get('message', '')}")
    elif "result" in event:
        # Handle calculation results
        expr = event.get("expression", "")
        result = event.get("result", "")
        print(f"🧮 Calculation: {expr} = {result}")
    elif "id" in event and "jsonrpc" in event:
        # This is a JSON-RPC response from the MCP server
        if "result" in event:
            print(f"🟢 MCP Response: {json.dumps(event['result'], indent=2)}")
        elif "error" in event:
            print(f"🔴 MCP Error: {json.dumps(event['error'], indent=2)}")
    else:
        # Unknown event type - print full event
        print(f"\n🔄 Unknown event: {json.dumps(event, indent=2)}")


async def sse_example(api_url: str):
    """
    Demonstrate streaming client usage with custom configuration.
    
    Args:
        api_url: The URL of the MCP API
    """
    # Create custom configuration
    config = MCPClientConfig(
        base_url=api_url,
        timeout=60.0,
        log_level="DEBUG",
        client_info={
            "name": "FastAPI MCP Client Example",
            "version": "0.1.0"
        }
    )
    
    # Create client with custom configuration
    async with MCPClient(api_url, config=config) as client:
        print(f"Connecting to MCP API at: {api_url}")
        
        # Example 1: Simple echo tool
        print("\n==== EXAMPLE: Echo Tool ====")
        try:
            result = await client.call_operation("echo", {"message": "Hello, MCP!"})
            print(f"Echo result: {result}")
        except Exception as e:
            print(f"Echo operation failed: {e}")
            
        # Example 2: Streaming number generation
        print("\n==== EXAMPLE: Streaming Number Generation ====")
        try:
            stream = await client.call_operation(
                "generate_numbers", 
                {"count": 5},
                stream=True
            )
            
            print("Streaming generated numbers:")
            counter = 0
            async for event in stream:
                counter += 1
                await handle_stream_event(event)
            
            print(f"\nStream complete. Received {counter} events.")
        except Exception as e:
            print(f"Streaming number generation failed: {e}")

        # Example 3: Document search with streaming results
        print("\n==== EXAMPLE: Document Search ====")
        try:
            print("Searching for 'machine learning' with streaming results:")
            stream = await client.call_operation(
                "search_documents", 
                {"query": "machine learning", "top_k": 3},
                stream=True
            )
            
            counter = 0
            async for event in stream:
                counter += 1
                await handle_stream_event(event)
            
            print(f"\nSearch stream complete. Received {counter} events.")
        except Exception as e:
            print(f"Document search failed: {e}")
        
        # Example 4: Calculate expression
        print("\n==== EXAMPLE: Calculation ====")
        try:
            result = await client.call_operation("calculate", {"expression": "10 * (5 + 3)"})
            print(f"Calculation result: {result}")
        except Exception as e:
            print(f"Calculation failed: {e}")


def setup_signal_handlers():
    """Set up clean shutdown on CTRL+C."""
    
    def handle_sigint(*args):
        print("\nInterrupted by user. Shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, handle_sigint)


if __name__ == "__main__":
    # Set up signal handlers for clean termination
    setup_signal_handlers()
    
    # Get API URL from environment or use default
    api_url = os.environ.get("API_URL", "http://localhost:8888")
    
    # Give instructions for starting the example server
    print("=" * 70)
    print("FastAPI MCP Client SSE Example")
    print("=" * 70)
    print("This example connects to a FastAPI MCP server and demonstrates SSE streaming.")
    print("\nBefore running this example, make sure the example server is running:")
    print("  1. Install fastapi-mcp: uv add fastapi-mcp")
    print("  2. Run: uvicorn fastapi_mcp_client.examples.server.simple_server:app --reload")
    print("\nConnecting to server at:", api_url)
    print("(Set API_URL environment variable to change)")
    print("=" * 70)
    
    # Run the example
    asyncio.run(sse_example(api_url)) 