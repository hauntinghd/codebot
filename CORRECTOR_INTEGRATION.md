"""
Integration Guide: Adding Corrector Layer to Chat API

This shows how to integrate the Corrector Layer into the existing chat message flow.
"""

# STEP 1: Update backend/routes/chat.py

# At the top, add import:
from backend.services.ai.corrector import correct_and_verify

# In the send_message function, after AI generates response but before saving to DB:

async def send_message_example():
    # ... existing code to generate AI response ...
    
    # Original response from Engineer/Auditor layers
    ai_response = "..." # From your AI generation
    
    # NEW: Run through Corrector Layer
    corrected_response, analysis = await correct_and_verify(
        response=ai_response,
        context={
            'user_id': user_id,
            'message': user_message,
            'project_id': project_id,
        },
        files_accessed=files_read_by_ai,  # List of files AI actually read
        inject_citations=True  # Add source links
    )
    
    # Save verification metadata to DB
    cursor.execute("""
        INSERT INTO message_verifications 
        (message_id, confidence_score, has_hallucination, issues_detected, sources_used, verified_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        message_id,
        analysis['confidence'],
        analysis['has_hallucination'],
        json.dumps(analysis['issues']),
        json.dumps(analysis['sources']),
        datetime.utcnow().isoformat()
    ))
    
    # Return corrected response + verification badge
    return {
        'message': corrected_response,
        'verification': {
            'confidence': analysis['confidence'],
            'verified': analysis['verified'],
            'badge': await corrector.get_verified_badge(analysis),
            'sources': analysis['sources']
        }
    }


# STEP 2: Update frontend/src/components/MessageBubble.tsx

interface MessageProps {
    message: string
    verification?: {
        confidence: number
        verified: boolean
        badge: {
            show: boolean
            type: 'verified' | 'warning' | 'caution'
            text: string
            color: string
        }
        sources: string[]
    }
}

export default function MessageBubble({ message, verification }: MessageProps) {
    return (
        <div className="message-bubble">
            <div className="message-content">{message}</div>
            
            {/* NEW: Verification Badge */}
            {verification?.badge.show && (
                <div className={`verification-badge badge-${verification.badge.color}`}>
                    {verification.badge.type === 'verified' && <CheckCircle className="w-4 h-4" />}
                    {verification.badge.type === 'warning' && <AlertTriangle className="w-4 h-4" />}
                    {verification.badge.type === 'caution' && <AlertCircle className="w-4 h-4" />}
                    <span>{verification.badge.text}</span>
                    <span className="confidence">
                        {Math.round(verification.confidence * 100)}%
                    </span>
                </div>
            )}
            
            {/* NEW: Sources Section */}
            {verification?.sources && verification.sources.length > 0 && (
                <div className="sources-section">
                    <div className="sources-label">Sources:</div>
                    {verification.sources.map((source, i) => (
                        <a
                            key={i}
                            href={source}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="source-link"
                        >
                            {source}
                        </a>
                    ))}
                </div>
            )}
            
            {/* NEW: Report Issue Button */}
            <button
                onClick={() => reportIssue(messageId)}
                className="report-button"
            >
                <Flag className="w-4 h-4" />
                Report Issue
            </button>
        </div>
    )
}


# STEP 3: Add Report Issue Handler

async function reportIssue(messageId: number) {
    const issueType = prompt('Select issue type: hallucination, incorrect_code, wrong_file, vague, other')
    if (!issueType) return
    
    const description = prompt('Describe the issue:')
    if (!description) return
    
    try {
        await axios.post('/codebot/api/chat/report-issue', {
            message_id: messageId,
            issue_type: issueType,
            description: description
        })
        
        alert('Thank you for reporting! This helps improve CodeBot.')
    } catch (err) {
        console.error('Failed to report issue:', err)
        alert('Failed to submit report. Please try again.')
    }
}


# STEP 4: Add Report Issue Endpoint to backend/routes/chat.py

@router.post("/report-issue")
async def report_issue(
    message_id: int,
    issue_type: str,
    description: str,
    code_snippet: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    User reports an issue with AI response
    Types: 'hallucination', 'incorrect_code', 'wrong_file', 'vague', 'other'
    """
    from backend.services.ai.corrector import corrector
    
    report_id = await corrector.report_issue(
        message_id=message_id,
        issue_type=issue_type,
        description=description,
        user_id=current_user['id'],
        code_snippet=code_snippet
    )
    
    return {
        "success": True,
        "report_id": report_id,
        "message": "Thank you for your feedback!"
    }


# STEP 5: Add CSS for Verification Badges

/* In your global CSS or ChatPage.css */
.verification-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0.75rem;
    border-radius: 0.5rem;
    font-size: 0.875rem;
    margin-top: 0.5rem;
}

.badge-green {
    background: rgba(34, 197, 94, 0.1);
    color: #22c55e;
    border: 1px solid rgba(34, 197, 94, 0.3);
}

.badge-yellow {
    background: rgba(234, 179, 8, 0.1);
    color: #eab308;
    border: 1px solid rgba(234, 179, 8, 0.3);
}

.badge-orange {
    background: rgba(249, 115, 22, 0.1);
    color: #f97316;
    border: 1px solid rgba(249, 115, 22, 0.3);
}

.sources-section {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--space-border);
}

.sources-label {
    font-size: 0.875rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
    opacity: 0.7;
}

.source-link {
    display: block;
    font-size: 0.75rem;
    color: var(--space-accent);
    text-decoration: none;
    margin-bottom: 0.25rem;
}

.source-link:hover {
    text-decoration: underline;
}

.report-button {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.75rem;
    color: var(--space-muted);
    background: none;
    border: none;
    cursor: pointer;
    margin-top: 0.5rem;
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    transition: all 0.2s;
}

.report-button:hover {
    color: var(--space-text);
    background: var(--space-panel-light);
}


# STEP 6: Test the Integration

1. Send a message that should trigger hallucination detection:
   "Can you check my database.py file?" (when no files uploaded)

2. Verify you see:
   - Warning badge with low confidence
   - Issue detected: "Mentioned file but may not have accessed it"

3. Send a message with code:
   "Here's a Python function: def hello(): print('hi')"

4. Verify you see:
   - Sources section with python.org links
   - Verified badge if no issues

5. Click "Report Issue" and submit feedback

6. Check database:
   SELECT * FROM hallucination_reports ORDER BY created_at DESC LIMIT 1;


# STEP 7: Monitor and Improve

-- View hallucination trends
SELECT 
    DATE(created_at) as date,
    issue_type,
    COUNT(*) as count
FROM hallucination_reports
GROUP BY DATE(created_at), issue_type
ORDER BY date DESC;

-- View average confidence by user
SELECT 
    u.email,
    AVG(mv.confidence_score) as avg_confidence,
    COUNT(*) as messages
FROM message_verifications mv
JOIN messages m ON mv.message_id = m.id
JOIN users u ON m.user_id = u.id
WHERE mv.verified_at > datetime('now', '-7 days')
GROUP BY u.email
ORDER BY avg_confidence ASC;

-- Find most common issues
SELECT 
    issue_type,
    COUNT(*) as count,
    AVG(LENGTH(description)) as avg_description_length
FROM hallucination_reports
GROUP BY issue_type
ORDER BY count DESC;


# STEP 8: Continuous Improvement

1. Review hallucination_reports weekly
2. Add new patterns to HALLUCINATION_PATTERNS based on reports
3. Update TRUSTED_SOURCES with new documentation sites
4. Adjust confidence thresholds based on false positive rate
5. Implement semantic similarity checking (beyond pattern matching)
6. Train custom model on reported issues (future enhancement)

"""

# Example: Full integration in chat.py

async def process_message(user_message: str, user_id: int, project_id: int):
    # 1. Security Layer (existing)
    validate_input(user_message)
    
    # 2. Router Layer (existing)
    service_type = route_to_service(user_message)
    
    # 3. Engineer Layer (existing)
    ai_response = await generate_response(user_message, service_type)
    files_accessed = track_files_read()  # Track which files AI actually read
    
    # 4. Auditor Layer (existing)
    audit_result = await audit_response(ai_response)
    
    # 5. Corrector Layer (NEW!)
    corrected_response, analysis = await correct_and_verify(
        response=ai_response,
        context={
            'user_id': user_id,
            'message': user_message,
            'project_id': project_id,
            'service_type': service_type,
        },
        files_accessed=files_accessed,
        inject_citations=True
    )
    
    # Save to database with verification
    message_id = save_message(corrected_response, user_id)
    save_verification(message_id, analysis)
    
    # Get badge for frontend
    badge = await corrector.get_verified_badge(analysis)
    
    return {
        'message': corrected_response,
        'verification': {
            'confidence': analysis['confidence'],
            'verified': analysis['verified'],
            'badge': badge,
            'sources': analysis['sources'],
            'issues': analysis['issues'] if not analysis['verified'] else []
        }
    }
