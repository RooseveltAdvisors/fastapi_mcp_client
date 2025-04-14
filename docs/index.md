# FastAPI MCP Client

A specialized client library specifically designed to work with [fastapi-mcp](https://github.com/tadata-org/fastapi_mcp) servers that implement the Model Context Protocol (MCP) over Server-Sent Events (SSE). This library provides a seamless way to interact with MCP-enabled FastAPI services.

## Installation

```bash
# Install with pip
pip install fastapi-mcp-client

# Or with UV (recommended)
uv add fastapi-mcp-client
```

## Quick Start

```python
import asyncio
from fastapi_mcp_client import MCPClient

async def main():
    async with MCPClient("http://localhost:8000") as client:
        # Call a non-streaming operation
        result = await client.call_operation("echo", {"message": "Hello, MCP!"})
        print(f"Echo result: {result}")
        
        # Call a streaming operation with SSE
        stream = await client.call_operation(
            "generate_numbers", 
            {"count": 5},
            stream=True
        )
        
        async for event in stream:
            print(f"Event: {event}")

asyncio.run(main())
```

## Features

- **MCP Protocol Support**: Full implementation of the Model Context Protocol
- **SSE Streaming**: First-class support for Server-Sent Events (SSE) streaming
- **Async-First Design**: Fully async-compatible for high-performance applications
- **Seamless Session Management**: Handles MCP session establishment and message passing
- **Error Handling**: Comprehensive error handling with fallback mechanisms
- **Type Annotations**: Full type hints for better IDE integration and validation

## Understanding the MCP/SSE Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server

    Note over C,S: Establish SSE Connection
    C->>+S: GET /mcp (Accept: text/event-stream)
    S-->>-C: 200 OK (Connection Open)
    S-->>C: SSE: data: /mcp/messages/?session_id=XXX

    Note over C: Parse session_id=XXX

    Note over C,S: MCP Initialization
    C->>+S: POST /mcp/messages/?session_id=XXX <br> Payload: {method: "initialize", ...}
    S-->>-C: 202 Accepted

    Note over C,S: MCP Tool Call
    C->>+S: POST /mcp/messages/?session_id=XXX <br> Payload: {method: "tools/call", ...}
    S-->>-C: 202 Accepted

    Note over C,S: Stream Results
    S-->>C: SSE: data: {result_part_1}
    S-->>C: SSE: data: {result_part_2}
    S-->>C: SSE: data: {final_result}
    Note over S: (Closes SSE Connection or sends close event)
```

## Next Steps

- Check out the provided examples in the [repository](https://github.com/your-username/fastapi-mcp-client/tree/main/examples)
- Explore custom client configuration options
- Learn about advanced streaming techniques

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/your-username/fastapi-mcp-client/blob/main/LICENSE) file for details. 