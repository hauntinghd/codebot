
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import logging
import io
import zipfile

router = APIRouter(tags=["WebContainer"])
logger = logging.getLogger("codebot")

@router.get("/{project_id}/fs/export_zip")
async def export_file_tree_zip(project_id: str):
    """Export the entire file tree as a ZIP archive."""
    try:
        container = await get_container(project_id)
        files = container.fs.get_all_files()
        mem_zip = io.BytesIO()
        with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path, content in files:
                zf.writestr(path.lstrip("/"), content)
        mem_zip.seek(0)
        from fastapi.responses import StreamingResponse
        return StreamingResponse(mem_zip, media_type="application/zip", headers={
            "Content-Disposition": f"attachment; filename=project_{project_id}_files.zip"
        })
    except Exception as e:
        logger.error(f"[WebContainer] Export ZIP error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
"""WebContainer API routes.

Provides REST API for WebContainer operations:
- Boot/teardown containers
- File operations (read, write, list)
- Process management (spawn, kill, status)
- Dev server control
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import logging

from backend.services.webcontainer import (
    get_container,
    destroy_container,
    list_containers,
    WebContainer,
    ProcessInfo
)
from backend.services.preview_manager import preview_manager

router = APIRouter(tags=["WebContainer"])
logger = logging.getLogger("codebot")


# === Request/Response Models ===

class MountRequest(BaseModel):
    """Request to mount files into a container."""
    files: Dict[str, Any]  # path -> {type, content} or nested structure


class WriteFileRequest(BaseModel):
    """Request to write a file."""
    path: str
    content: str


class SpawnRequest(BaseModel):
    """Request to spawn a process."""
    command: str
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None


class RunRequest(BaseModel):
    """Request to run a command and wait."""
    command: str
    args: Optional[List[str]] = None
    timeout: float = 60.0


class DevServerRequest(BaseModel):
    """Request to start dev server."""
    port: int = 3000


class ProcessResponse(BaseModel):
    """Process information response."""
    pid: int
    command: str
    status: str
    exit_code: Optional[int] = None
    output: str = ""
    error: str = ""


class ContainerStatus(BaseModel):
    """Container status response."""
    project_id: str
    is_mounted: bool
    file_count: int
    dev_server_url: Optional[str] = None


# === Routes ===

@router.post("/{project_id}/boot")
async def boot_container(project_id: str) -> Dict[str, str]:
    """Boot a new WebContainer for a project."""
    try:
        container = await get_container(project_id)
        return {
            "status": "ok",
            "message": f"WebContainer booted for project {project_id}"
        }
    except Exception as e:
        logger.error(f"[WebContainer] Boot error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/mount")
async def mount_files(project_id: str, request: MountRequest) -> Dict[str, Any]:
    """Mount files into the container."""
    try:
        container = await get_container(project_id)
        await container.mount(request.files)
        
        file_count = len(container.fs.get_all_files())
        
        return {
            "status": "ok",
            "message": f"Mounted {file_count} files",
            "file_count": file_count
        }
    except Exception as e:
        logger.error(f"[WebContainer] Mount error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/status")
async def get_container_status(project_id: str) -> ContainerStatus:
    """Get container status."""
    try:
        container = await get_container(project_id)
        
        return ContainerStatus(
            project_id=project_id,
            is_mounted=container.is_mounted,
            file_count=len(container.fs.get_all_files()),
            dev_server_url=container.get_preview_url()
        )
    except Exception as e:
        logger.error(f"[WebContainer] Status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def teardown_container(project_id: str) -> Dict[str, str]:
    """Teardown a WebContainer."""
    try:
        result = await destroy_container(project_id)
        if result:
            return {"status": "ok", "message": "Container destroyed"}
        else:
            return {"status": "ok", "message": "Container was not active"}
    except Exception as e:
        logger.error(f"[WebContainer] Teardown error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_active_containers() -> Dict[str, List[str]]:
    """List all active container IDs."""
    return {"containers": list_containers()}


# === File Operations ===

@router.get("/{project_id}/fs")
async def list_directory(
    project_id: str,
    path: str = Query(default="/", description="Directory path")
) -> Dict[str, Any]:
    """List directory contents."""
    try:
        container = await get_container(project_id)
        contents = container.fs.readdir(path)
        
        items = []
        for name in contents:
            full_path = f"{path.rstrip('/')}/{name}"
            items.append({
                "name": name,
                "path": full_path,
                "is_directory": container.fs.is_dir(full_path)
            })
        
        return {"path": path, "items": items}
    except Exception as e:
        logger.error(f"[WebContainer] List dir error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/fs/file")
async def read_file(
    project_id: str,
    path: str = Query(..., description="File path")
) -> Dict[str, Any]:
    """Read a file from the container."""
    try:
        container = await get_container(project_id)
        content = container.fs.read_file(path)
        
        if content is None:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {"path": path, "content": content}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WebContainer] Read file error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/fs/file")
async def write_file(project_id: str, request: WriteFileRequest) -> Dict[str, str]:
    """Write a file to the container."""
    try:
        container = await get_container(project_id)
        container.fs.write_file(request.path, request.content)
        container.fs.sync_to_disk()
        
        return {"status": "ok", "message": f"Wrote {request.path}"}
    except Exception as e:
        logger.error(f"[WebContainer] Write file error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}/fs/file")
async def delete_file(
    project_id: str,
    path: str = Query(..., description="File path"),
    recursive: bool = Query(default=False, description="Recursive delete for directories")
) -> Dict[str, str]:
    """Delete a file or directory."""
    try:
        container = await get_container(project_id)
        result = container.fs.rm(path, recursive=recursive)
        
        if not result:
            raise HTTPException(status_code=404, detail="Path not found or not empty")
        
        container.fs.sync_to_disk()
        return {"status": "ok", "message": f"Deleted {path}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WebContainer] Delete file error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/fs/tree")
async def get_file_tree(project_id: str) -> Dict[str, Any]:
    """Get entire file tree."""
    try:
        container = await get_container(project_id)
        return container.fs.to_dict()
    except Exception as e:
        logger.error(f"[WebContainer] Tree error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/fs/files")
async def get_all_files(project_id: str) -> Dict[str, List[Dict[str, str]]]:
    """Get all files with their content."""
    try:
        container = await get_container(project_id)
        files = container.fs.get_all_files()
        
        return {
            "files": [{"path": path, "content": content} for path, content in files]
        }
    except Exception as e:
        logger.error(f"[WebContainer] Get all files error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === Process Management ===

@router.post("/{project_id}/process/spawn")
async def spawn_process(project_id: str, request: SpawnRequest) -> Dict[str, str]:
    """Spawn a new process."""
    try:
        container = await get_container(project_id)
        process_id = await container.spawn(request.command, request.args, request.env)
        
        return {
            "status": "ok",
            "process_id": process_id
        }
    except Exception as e:
        logger.error(f"[WebContainer] Spawn error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/process/run")
async def run_command(project_id: str, request: RunRequest) -> ProcessResponse:
    """Run a command and wait for completion."""
    try:
        container = await get_container(project_id)
        result = await container.run(request.command, request.args, request.timeout)
        
        return ProcessResponse(
            pid=result.pid,
            command=result.command,
            status=result.status,
            exit_code=result.exit_code,
            output=result.output,
            error=result.error
        )
    except Exception as e:
        logger.error(f"[WebContainer] Run error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/process/{process_id}")
async def get_process_status(project_id: str, process_id: str) -> ProcessResponse:
    """Get process status."""
    try:
        container = await get_container(project_id)
        info = container.process_manager.get_status(process_id)
        
        if not info:
            raise HTTPException(status_code=404, detail="Process not found")
        
        return ProcessResponse(
            pid=info.pid,
            command=info.command,
            status=info.status,
            exit_code=info.exit_code,
            output=info.output,
            error=info.error
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WebContainer] Process status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/process/{process_id}/wait")
async def wait_for_process(
    project_id: str,
    process_id: str,
    timeout: float = Query(default=60.0, description="Timeout in seconds")
) -> ProcessResponse:
    """Wait for a process to complete."""
    try:
        container = await get_container(project_id)
        info = await container.wait(process_id, timeout)
        
        return ProcessResponse(
            pid=info.pid,
            command=info.command,
            status=info.status,
            exit_code=info.exit_code,
            output=info.output,
            error=info.error
        )
    except Exception as e:
        logger.error(f"[WebContainer] Wait error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}/process/{process_id}")
async def kill_process(project_id: str, process_id: str) -> Dict[str, str]:
    """Kill a running process."""
    try:
        container = await get_container(project_id)
        result = await container.process_manager.kill(process_id)
        
        if result:
            return {"status": "ok", "message": "Process killed"}
        else:
            raise HTTPException(status_code=404, detail="Process not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WebContainer] Kill error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === Dev Server ===

@router.post("/{project_id}/dev-server/start")
async def start_dev_server(project_id: str, request: DevServerRequest) -> Dict[str, Any]:
    """Start the development server."""
    try:
        container = await get_container(project_id)
        process_id, port = await container.start_dev_server(request.port)
        
        return {
            "status": "ok",
            "process_id": process_id,
            "port": port,
            "url": container.get_preview_url()
        }
    except Exception as e:
        logger.error(f"[WebContainer] Start dev server error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/dev-server/register")
async def register_dev_server(project_id: str, ports: Optional[List[int]] = None) -> Dict[str, Any]:
    """Explicitly register a dev-server preview for a project.

    This is useful when the in-memory registration may be lost across
    worker restarts; calling this will persist the preview entry so the
    preview-proxy can find it.
    """
    try:
        container = await get_container(project_id)
        # If ports not provided, try to infer from the container
        inferred_ports = ports or []
        if not inferred_ports:
            url = container.get_preview_url()
            if url:
                try:
                    inferred_ports = [int(url.split(":")[-1])]
                except Exception:
                    inferred_ports = [3000]

        info = await preview_manager.start_preview(project_id, container.base_path, inferred_ports)
        return {"status": "ok", "preview": info}
    except Exception as e:
        logger.error(f"[WebContainer] Register dev server error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/dev-server/unregister")
async def unregister_dev_server(project_id: str) -> Dict[str, Any]:
    try:
        ok = await preview_manager.stop_preview(project_id)
        return {"status": "ok", "stopped": ok}
    except Exception as e:
        logger.error(f"[WebContainer] Unregister dev server error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/dev-server/force-register")
async def force_register_dev_server(project_id: str, ports: Optional[List[int]] = None) -> Dict[str, Any]:
    """Force (re-)register a preview entry for a single project.

    This endpoint is safe to call when the container is not active; it will
    attempt to reuse any previously persisted registry entry, infer ports from
    the active container if available, or fall back to common defaults.
    """
    try:
        # Prefer explicit ports passed by the caller
        inferred_ports = ports or []

        # If no ports provided, reuse persisted entry if present
        existing = preview_manager.get_preview_status(project_id)
        if not inferred_ports and existing and isinstance(existing.get("ports"), dict):
            fp = existing["ports"].get("frontend")
            bp = existing["ports"].get("backend", 8000)
            if fp:
                inferred_ports = [int(fp), int(bp)]

        # Try to infer from an active container if still available
        if not inferred_ports:
            try:
                container = await get_container(project_id)
                url = container.get_preview_url()
                if url:
                    try:
                        inferred_ports = [int(url.split(":")[-1])]
                    except Exception:
                        inferred_ports = [3000]
            except Exception:
                # container not active or other error; fall through
                inferred_ports = inferred_ports or []

        if not inferred_ports:
            inferred_ports = [3000, 8000]

        project_path = f"data/projects/{project_id}"
        info = await preview_manager.start_preview(project_id, project_path, inferred_ports)
        return {"status": "ok", "preview": info}
    except Exception as e:
        logger.exception(f"[WebContainer] Force register error for {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/dev-server/registry")
async def get_dev_server_registry(project_id: str) -> Dict[str, Any]:
    try:
        status = preview_manager.get_preview_status(project_id)
        return {"status": "ok", "preview": status}
    except Exception as e:
        logger.error(f"[WebContainer] Get registry error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/dev-server/stop")
async def stop_dev_server(project_id: str) -> Dict[str, str]:
    """Stop the development server."""
    try:
        container = await get_container(project_id)
        result = await container.stop_dev_server()
        
        if result:
            return {"status": "ok", "message": "Dev server stopped"}
        else:
            return {"status": "ok", "message": "Dev server was not running"}
    except Exception as e:
        logger.error(f"[WebContainer] Stop dev server error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/dev-server/url")
async def get_dev_server_url(project_id: str) -> Dict[str, Any]:
    """Get the development server URL."""
    try:
        container = await get_container(project_id)
        url = container.get_preview_url()
        
        return {
            "url": url,
            "running": url is not None
        }
    except Exception as e:
        logger.error(f"[WebContainer] Get URL error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dev-server/re-register-all")
async def re_register_all_dev_servers() -> Dict[str, Any]:
    """Scan active containers and persist preview registrations for each.

    This endpoint is useful to recover preview registry entries after
    a backend restart or when running with multiple worker processes.
    """
    try:
        registered = []
        for project_id in list_containers():
            try:
                container = await get_container(project_id)
                url = container.get_preview_url()
                inferred_ports = []
                if url:
                    try:
                        inferred_ports = [int(url.split(":")[-1])]
                    except Exception:
                        inferred_ports = [3000]

                info = await preview_manager.start_preview(project_id, container.base_path, inferred_ports)
                registered.append({"project_id": project_id, "preview": info})
            except Exception as inner:
                logger.exception(f"Failed to re-register project {project_id}: {inner}")
        return {"status": "ok", "registered": registered}
    except Exception as e:
        logger.error(f"[WebContainer] Re-register all error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
