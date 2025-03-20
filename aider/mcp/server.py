import os
import time
import uuid
from pathlib import Path

from aider.mcp.tools import AiderMCPTools


class AiderMCPServer:
    """MCP server for Aider with session management"""
    
    def __init__(self, name="Aider", session_timeout=3600):
        """Initialize the Aider MCP server with session management"""
        self.name = name
        self.session_timeout = session_timeout  # Session timeout in seconds
        self.sessions = {}  # Map session_id -> AiderMCPTools
        
        # Create MCP server - We import this here to avoid
        # requiring mcp-python and fastmcp if not needed
        try:
            from mcp.server.fastmcp import FastMCP
            self.mcp = FastMCP(name)
        except ImportError:
            raise ImportError(
                "MCP support requires additional packages. "
                "Install with 'pip install aider-chat[mcp]'"
            )
        
        # Register tools and resources
        self._register_tools()
        self._register_resources()
        
    def _get_or_create_session(self, session_id, repo_path, ctx):
        """Get existing session or create a new one"""
        # Clean up expired sessions
        self._cleanup_inactive_sessions()
        
        # Create a new session if it doesn't exist
        if session_id not in self.sessions:
            try:
                self.sessions[session_id] = AiderMCPTools(repo_path)
                ctx.debug(f"Created new session {session_id} for repo {repo_path}")
            except Exception as e:
                ctx.error(f"Failed to create session: {e}")
                raise
                
        return self.sessions[session_id]
        
    def _cleanup_inactive_sessions(self):
        """Clean up inactive sessions"""
        current_time = time.time()
        for session_id in list(self.sessions.keys()):
            session = self.sessions[session_id]
            if current_time - session.last_activity > self.session_timeout:
                # Log cleanup
                print(f"Cleaning up inactive session {session_id}")
                # Delete session
                del self.sessions[session_id]
                
    def _register_tools(self):
        """Register Aider tools with MCP"""
        from mcp.server.fastmcp import Context
        
        @self.mcp.tool()
        def create_session(repo_path: str, ctx: Context) -> dict:
            """Create a new session for working with a repository"""
            session_id = str(uuid.uuid4())
            session = self._get_or_create_session(session_id, repo_path, ctx)
            return {"session_id": session_id}
            
        @self.mcp.tool()
        def edit_file(session_id: str, file_path: str, content: str, ctx: Context) -> str:
            """Edit a file using Aider"""
            try:
                # Validate inputs
                if not session_id or not isinstance(session_id, str):
                    return "Error: Invalid session ID"
                    
                # Get session
                if session_id not in self.sessions:
                    return f"Error: Session {session_id} not found"
                    
                session = self.sessions[session_id]
                
                # Edit file
                result = session.edit_file(file_path, content)
                return f"Successfully edited {file_path}: {result}"
            except ValueError as e:
                ctx.error(f"Value error: {e}")
                return f"Failed to edit file: {e}"
            except FileNotFoundError as e:
                ctx.error(f"File not found: {e}")
                return f"Failed to edit file: {e}"
            except Exception as e:
                ctx.error(f"Error editing file: {e}")
                return f"Failed to edit file: {e}"
                
        @self.mcp.tool()
        def commit_changes(session_id: str, message: str, ctx: Context) -> str:
            """Commit changes using git"""
            try:
                # Validate inputs
                if not session_id or not isinstance(session_id, str):
                    return "Error: Invalid session ID"
                    
                # Get session
                if session_id not in self.sessions:
                    return f"Error: Session {session_id} not found"
                    
                session = self.sessions[session_id]
                
                # Commit changes
                result = session.commit_changes(message)
                return f"Successfully committed changes: {result}"
            except Exception as e:
                ctx.error(f"Error committing changes: {e}")
                return f"Failed to commit changes: {e}"
                
        @self.mcp.tool()
        def extract_code_blocks(markdown: str, ctx: Context) -> dict:
            """Extract code blocks from markdown text"""
            import re
            
            # Regex pattern to identify code blocks with optional language
            pattern = r"```(\w*)\n(.*?)```"
            matches = re.findall(pattern, markdown, re.DOTALL)
            
            code_blocks = {}
            for i, (lang, code) in enumerate(matches):
                lang = lang.strip() or "text"
                code_blocks[f"block_{i+1}"] = {
                    "language": lang,
                    "code": code.strip()
                }
            
            return code_blocks
    
    def _register_resources(self):
        """Register Aider resources with MCP"""
        from mcp.server.fastmcp import Context
        
        @self.mcp.resource("repo://{session_id}/status")
        def get_repo_status(session_id: str, ctx: Context) -> str:
            """Get the current git repository status"""
            try:
                # Validate inputs
                if not session_id or not isinstance(session_id, str):
                    return "Error: Invalid session ID"
                    
                # Get session
                if session_id not in self.sessions:
                    return f"Error: Session {session_id} not found"
                    
                session = self.sessions[session_id]
                
                # Get status
                return session.get_repo_status()
            except Exception as e:
                ctx.error(f"Error getting repository status: {e}")
                return f"Failed to get repository status: {e}"
                
        @self.mcp.resource("repo://{session_id}/files/{path}")
        def get_file_content(session_id: str, path: str, ctx: Context) -> str:
            """Get the content of a file in the repository"""
            try:
                # Validate inputs
                if not session_id or not isinstance(session_id, str):
                    return "Error: Invalid session ID"
                    
                # Get session
                if session_id not in self.sessions:
                    return f"Error: Session {session_id} not found"
                    
                session = self.sessions[session_id]
                
                # Get file content
                return session.get_file_content(path)
            except FileNotFoundError:
                ctx.error(f"File not found: {path}")
                return f"File not found: {path}"
            except Exception as e:
                ctx.error(f"Error reading file: {e}")
                return f"Failed to read file: {e}"
                
        @self.mcp.resource("repo://{session_id}/structure")
        def get_repo_structure(session_id: str, ctx: Context) -> str:
            """Get the repository structure"""
            try:
                # Validate inputs
                if not session_id or not isinstance(session_id, str):
                    return "Error: Invalid session ID"
                    
                # Get session
                if session_id not in self.sessions:
                    return f"Error: Session {session_id} not found"
                    
                session = self.sessions[session_id]
                
                # Get repository structure
                return session.get_repo_structure()
            except Exception as e:
                ctx.error(f"Error getting repository structure: {e}")
                return f"Failed to get repository structure: {e}"
    
    def run(self, transport="stdio", port=8000):
        """Run the MCP server with the specified transport"""
        if transport == "stdio":
            self.mcp.stdio()
        elif transport == "sse":
            # Only import uvicorn when needed
            try:
                import uvicorn
                uvicorn.run(self.mcp.sse_app(), host="0.0.0.0", port=port)
            except ImportError:
                raise ImportError(
                    "SSE transport requires uvicorn. "
                    "Install with 'pip install aider-chat[mcp]'"
                )
        else:
            raise ValueError(f"Unsupported transport: {transport}")
