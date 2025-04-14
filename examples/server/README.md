# FastAPI MCP Server Example

This directory contains an example FastAPI server that implements the Model Context Protocol (MCP) for use with the FastAPI MCP Client.

## Overview

The `simple_server.py` example demonstrates how to:

1. Create a FastAPI application with MCP support
2. Define both regular and streaming tools
3. Handle different types of requests and responses
4. Implement proper error handling

## Running the Server

To run the example server:

```bash
# Install dependencies
uv add fastapi-mcp fastapi uvicorn

# Run the server
uvicorn fastapi_mcp_client.examples.server.simple_server:app --reload
```

The server will run on `http://localhost:8000` by default.

## Available Tools

The example server implements several tools that demonstrate different MCP features:

### Echo

A simple tool that echoes back a message:

```python
@mcp_router.tool()
async def echo(message: str) -> Dict[str, str]:
    return {"message": message}
```

### Generate Numbers

A streaming tool that generates a sequence of numbers:

```python
@mcp_router.tool()
async def generate_numbers(count: int = 5) -> AsyncIterator[Dict[str, int]]:
    for i in range(count):
        yield {"number": i}
        await asyncio.sleep(0.2)  # Simulate work between yields
```

### Search Documents

A more complex streaming tool that simulates document search with progressive results:

```python
@mcp_router.tool()
async def search_documents(query: str, top_k: int = 3) -> AsyncIterator[Dict[str, Any]]:
    # Simulate initial processing
    await asyncio.sleep(0.5)
    yield {"status": "processing", "message": f"Searching for: {query}"}
    
    # Generate and stream results...
    for i, doc in enumerate(documents[:top_k]):
        await asyncio.sleep(0.3)
        # Yield individual results...
        yield {"type": "partial_result", "result_number": i + 1, "document": result}
    
    # Final results
    yield {"type": "complete", "results": results}
```

### Calculate

A simple tool that evaluates mathematical expressions:

```python
@mcp_router.tool()
async def calculate(expression: str) -> Dict[str, Any]:
    # Validation and calculation...
    return {"expression": expression, "result": result}
```

## Testing with the Client

You can use the `sse_example.py` in the `examples` directory to test this server:

```bash
python -m fastapi_mcp_client.examples.sse_example
```

This will connect to the server and demonstrate all the available tools. 