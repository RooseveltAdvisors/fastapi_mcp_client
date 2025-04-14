# FastAPI MCP Client Examples

This directory contains examples demonstrating how to use the FastAPI MCP Client library.

## Overview

The examples demonstrate how to connect to a FastAPI MCP server, establish an SSE connection, and process streaming responses.

## Example Server

The [`server`](./server/) directory contains a sample FastAPI MCP server that you can use to test the client. See the [server README](./server/README.md) for details on how to run it.

## SSE Example

The [`sse_example.py`](./sse_example.py) script demonstrates how to use the FastAPI MCP Client to connect to a server and stream results via SSE. It showcases:

1. Setting up a client with custom configuration
2. Connecting to an MCP server
3. Making calls to different types of tools (both streaming and non-streaming)
4. Processing streaming events from the server

### Running the SSE Example

To run the SSE example:

```bash
# First, start the example server in a separate terminal
uvicorn fastapi_mcp_client.examples.server.simple_server:app --reload

# Then run the SSE example
python -m fastapi_mcp_client.examples.sse_example
```

The example will:

1. Connect to the server
2. Make a simple non-streaming call to the `echo` tool
3. Make a streaming call to the `generate_numbers` tool and process events
4. Make a streaming call to the `search_documents` tool and process events
5. Make a non-streaming call to the `calculate` tool

## Communication Flow

The examples demonstrate the MCP protocol flow over SSE:

1. Client establishes an SSE connection via `GET /mcp`
2. Server sends back a session ID
3. Client sends an initialize request via `POST /mcp/messages/?session_id=XXX`
4. Client sends a tool call request via `POST /mcp/messages/?session_id=XXX`
5. Server streams results back over the original SSE connection
6. Client processes the streaming events 