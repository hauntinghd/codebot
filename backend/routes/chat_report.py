"""Report issue endpoint for chat messages."""
from typing import Any, Dict, Optional
import sqlite3
from fastapi import Depends, HTTPException
from backend.auth import current_user
from backend.config import API_PREFIX
from backend.database import db
from backend.services.ai.corrector import corrector

import logging
logger = logging.getLogger("codebot")


def register_report_routes(api):
    """Register report issue routes."""
    
    @api.post(f"{API_PREFIX}/chats/report-issue")
    async def report_issue(
        message_id: str,
        issue_type: str,
        description: str,
        code_snippet: Optional[str] = None,
        u: sqlite3.Row = Depends(current_user)
    ) -> Dict[str, Any]:
        """User reports an issue with AI response (hallucination, incorrect code, etc)."""
        if issue_type not in ['hallucination', 'incorrect_code', 'wrong_file', 'vague', 'other']:
            raise HTTPException(status_code=400, detail="Invalid issue type")
        
        # Initialize corrector with database connection
        with db() as conn:
            corrector_instance = corrector
            corrector_instance.db = conn
            
            report_id = await corrector_instance.report_issue(
                message_id=int(message_id) if message_id.isdigit() else 0,
                issue_type=issue_type,
                description=description,
                user_id=int(u["id"]),
                code_snippet=code_snippet
            )
        
        logger.info(f"Issue reported by user {u['id']}: {issue_type} - {description[:100]}")
        
        return {
            "success": True,
            "report_id": report_id,
            "message": "Thank you for your feedback! This helps improve CodeBot."
        }
