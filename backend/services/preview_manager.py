"""Preview server manager for Architecture mode.

This manager persists a small registry into the application's SQLite DB
(`preview_registry` table) so preview registrations survive backend
restarts and are visible across worker processes. It still keeps an
in-memory index for fast access and queries the DB on init.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Optional

from backend.database import db

logger = logging.getLogger("codebot")




class PreviewServerManager:
    """Manages preview servers for Architecture projects with simple persistence."""
    
    def __init__(self):
        self._servers: Dict[str, Dict] = {}
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        # Load persisted registry if available
        try:
            self._load_registry()
        except Exception as e:
            logger.debug(f"preview_manager: failed to load registry: {e}")
    
    def _load_registry(self) -> None:
        """Load persisted preview registrations from the DB into memory."""
        try:
            with db() as conn:
                cur = conn.execute("SELECT project_id, status, preview_url, port, ports_json, started_at, stopped_at FROM preview_registry")
                rows = cur.fetchall()
                for r in rows:
                    ports = {}
                    if r[4]:
                        try:
                            ports = json.loads(r[4])
                        except Exception:
                            ports = {}
                    self._servers[r[0]] = {
                        "project_id": r[0],
                        "status": r[1],
                        "preview_url": r[2],
                        "port": r[3],
                        "ports": ports,
                        "started_at": r[5],
                        "stopped_at": r[6]
                    }
            logger.info(f"Loaded preview registry with {len(self._servers)} entries from DB")
        except Exception:
            logger.exception("Failed to load preview registry from DB")

    def _save_registry(self) -> None:
        """Persist the in-memory registry to the DB. Uses upsert semantics."""
        try:
            with db() as conn:
                for pid, info in self._servers.items():
                    ports_json = json.dumps(info.get("ports") or {})
                    conn.execute(
                        "INSERT OR REPLACE INTO preview_registry(project_id, status, preview_url, port, ports_json, started_at, stopped_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (pid, info.get("status"), info.get("preview_url"), info.get("port"), ports_json, info.get("started_at"), info.get("stopped_at"))
                    )
            logger.debug(f"Preview registry saved to DB ({len(self._servers)} entries)")
        except Exception:
            logger.exception("Failed to write preview registry to DB")

    async def start_preview(self, project_id: str, project_path: str, ports: list[int]) -> dict:
        """Start / register preview server for a project.

        This method registers the preview immediately into the persisted
        registry so other worker processes and the preview proxy can find it.
        """
        if project_id in self._servers and self._servers[project_id].get("status") == "running":
            return self._servers[project_id]

        try:
            frontend_port = int(ports[0]) if len(ports) > 0 else 3000
            backend_port = int(ports[1]) if len(ports) > 1 else 8000
            preview_url = f"http://localhost:{frontend_port}"

            server_info = {
                "project_id": project_id,
                "status": "running",
                "preview_url": preview_url,
                "port": frontend_port,
                "ports": {"frontend": frontend_port, "backend": backend_port},
                "started_at": datetime.utcnow().isoformat() + "Z"
            }

            self._servers[project_id] = server_info
            # Persist registry synchronously to ensure visibility across workers
            logger.debug(f"Registering preview for project {project_id}: {server_info}")
            try:
                with db() as conn:
                    conn.execute(
                        "INSERT OR REPLACE INTO preview_registry(project_id, status, preview_url, port, ports_json, started_at, stopped_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (project_id, server_info["status"], server_info["preview_url"], server_info["port"], json.dumps(server_info.get("ports", {})), server_info["started_at"], None)
                    )
            except Exception:
                logger.exception("Failed to persist preview registration to DB")

            logger.info(f"Preview server registered for project {project_id} at {preview_url}")
            return server_info

        except Exception as e:
            logger.error(f"Failed to register preview for {project_id}: {e}")
            return {"project_id": project_id, "status": "error", "error": str(e)}

    async def stop_preview(self, project_id: str) -> bool:
        """Stop/unregister preview server for a project."""
        if project_id not in self._servers:
            return False

        try:
            # If there were processes tracked, try to stop them
            if project_id in self._processes:
                process = self._processes[project_id]
                process.terminate()
                await process.wait()
                del self._processes[project_id]

            self._servers[project_id]["status"] = "stopped"
            self._servers[project_id]["stopped_at"] = datetime.utcnow().isoformat() + "Z"
            logger.debug(f"Unregistering preview for project {project_id}")
            try:
                with db() as conn:
                    conn.execute("UPDATE preview_registry SET status = ?, stopped_at = ? WHERE project_id = ?", (self._servers[project_id]["status"], self._servers[project_id]["stopped_at"], project_id))
            except Exception:
                logger.exception("Failed to persist preview stop to DB")

            logger.info(f"Preview server stopped for project {project_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop preview for {project_id}: {e}")
            return False

    def get_preview_status(self, project_id: str) -> Optional[dict]:
        """Get preview server status. If missing in-memory, attempt DB lookup."""
        if project_id in self._servers:
            return self._servers.get(project_id)
        try:
            with db() as conn:
                cur = conn.execute("SELECT project_id, status, preview_url, port, ports_json, started_at, stopped_at FROM preview_registry WHERE project_id = ?", (project_id,))
                r = cur.fetchone()
                if r:
                    ports = {}
                    if r[4]:
                        try:
                            ports = json.loads(r[4])
                        except Exception:
                            ports = {}
                    info = {
                        "project_id": r[0],
                        "status": r[1],
                        "preview_url": r[2],
                        "port": r[3],
                        "ports": ports,
                        "started_at": r[5],
                        "stopped_at": r[6]
                    }
                    self._servers[project_id] = info
                    return info
        except Exception:
            logger.exception("Failed to load preview status from DB")
        return None

    def list_active_previews(self) -> list[dict]:
        """List all active preview servers."""
        # Ensure any DB-backed entries are visible
        try:
            with db() as conn:
                cur = conn.execute("SELECT project_id FROM preview_registry WHERE status = 'running'")
                for row in cur.fetchall():
                    pid = row[0]
                    if pid not in self._servers:
                        # populate from DB
                        self.get_preview_status(pid)
        except Exception:
            logger.exception("Failed to refresh active previews from DB")

        return [info for info in self._servers.values() if info.get("status") == "running"]


# Global preview manager instance
preview_manager = PreviewServerManager()
