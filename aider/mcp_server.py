#!/usr/bin/env python

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from aider.io import InputOutput
from aider.repo import GitRepo

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("aider.mcp_server")

# Global variables to store Aider components
aider_io: Optional[InputOutput] = None
aider_git_repo: Optional[GitRepo] = None

# Create FastAPI app
app = FastAPI(title="Aider MCP Server", description="Model Context Protocol server for Aider")

# Add CORS middleware to allow requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define Pydantic models for MCP protocol
class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[int, str]] = None

class JsonRpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Union[int, str]] = None

class GetContextParams(BaseModel):
    file_paths: List[str]

class GetContextResult(BaseModel):
    files: Dict[str, Optional[str]]  # path: content (None if file not found)

class ApplyChangesParams(BaseModel):
    file_path: str
    content: str  # New content to write to the file

class ApplyChangesResult(BaseModel):
    success: bool
    message: Optional[str] = None

# Health check endpoint
@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "ok", "version": "1.0.0"}

# Main MCP endpoint
@app.post("/mcp", response_model=JsonRpcResponse)
async def handle_mcp_request(request: JsonRpcRequest):
    """Handle MCP JSON-RPC requests"""
    logger.info(f"Received MCP request: {request.method}")
    
    # Basic request validation
    if not request.method:
        return JsonRpcResponse(
            error={"code": -32600, "message": "Invalid Request"}, 
            id=request.id
        )
    
    # Ensure Aider components are initialized
    if not aider_io:
        return JsonRpcResponse(
            error={"code": -32603, "message": "Aider IO not initialized"}, 
            id=request.id
        )
    
    # Dispatch based on method
    try:
        if request.method == "getContext":
            result = await handle_get_context(request.params or {})
            return JsonRpcResponse(result=result, id=request.id)
        
        elif request.method == "applyChanges":
            result = await handle_apply_changes(request.params or {})
            return JsonRpcResponse(result=result, id=request.id)
        
        else:
            return JsonRpcResponse(
                error={"code": -32601, "message": f"Method '{request.method}' not found"}, 
                id=request.id
            )
    
    except Exception as e:
        logger.error(f"Error handling request: {e}", exc_info=True)
        return JsonRpcResponse(
            error={"code": -32000, "message": f"Server error: {str(e)}"}, 
            id=request.id
        )

async def handle_get_context(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle getContext method to retrieve file contents"""
    try:
        context_params = GetContextParams(**params)
        file_contents = {}
        
        for file_path in context_params.file_paths:
            try:
                # Use Aider's IO to read the file
                content = aider_io.read_text(file_path)
                file_contents[file_path] = content
            except FileNotFoundError:
                logger.warning(f"File not found: {file_path}")
                file_contents[file_path] = None
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                file_contents[file_path] = None
        
        result = GetContextResult(files=file_contents)
        return result.model_dump()
    
    except Exception as e:
        logger.error(f"Error in handle_get_context: {e}", exc_info=True)
        raise

async def handle_apply_changes(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle applyChanges method to write changes to files"""
    try:
        change_params = ApplyChangesParams(**params)
        file_path = change_params.file_path
        new_content = change_params.content
        
        # Check if git repo is available
        has_git = aider_git_repo is not None
        
        # Write the new content to the file
        logger.info(f"Writing changes to {file_path}")
        aider_io.write_text(file_path, new_content)
        
        # If git repo is available, commit the changes
        if has_git:
            try:
                commit_message = f"MCP: Apply changes to {os.path.basename(file_path)}"
                logger.info(f"Committing changes with message: '{commit_message}'")
                aider_git_repo.commit(message=commit_message, files=[file_path])
                result = ApplyChangesResult(
                    success=True, 
                    message=f"Changes applied and committed to {file_path}"
                )
            except Exception as e:
                logger.error(f"Error committing changes: {e}", exc_info=True)
                result = ApplyChangesResult(
                    success=True,
                    message=f"Changes applied to {file_path} but not committed: {str(e)}"
                )
        else:
            result = ApplyChangesResult(
                success=True,
                message=f"Changes applied to {file_path} (no git repository)"
            )
        
        return result.model_dump()
    
    except Exception as e:
        logger.error(f"Error in handle_apply_changes: {e}", exc_info=True)
        return ApplyChangesResult(
            success=False,
            message=f"Error applying changes: {str(e)}"
        ).model_dump()

def run_server(io_instance, git_repo_instance, host: str, port: int):
    """Run the MCP server with the provided Aider components"""
    global aider_io, aider_git_repo
    
    # Store Aider components in global variables
    aider_io = io_instance
    aider_git_repo = git_repo_instance
    
    logger.info(f"Starting Aider MCP server on {host}:{port}")
    
    # Run the server
    uvicorn.run(app, host=host, port=port)