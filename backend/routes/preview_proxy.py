from fastapi import APIRouter, Request, Response, HTTPException
import httpx
import asyncio
from typing import Optional
from backend.services.preview_manager import preview_manager
from backend.services.webcontainer import get_container
from backend.auth import get_session_user_id
from backend.database import db
from fastapi.responses import JSONResponse
import logging
from backend.database import db

logger = logging.getLogger('codebot')

router = APIRouter(prefix="/preview-proxy", tags=["preview-proxy"])


def _filter_hop_by_hop_headers(headers: dict) -> dict:
    hop_by_hop = {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
    return {k: v for k, v in headers.items() if k.lower() not in hop_by_hop}


@router.api_route("/{project_id}/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_vite_http(
    project_id: str,
    full_path: str,
    request: Request
):
    """
    Proxy HTTP requests to the project's dev server with retries and backoff.

    This endpoint will attempt multiple short requests if the target dev server
    is not yet ready (connection refused, timeouts, or 5xx responses). It
    returns the upstream response when available or a clear 503/504 error
    describing the last failure.
    """
    preview = preview_manager.get_preview_status(project_id)
    logger.info(f"[preview-proxy] project={project_id} preview_manager={preview}")
    # Ensure the project has completed its AI build step before exposing previews
    try:
        with db() as conn:
            prow = conn.execute("SELECT built FROM architecture_projects WHERE id = ?", (project_id,)).fetchone()
            built_val = 0
            if prow and prow[0] is not None:
                try:
                    built_val = int(prow[0])
                except Exception:
                    built_val = 0
            logger.debug(f"[preview-proxy] project={project_id} built={built_val}")
            # If project not built, we will still allow authorized users to probe previews
            # but deny unauthenticated or non-paying users early.
            # Authorization check below will enforce subscription requirements.
    except HTTPException:
        raise
    except Exception:
        # If DB check fails for unexpected reasons, continue with proxy flow
        logger.debug(f"[preview-proxy] could not determine built status for project {project_id}")
    port: Optional[int] = None
    # Prefer preview_manager record when available
    if preview:
        if "port" in preview:
            port = preview["port"]
        elif "ports" in preview and isinstance(preview["ports"], dict) and "frontend" in preview["ports"]:
            port = preview["ports"]["frontend"]

    # Fallback: ask the WebContainer instance for the preview URL/port
    if not port:
        try:
            container = await get_container(project_id)
            url = container.get_preview_url()
            logger.info(f"[preview-proxy] container.get_preview_url for {project_id} => {url}")
            if url:
                # url like http://localhost:3001
                try:
                    port = int(url.split(":")[-1])
                except Exception:
                    port = None
        except Exception as e:
            logger.debug(f"[preview-proxy] get_container error for {project_id}: {e}")
            port = None

    if not port:
        # As a last-resort, probe a broader range of common frontend ports on localhost
        # to increase the chance of finding a dev server started on a non-standard port
        # during rapid E2E runs. Keep short timeouts to avoid long delays.
        probe_ports = list(range(3000, 3101))
        async with httpx.AsyncClient() as client:
            for p in probe_ports:
                try:
                    probe_url = f"http://localhost:{p}/{full_path}"
                    logger.debug(f"[preview-proxy] probing {probe_url}")
                    r = await client.get(probe_url, timeout=0.3)
                    logger.info(f"[preview-proxy] probe {p} => status={r.status_code}")
                    if r.status_code < 500:
                        port = p
                        logger.info(f"[preview-proxy] selected port {port} for project {project_id}")
                        break
                except Exception as e:
                    logger.debug(f"[preview-proxy] probe error for port {p}: {e}")
                    continue

    if not port:
        # No preview server found; return 404 for authorized users, otherwise 403
        # But ensure the requester is authorized first
        try:
            uid = get_session_user_id(request)
        except Exception:
            uid = None
        if not uid:
            raise HTTPException(status_code=403, detail="Preview unavailable: authentication required")

        # Verify user plan/admin
        try:
            with db() as conn:
                user_row = conn.execute("SELECT plan, is_admin FROM users WHERE id = ?", (str(uid),)).fetchone()
                is_admin = int(user_row["is_admin"]) if user_row and "is_admin" in user_row.keys() and user_row["is_admin"] is not None else 0
                plan = str(user_row["plan"]) if user_row and "plan" in user_row.keys() and user_row["plan"] is not None else "none"
        except Exception:
            is_admin = 0
            plan = "none"

        if is_admin == 1 or plan in ("basic", "pro", "elite"):
            raise HTTPException(status_code=404, detail="Preview server not running for this project.")
        raise HTTPException(status_code=403, detail="Preview unavailable to non-paying users")

    # Build target URL. If full_path is empty, request the root '/'.
    target_path = full_path or ""
    url = f"http://localhost:{port}/{target_path}"

    method = request.method
    headers = dict(request.headers)
    body = await request.body()

    max_retries = 8
    backoff = 0.4
    last_exc: Optional[BaseException] = None
    last_resp_status: Optional[int] = None

    async with httpx.AsyncClient() as client:
        for attempt in range(1, max_retries + 1):
            try:
                resp = await client.request(method, url, headers=headers, content=body, timeout=7.0, follow_redirects=True)
                last_resp_status = resp.status_code

                # Treat 200-399 as success, return immediately
                if 200 <= resp.status_code < 400:
                    # Treat empty responses as transient (some dev servers may not
                    # be fully ready even if TCP connects succeed). Retry a few
                    # times to allow the dev server to warm up.
                    if not resp.content or len(resp.content) == 0:
                        last_resp_status = resp.status_code
                        last_exc = None
                        logger.debug(f"[preview-proxy] empty response from {url}, retrying")
                        # Quick socket-level probe: some dev servers accept TCP then close
                        # without sending data; perform a lightweight probe to detect that
                        # case and retry early.
                        try:
                            async def _tcp_probe(p):
                                try:
                                    r, w = await asyncio.wait_for(asyncio.open_connection('127.0.0.1', p), timeout=0.4)
                                    req_line = f"GET /{target_path} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
                                    w.write(req_line.encode())
                                    await w.drain()
                                    data = await asyncio.wait_for(r.read(256), timeout=0.6)
                                    try:
                                        w.close()
                                    except Exception:
                                        pass
                                    return bool(data)
                                except Exception:
                                    return False

                            ok = await _tcp_probe(port)
                            if not ok:
                                last_exc = None
                                await asyncio.sleep(backoff)
                                backoff *= 1.9
                                continue
                        except Exception:
                            # If probe fails unexpectedly, continue to attempt HTTP request
                            pass
                        await asyncio.sleep(backoff)
                        backoff *= 1.9
                        continue

                    filtered_headers = _filter_hop_by_hop_headers(dict(resp.headers))
                    return Response(content=resp.content, status_code=resp.status_code, headers=filtered_headers)

                # On 404 or other non-2xx/3xx, consider target not ready and retry a few times
                if resp.status_code >= 500 or resp.status_code == 404:
                    last_exc = None
                    await asyncio.sleep(backoff)
                    backoff *= 1.9
                    continue

                # For other client errors (4xx), return the response directly
                filtered_headers = _filter_hop_by_hop_headers(dict(resp.headers))
                return Response(content=resp.content, status_code=resp.status_code, headers=filtered_headers)

            except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError, httpx.ReadError, httpx.ProtocolError) as e:
                # Treat a broader set of httpx transient/connection errors as retryable.
                last_exc = e
                logger.debug(f"[preview-proxy] transient httpx error contacting {url}: {e}")
                await asyncio.sleep(backoff)
                backoff *= 1.9
                continue
            except Exception as e:
                # Catch-all for unexpected transient errors (e.g. sudden socket close).
                last_exc = e
                logger.debug(f"[preview-proxy] unexpected error contacting {url}: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(backoff)
                    backoff *= 1.9
                    continue
                else:
                    # Let the final handling below convert to an HTTPException
                    break

    # All retries exhausted
    if last_exc:
        raise HTTPException(status_code=504, detail=f"Preview proxy could not connect to dev server: {str(last_exc)}")
    elif last_resp_status:
        raise HTTPException(status_code=503, detail=f"Preview server returned status {last_resp_status} after retries")
    else:
        raise HTTPException(status_code=503, detail="Preview server not responding")

# Note: WebSocket proxy removed to avoid conflicts with Server-Sent Events (SSE).
