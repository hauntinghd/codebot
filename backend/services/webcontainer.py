"""WebContainers - Browser-based development environment.

A lightweight implementation inspired by StackBlitz WebContainers.
This provides:
1. Virtual file system (in-memory)
2. Process execution (via backend proxy)
3. Real-time file synchronization
4. Preview server management

For production use, consider:
- @stackblitz/sdk for full WebContainers
- Sandpack (@codesandbox/sandpack-react) for simpler use cases
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import uuid
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("codebot")
from backend.services.preview_manager import preview_manager


@dataclass
class FileSystemNode:
    """A node in the virtual file system."""
    name: str
    is_directory: bool = False
    content: str = ""
    children: Dict[str, "FileSystemNode"] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        if self.is_directory:
            return {
                "type": "directory",
                "name": self.name,
                "children": {k: v.to_dict() for k, v in self.children.items()}
            }
        return {
            "type": "file",
            "name": self.name,
            "content": self.content
        }


class VirtualFileSystem:
    """In-memory virtual file system.
    
    Provides file operations that can be synced to disk or kept in memory.
    """
    
    def __init__(self, project_id: str, base_path: Optional[str] = None):
        self.project_id = project_id
        self.base_path = base_path or f"data/projects/{project_id}"
        self.root = FileSystemNode(name="/", is_directory=True)
        self._watchers: List[Callable[[str, str], None]] = []
    
    def _get_node(self, path: str, create_dirs: bool = False) -> Optional[FileSystemNode]:
        """Get a node by path, optionally creating parent directories."""
        parts = [p for p in path.strip("/").split("/") if p]
        node = self.root
        
        for i, part in enumerate(parts):
            if part not in node.children:
                if create_dirs and i < len(parts) - 1:
                    # Create intermediate directory
                    node.children[part] = FileSystemNode(name=part, is_directory=True)
                else:
                    return None
            node = node.children[part]
        
        return node
    
    def _get_parent(self, path: str) -> Tuple[Optional[FileSystemNode], str]:
        """Get parent node and filename for a path."""
        parts = [p for p in path.strip("/").split("/") if p]
        if not parts:
            return None, ""
        
        filename = parts[-1]
        parent_path = "/".join(parts[:-1])
        
        if parent_path:
            parent = self._get_node(parent_path, create_dirs=True)
        else:
            parent = self.root
        
        return parent, filename
    
    def write_file(self, path: str, content: str) -> bool:
        """Write content to a file."""
        parent, filename = self._get_parent(path)
        if parent is None:
            return False
        
        parent.children[filename] = FileSystemNode(
            name=filename,
            is_directory=False,
            content=content
        )
        
        # Notify watchers
        for watcher in self._watchers:
            watcher(path, "write")
        
        return True
    
    def read_file(self, path: str) -> Optional[str]:
        """Read content from a file."""
        node = self._get_node(path)
        if node and not node.is_directory:
            return node.content
        return None
    
    def mkdir(self, path: str) -> bool:
        """Create a directory."""
        parent, dirname = self._get_parent(path)
        if parent is None:
            return False
        
        if dirname not in parent.children:
            parent.children[dirname] = FileSystemNode(
                name=dirname,
                is_directory=True
            )
        
        return True
    
    def rm(self, path: str, recursive: bool = False) -> bool:
        """Remove a file or directory."""
        parent, name = self._get_parent(path)
        if parent is None or name not in parent.children:
            return False
        
        node = parent.children[name]
        if node.is_directory and node.children and not recursive:
            return False
        
        del parent.children[name]
        
        # Notify watchers
        for watcher in self._watchers:
            watcher(path, "delete")
        
        return True
    
    def readdir(self, path: str = "/") -> List[str]:
        """List directory contents."""
        node = self._get_node(path) if path != "/" else self.root
        if node and node.is_directory:
            return list(node.children.keys())
        return []
    
    def exists(self, path: str) -> bool:
        """Check if a path exists."""
        return self._get_node(path) is not None
    
    def is_file(self, path: str) -> bool:
        """Check if path is a file."""
        node = self._get_node(path)
        return node is not None and not node.is_directory
    
    def is_dir(self, path: str) -> bool:
        """Check if path is a directory."""
        node = self._get_node(path)
        return node is not None and node.is_directory
    
    def watch(self, callback: Callable[[str, str], None]) -> None:
        """Add a file watcher callback."""
        self._watchers.append(callback)
    
    def sync_to_disk(self) -> int:
        """Sync virtual filesystem to disk. Returns number of files written."""
        os.makedirs(self.base_path, exist_ok=True)
        count = 0
        
        def write_node(node: FileSystemNode, current_path: str):
            nonlocal count
            for name, child in node.children.items():
                child_path = os.path.join(current_path, name)
                if child.is_directory:
                    os.makedirs(child_path, exist_ok=True)
                    write_node(child, child_path)
                else:
                    with open(child_path, "w") as f:
                        f.write(child.content)
                    count += 1
        
        write_node(self.root, self.base_path)
        return count
    
    def load_from_disk(self) -> int:
        """Load files from disk into virtual filesystem. Returns number of files loaded."""
        if not os.path.exists(self.base_path):
            return 0
        
        count = 0
        
        for root, dirs, files in os.walk(self.base_path):
            rel_root = os.path.relpath(root, self.base_path)
            
            for dir_name in dirs:
                if rel_root == ".":
                    self.mkdir(f"/{dir_name}")
                else:
                    self.mkdir(f"/{rel_root}/{dir_name}")
            
            for file_name in files:
                file_path = os.path.join(root, file_name)
                with open(file_path, "r") as f:
                    content = f.read()
                
                if rel_root == ".":
                    self.write_file(f"/{file_name}", content)
                else:
                    self.write_file(f"/{rel_root}/{file_name}", content)
                count += 1
        
        return count
    
    def to_dict(self) -> dict:
        """Export entire filesystem as dictionary."""
        return self.root.to_dict()
    
    def get_all_files(self) -> List[Tuple[str, str]]:
        """Get all files as (path, content) tuples."""
        files = []
        
        def collect(node: FileSystemNode, current_path: str):
            for name, child in node.children.items():
                child_path = f"{current_path}/{name}"
                if child.is_directory:
                    collect(child, child_path)
                else:
                    files.append((child_path, child.content))
        
        collect(self.root, "")
        return files


@dataclass
class ProcessInfo:
    """Information about a running process."""
    pid: int
    command: str
    status: str = "running"  # running, stopped, error
    exit_code: Optional[int] = None
    output: str = ""
    error: str = ""


class ProcessManager:
    """Manages processes for WebContainer projects."""
    
    def __init__(self, project_id: str, work_dir: str):
        self.project_id = project_id
        self.work_dir = work_dir
        self.processes: Dict[str, ProcessInfo] = {}
        self._subprocess_handles: Dict[str, subprocess.Popen] = {}
    
    async def spawn(
        self,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None
    ) -> str:
        """Spawn a new process. Returns process ID."""
        process_id = str(uuid.uuid4())[:8]
        
        full_command = command
        if args:
            full_command = f"{command} {' '.join(args)}"
        
        logger.info(f"[WebContainer:{self.project_id}] Spawning: {full_command}")
        
        # Create environment
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
        
        try:
            # Run process
            proc = subprocess.Popen(
                full_command,
                shell=True,
                cwd=self.work_dir,
                env=process_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self._subprocess_handles[process_id] = proc
            self.processes[process_id] = ProcessInfo(
                pid=proc.pid,
                command=full_command,
                status="running"
            )
            
            return process_id
            
        except Exception as e:
            logger.error(f"[WebContainer:{self.project_id}] Spawn error: {e}")
            self.processes[process_id] = ProcessInfo(
                pid=0,
                command=full_command,
                status="error",
                error=str(e)
            )
            return process_id
    
    async def wait(self, process_id: str, timeout: Optional[float] = None) -> ProcessInfo:
        """Wait for a process to complete."""
        if process_id not in self._subprocess_handles:
            return self.processes.get(process_id, ProcessInfo(pid=0, command="", status="error"))
        
        proc = self._subprocess_handles[process_id]
        
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            
            self.processes[process_id].status = "stopped"
            self.processes[process_id].exit_code = proc.returncode
            self.processes[process_id].output = stdout
            self.processes[process_id].error = stderr
            
        except subprocess.TimeoutExpired:
            proc.kill()
            self.processes[process_id].status = "stopped"
            self.processes[process_id].error = "Process timed out"
        
        return self.processes[process_id]
    
    async def kill(self, process_id: str) -> bool:
        """Kill a running process."""
        if process_id not in self._subprocess_handles:
            return False
        
        proc = self._subprocess_handles[process_id]
        proc.kill()
        self.processes[process_id].status = "stopped"
        
        return True
    
    def get_status(self, process_id: str) -> Optional[ProcessInfo]:
        """Get process status."""
        return self.processes.get(process_id)
    
    async def cleanup(self) -> None:
        """Kill all processes and cleanup."""
        for process_id in list(self._subprocess_handles.keys()):
            await self.kill(process_id)
        self.processes.clear()
        self._subprocess_handles.clear()


class WebContainer:
    """Main WebContainer class - browser-based development environment.
    
    Usage:
        container = WebContainer(project_id="my-project")
        await container.mount({
            "package.json": {"type": "file", "content": "..."},
            "src": {
                "type": "directory",
                "children": {
                    "index.ts": {"type": "file", "content": "..."}
                }
            }
        })
        process_id = await container.spawn("npm", ["install"])
        result = await container.wait(process_id)
    """
    
    def __init__(self, project_id: str, base_path: Optional[str] = None):
        self.project_id = project_id
        self.base_path = base_path or f"data/projects/{project_id}/webcontainer"
        self.fs = VirtualFileSystem(project_id, self.base_path)
        self.process_manager = ProcessManager(project_id, self.base_path)
        self.is_mounted = False
        self._dev_server_id: Optional[str] = None
        self._dev_server_port: Optional[int] = None
    
    async def boot(self) -> None:
        """Initialize the WebContainer."""
        os.makedirs(self.base_path, exist_ok=True)
        logger.info(f"[WebContainer:{self.project_id}] Booted")
    
    async def mount(self, files: Dict[str, Any]) -> None:
        """Mount files into the container.
        
        Args:
            files: Dictionary mapping paths to file definitions.
                   Each file can be:
                   - {"type": "file", "content": "..."} 
                   - {"type": "directory", "children": {...}}
        """
        def mount_recursive(node: Dict[str, Any], current_path: str = ""):
            for name, entry in node.items():
                path = f"{current_path}/{name}"

                # Accept simple string values as file content
                if isinstance(entry, str):
                    self.fs.write_file(path, entry)
                    continue

                # If entry is a dict-like object, handle explicit types first
                if isinstance(entry, dict):
                    entry_type = entry.get("type") if hasattr(entry, 'get') else None
                    if entry_type == "directory":
                        self.fs.mkdir(path)
                        if "children" in entry and isinstance(entry["children"], dict):
                            mount_recursive(entry["children"], path)
                        continue
                    if entry_type == "file":
                        self.fs.write_file(path, entry.get("content", ""))
                        continue

                    # If dict has no explicit type/content, treat it as nested directory
                    if "content" not in entry and "type" not in entry:
                        self.fs.mkdir(path)
                        mount_recursive(entry, path)
                        continue

                # Fallback: coerce other types to string content
                try:
                    self.fs.write_file(path, str(entry))
                except Exception:
                    logger.warning(f"[WebContainer:{self.project_id}] Skipping mount entry for {path}: unsupported type")
        
        mount_recursive(files)
        
        # Sync to disk
        file_count = self.fs.sync_to_disk()
        self.is_mounted = True
        
        logger.info(f"[WebContainer:{self.project_id}] Mounted {file_count} files")
    
    async def spawn(
        self,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None
    ) -> str:
        """Spawn a process in the container."""
        return await self.process_manager.spawn(command, args, env)
    
    async def wait(self, process_id: str, timeout: Optional[float] = None) -> ProcessInfo:
        """Wait for a process to complete."""
        return await self.process_manager.wait(process_id, timeout)
    
    async def run(
        self,
        command: str,
        args: Optional[List[str]] = None,
        timeout: float = 60.0
    ) -> ProcessInfo:
        """Run a command and wait for it to complete."""
        process_id = await self.spawn(command, args)
        return await self.wait(process_id, timeout)
    
    async def start_dev_server(self, port: int = 3000) -> Tuple[str, int]:
        """Start a development server. Returns (process_id, port)."""
        # Ensure the requested port is available. If not, pick an available ephemeral port
        # to avoid collisions when tests or previous processes left ports bound.
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                try:
                    s.connect(('127.0.0.1', port))
                    # Connection succeeded -> port is in use. Find a free port instead.
                    logger.debug(f"[WebContainer:{self.project_id}] requested port {port} in use, selecting free port")
                    helper = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    helper.bind(('127.0.0.1', 0))
                    _, free_port = helper.getsockname()
                    helper.close()
                    port = int(free_port)
                except Exception:
                    # Connect failed, port is free as expected
                    pass
        except Exception:
            # If any socket checks fail, proceed with the requested port
            pass

        # Check for common dev server commands
        if self.fs.exists("/package.json"):
            pkg_content = self.fs.read_file("/package.json")
            if pkg_content:
                try:
                    pkg = json.loads(pkg_content)
                    scripts = pkg.get("scripts", {})
                    
                    if "dev" in scripts:
                        cmd = "npm run dev"
                    elif "start" in scripts:
                        cmd = "npm run start"
                    else:
                        cmd = f"npx vite --port {port}"
                except json.JSONDecodeError:
                    cmd = f"npx vite --port {port}"
        else:
            # Static file server
            cmd = f"python3 -m http.server {port}"
        
        process_id = await self.spawn(cmd)
        self._dev_server_id = process_id
        self._dev_server_port = port
        
        logger.info(f"[WebContainer:{self.project_id}] Dev server started on port {port}")
        try:
            # Register preview status with preview manager synchronously so
            # the registration is persisted and visible to other worker
            # processes before we return to callers.
            await preview_manager.start_preview(self.project_id, self.base_path, [port])
        except Exception as e:
            logger.warning(f"[WebContainer:{self.project_id}] Failed to register preview: {e}")

        return process_id, port
    
    async def stop_dev_server(self) -> bool:
        """Stop the development server."""
        if self._dev_server_id:
            result = await self.process_manager.kill(self._dev_server_id)
            self._dev_server_id = None
            return result
        return False
    
    def get_preview_url(self) -> Optional[str]:
        """Get the preview URL for the dev server."""
        if self._dev_server_port:
            return f"http://localhost:{self._dev_server_port}"
        return None
    
    async def teardown(self) -> None:
        """Cleanup the WebContainer."""
        await self.process_manager.cleanup()
        self.is_mounted = False
        logger.info(f"[WebContainer:{self.project_id}] Torn down")


# Global container registry
_containers: Dict[str, WebContainer] = {}


async def get_container(project_id: str) -> WebContainer:
    """Get or create a WebContainer for a project."""
    if project_id not in _containers:
        container = WebContainer(project_id)
        await container.boot()
        _containers[project_id] = container
    
    return _containers[project_id]


async def destroy_container(project_id: str) -> bool:
    """Destroy a WebContainer."""
    if project_id in _containers:
        await _containers[project_id].teardown()
        del _containers[project_id]
        return True
    return False


def list_containers() -> List[str]:
    """List all active container IDs."""
    return list(_containers.keys())
