"""
Simple FastAPI MCP Server Example.

This server demonstrates how to create a FastAPI application with MCP support
for streaming responses through Server-Sent Events (SSE).

Run with:
    uvicorn simple_server:app --reload
"""

import asyncio
import random
from typing import Dict, List, Any, AsyncIterator

from fastapi import FastAPI, HTTPException, APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi_mcp import FastApiMCP

# Create the FastAPI application
app = FastAPI(
    title="FastAPI MCP Example Server",
    description="A simple server demonstrating MCP/SSE capabilities",
    version="0.1.0",
)

# Create an API router for the tools
router = APIRouter()

# Create the MCP server
mcp = FastApiMCP(app)

# Add a simple health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# -- API Endpoints as MCP Tools --

@router.post("/echo", tags=["tools"], operation_id="echo")
async def echo(request: Request) -> JSONResponse:
    """
    Echo the provided message.
    
    Args:
        message: The message to echo
        
    Returns:
        A dictionary containing the echoed message
    """
    data = await request.json()
    message = data.get("message", "")
    return JSONResponse({"message": message})


async def number_generator(count: int) -> AsyncIterator[str]:
    """Stream generator for numbers."""
    for i in range(count):
        yield f"data: {{'number': {i}}}\n\n"
        await asyncio.sleep(0.2)  # Simulate work between yields


@router.post("/generate_numbers", tags=["tools"], operation_id="generate_numbers")
async def generate_numbers(request: Request) -> StreamingResponse:
    """
    Generate a sequence of numbers with streaming.
    
    Args:
        count: How many numbers to generate
        
    Returns:
        A stream of generated numbers
    """
    data = await request.json()
    count = data.get("count", 5)
    
    return StreamingResponse(
        number_generator(count),
        media_type="text/event-stream"
    )


async def document_search_generator(query: str, top_k: int) -> AsyncIterator[str]:
    """Stream generator for document search."""
    # Simulate some initial processing time
    await asyncio.sleep(0.5)
    
    # Send an initial status update
    yield f"data: {{'status': 'processing', 'message': 'Searching for: {query}'}}\n\n"
    
    # Create some example documents with random similarities
    documents = [
        {"id": "doc1", "title": "Introduction to Machine Learning", "content": "Machine learning is a subfield of artificial intelligence..."},
        {"id": "doc2", "title": "Deep Learning Fundamentals", "content": "Deep learning is a subset of machine learning..."},
        {"id": "doc3", "title": "Natural Language Processing", "content": "NLP is a field of AI focused on language understanding..."},
        {"id": "doc4", "title": "Computer Vision", "content": "Computer vision enables machines to interpret visual information..."},
        {"id": "doc5", "title": "Reinforcement Learning", "content": "Reinforcement learning trains agents through rewards..."},
    ]
    
    # Simulate streaming results as they're found
    results = []
    for i, doc in enumerate(documents[:top_k]):
        # Simulate processing time between results
        await asyncio.sleep(0.3)
        
        # Create a result with a "relevance" score
        similarity = random.uniform(0.5, 1.0)
        result = {
            "id": doc["id"],
            "title": doc["title"],
            "similarity": similarity,
            "snippet": doc["content"][:50] + "..."
        }
        results.append(result)
        
        # Yield the individual result
        import json
        partial_result = {
            "type": "partial_result", 
            "result_number": i + 1, 
            "document": result
        }
        yield f"data: {json.dumps(partial_result)}\n\n"
    
    # Finally, yield the complete result set
    complete_result = {"type": "complete", "results": results}
    yield f"data: {json.dumps(complete_result)}\n\n"


@router.post("/search_documents", tags=["tools"], operation_id="search_documents")
async def search_documents(request: Request) -> StreamingResponse:
    """
    Simulate a streaming document search.
    
    Args:
        query: The search query
        top_k: Number of results to return
        
    Returns:
        A stream of search results
    """
    data = await request.json()
    query = data.get("query", "")
    top_k = data.get("top_k", 3)
    
    return StreamingResponse(
        document_search_generator(query, top_k),
        media_type="text/event-stream"
    )


@router.post("/calculate", tags=["tools"], operation_id="calculate")
async def calculate(request: Request) -> JSONResponse:
    """
    Safely evaluate a mathematical expression.
    
    Args:
        expression: The mathematical expression to evaluate
        
    Returns:
        The result of the calculation
    """
    data = await request.json()
    expression = data.get("expression", "")
    
    # Very limited safe eval for demo purposes
    allowed_chars = set("0123456789+-*/() .")
    if not all(c in allowed_chars for c in expression):
        raise HTTPException(status_code=400, detail="Invalid characters in expression")
    
    try:
        # Warning: eval is used here for demonstration only
        # In production, use a proper safe math expression evaluator
        result = eval(expression)
        return JSONResponse({"expression": expression, "result": result})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error evaluating expression: {str(e)}")


# Include the router in the app and mount the MCP server
app.include_router(router)
mcp.mount()  # Mount the MCP server to the FastAPI app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("simple_server:app", host="0.0.0.0", port=8888, reload=True) 