"""Pydantic models for request/response validation."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class RegisterIn(BaseModel):
    email: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class MeOut(BaseModel):
    id: str
    email: str
    is_admin: bool
    subscription_status: str
    plan: str
    current_period_end: int
    credits_remaining: Optional[float] = None


class ChatOut(BaseModel):
    chat_id: str
    title: str
    created_at: int
    updated_at: int


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: int


class ChatMessageIn(BaseModel):
    content: str
    project_id: Optional[str] = None
    file_paths: Optional[List[str]] = None
    file_ids: Optional[List[str]] = None
    title_hint: Optional[str] = None
    code_mode: Optional[str] = "functional"  # "mock" or "functional"


class ChatMessageOut(BaseModel):
    message_id: str
    content: str
    role: str = "assistant"
    created_at: int
    tokens_input: int = 0
    tokens_output: int = 0
    cost_in_credits: Optional[float] = None
    credits_remaining: Optional[float] = None
    is_admin: Optional[bool] = None
    model_used: Optional[str] = None
    ai_layers: Optional[List[str]] = None
    verification_badge: Optional[Dict[str, Any]] = None


class CreateCheckoutIn(BaseModel):
    plan: str  # basic|pro|elite


class CheckoutOut(BaseModel):
    url: str


class ApiKeySetIn(BaseModel):
    api_key: str
    provider: str = "huggingface"  # huggingface, anthropic, gemini, replicate, grok


class ApiKeyOut(BaseModel):
    has_key: bool
    provider: Optional[str] = None


class PortalOut(BaseModel):
    url: str


class ProjectOut(BaseModel):
    id: str
    name: str
    created_at: int
    updated_at: int


class AddCreditsIn(BaseModel):
    amount: float
    description: str


# Architecture Mode Models

class ArchitectureProjectCreate(BaseModel):
    """Create new architecture project."""
    name: str
    description: Optional[str] = None
    template: Optional[str] = "blank"  # blank, react, nextjs, fastapi, fullstack


class ArchitectureProjectOut(BaseModel):
    """Architecture project output."""
    project_id: str
    name: str
    description: Optional[str] = None
    template: str
    status: str  # planning, design, building, testing, deployed
    preview_url: Optional[str] = None
    created_at: int
    updated_at: int


class ArchitectureTaskCreate(BaseModel):
    """Create architecture task."""
    project_id: str
    phase: str  # plan, design, build, test, deploy
    title: str
    description: Optional[str] = None


class ArchitectureTaskOut(BaseModel):
    """Architecture task output."""
    task_id: str
    project_id: str
    phase: str
    title: str
    description: Optional[str] = None
    status: str  # pending, in_progress, completed, failed
    created_at: int
    updated_at: int


class PreviewStartRequest(BaseModel):
    """Start preview server request."""
    project_id: str
    ports: Optional[List[int]] = [3000, 8000]  # frontend, backend


class PreviewStatusOut(BaseModel):
    """Preview server status."""
    project_id: str
    status: str  # stopped, starting, running, error
    preview_url: Optional[str] = None
    ports: Optional[dict] = None
    started_at: Optional[int] = None


class FileTreeNode(BaseModel):
    """File tree node."""
    name: str
    type: str  # file, directory
    path: str
    children: Optional[List['FileTreeNode']] = None


class ArchitectureWorkflowRequest(BaseModel):
    """Request to run architecture workflow."""
    project_id: str
    phase: str  # plan, design, build, test, deploy
    requirements: Optional[str] = None
