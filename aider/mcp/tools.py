import os
import time
from pathlib import Path

from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model
from aider.repo import GitRepo


class AiderMCPTools:
    """Core integration between MCP and Aider's functionality"""
    
    def __init__(self, repo_path, model_name=None, io=None):
        """Initialize Aider integration with direct class access"""
        self.repo_path = Path(repo_path).resolve()
        self.model_name = model_name or "gpt-4o"  # Default model
        self.io = io or InputOutput()
        self.git_repo = GitRepo(self.io, git_root=str(self.repo_path))
        
        # Create model instance if specified
        self.model = Model(self.model_name) if model_name else None
        
        # Initialize a coder instance if model is specified
        self.coder = None
        if self.model:
            self.coder = Coder.create(
                main_model=self.model,
                fnames=[],  # Will be populated as needed
                git_root=str(self.repo_path),
                io=self.io
            )
            
        # Track last activity time for session management
        self.last_activity = time.time()
        
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = time.time()
        
    def edit_file(self, file_path, content):
        """Edit a file using Aider's Coder directly"""
        self.update_activity()
        
        # Convert to absolute path
        abs_path = (self.repo_path / file_path).resolve()
        rel_path = abs_path.relative_to(self.repo_path)
        
        # Safety check - ensure file is within repo
        if not str(abs_path).startswith(str(self.repo_path)):
            raise ValueError(f"File path {file_path} is outside repository")
            
        # Add the file to the coder's context if not already there
        if self.coder and str(abs_path) not in self.coder.abs_fnames:
            self.coder.abs_fnames.append(str(abs_path))
            
        # Use the coder to edit the file
        if self.coder:
            result = self.coder.edit_files({str(abs_path): content})
        else:
            try:
                # If no coder, do basic file write
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(content)
                result = f"Wrote {len(content)} bytes to {file_path}"
            except Exception as e:
                raise ValueError(f"Failed to write file: {str(e)}")
                
        return result
        
    def commit_changes(self, message):
        """Commit changes using GitRepo directly"""
        self.update_activity()
        
        # Use Aider's git repo implementation
        result = self.git_repo.commit(message)
        return result
        
    def get_repo_status(self):
        """Get repository status using GitRepo directly"""
        self.update_activity()
        
        # Use Aider's git repo implementation
        return self.git_repo.status()
        
    def get_file_content(self, file_path):
        """Get file content using direct file operations"""
        self.update_activity()
        
        # Convert to absolute path
        abs_path = (self.repo_path / file_path).resolve()
        
        # Safety check - ensure file is within repo
        if not str(abs_path).startswith(str(self.repo_path)):
            raise ValueError(f"File path {file_path} is outside repository")
            
        # Read file content
        if not abs_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        return abs_path.read_text(encoding="utf-8")
        
    def get_repo_structure(self):
        """Get repository structure using direct file operations"""
        self.update_activity()
        
        # Use a repo map if available
        if self.coder and hasattr(self.coder, 'repo_map'):
            return self.coder.repo_map.get_repo_map()
            
        # Fallback to simple directory listing
        files = []
        for path in self.repo_path.rglob('*'):
            if path.is_file() and not path.name.startswith('.'):
                files.append(str(path.relative_to(self.repo_path)))
                
        return '\n'.join(files)
