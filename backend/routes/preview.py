"""
Live Preview API Routes
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from backend.auth import get_session_user_id, get_user_by_id
from backend.services.live_preview import preview_manager, ProjectDetector
import os

router = APIRouter(prefix="/preview", tags=["preview"])


async def get_current_user(request: Request) -> dict:
    """Get current user from session"""
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return dict(user)


class PreviewRequest(BaseModel):
    project_id: int
    project_path: str


class DetectionRequest(BaseModel):
    project_path: str


@router.post("/detect")
async def detect_project_type(
    request: DetectionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Detect if a project is previewable in browser
    """
    try:
        # Security: Ensure path is within user's data directory
        user_data_dir = f"data/projects/{current_user['id']}"
        if not request.project_path.startswith(user_data_dir):
            raise HTTPException(status_code=403, detail="Access denied")

        if not os.path.exists(request.project_path):
            raise HTTPException(status_code=404, detail="Project path not found")

        detector = ProjectDetector(request.project_path)
        detection = await detector.detect()

        return {
            "success": True,
            "detection": detection
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection error: {str(e)}")


@router.post("/create")
async def create_preview(
    request: PreviewRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a live preview session for a project
    """
    try:
        # Security check
        user_data_dir = f"data/projects/{current_user['id']}"
        if not request.project_path.startswith(user_data_dir):
            raise HTTPException(status_code=403, detail="Access denied")

        if not os.path.exists(request.project_path):
            raise HTTPException(status_code=404, detail="Project not found")

        result = await preview_manager.create_preview(
            project_id=request.project_id,
            project_path=request.project_path,
            user_id=current_user['id']
        )

        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview creation error: {str(e)}")


@router.delete("/{project_id}")
async def stop_preview(
    project_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Stop a preview session
    """
    preview_status = preview_manager.get_preview_status(project_id)
    
    if not preview_status:
        raise HTTPException(status_code=404, detail="Preview session not found")

    if preview_status["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    await preview_manager.stop_preview(project_id)

    return {"success": True, "message": "Preview stopped"}


@router.get("/{project_id}/status")
async def get_preview_status(
    project_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get status of a preview session
    """
    preview_status = preview_manager.get_preview_status(project_id)

    if not preview_status:
        return {"active": False, "preview_url": None}

    if preview_status["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "active": True,
        "preview_url": f"/preview/{project_id}",
        "config": preview_status
    }


@router.post("/report-issue")
async def report_preview_issue(
    project_id: int,
    issue_description: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Report an issue with live preview
    """
    # Log for debugging
    print(f"[PREVIEW] Issue reported for project {project_id}: {issue_description}")
    
    return {"success": True, "message": "Issue reported"}
