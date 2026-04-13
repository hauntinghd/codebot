# Internet Access Control - Testing Guide

## Overview
CodeBot is now restricted from internet access by default. It can only use internet when absolutely necessary for specific error lookups.

## What's Restricted
- General "what is" / "how to" / "explain" questions
- Best practices queries  
- Tutorial requests
- Documentation browsing without specific need
- Theoretical coding discussions

## What's Allowed
- **Error stacktraces**: When user pastes a real error message with line numbers
- **CVE lookups**: Security vulnerability research
- **Specific version queries**: "Does Python 3.12 support X?"
- **API deprecation checks**: "Is urllib.request.urlopen deprecated?"
- **Library compatibility**: "Does React 18 work with Vite 5?"

## Test Cases

### Test 1: Forbidden General Question ❌
**Send**: "What is the best way to write Python code?"

**Expected**: 
- Internet access: DENIED
- Reason: "General knowledge question - must use uploaded files"
- Response: AI should refuse or work only with uploaded files

### Test 2: Legitimate Error Lookup ✅
**Send**: 
```
I'm getting this error:
TypeError: 'NoneType' object is not subscriptable
  File "app.py", line 42, in process_data
    result = data[0]
```

**Expected**:
- Internet access: ALLOWED
- Reason: "Request contains error stacktrace - needs documentation lookup"
- Response: AI can cite official Python docs for this specific error

### Test 3: Work With Uploaded Files ✅
**Steps**:
1. Upload a Python file (e.g., `server.py`)
2. Send: "Can you review this code for bugs?"

**Expected**:
- Internet access: NOT NEEDED (has context)
- Response: AI analyzes the uploaded file only

### Test 4: CVE Lookup ✅
**Send**: "Is CVE-2023-12345 affecting my Django version?"

**Expected**:
- Internet access: ALLOWED
- Reason: "CVE vulnerability lookup"
- Response: Can cite security databases

### Test 5: Block Violation Attempt ⚠️
**Send**: "What are Python decorators?" (general question)

**Expected**:
- Internet access: DENIED
- If AI tries to cite docs anyway, response should be blocked
- `internet_violation` should be logged in database

## Database Verification

Check internet access logs:
```sql
SELECT 
    m.content as user_message,
    mv.internet_allowed,
    mv.internet_reason,
    mv.internet_violation
FROM message_verifications mv
JOIN messages m ON mv.message_id = m.id
ORDER BY mv.verified_at DESC
LIMIT 10;
```

## Expected Behavior

1. **Default**: Internet OFF
2. **With uploaded files**: Should work without internet
3. **With error stacktrace**: Internet ON, specific docs only
4. **General questions**: Blocked or uses only uploaded context
5. **Violations**: Logged to database, response replaced

## Success Criteria

✅ General questions rejected or use uploaded files only  
✅ Error lookups allowed with specific citations  
✅ CVE/version queries allowed  
✅ Violations logged to database  
✅ Hallucinations reduced (AI can't make up info from "memory")

## Monitoring

Watch for:
- `internet_allowed = 1` only for legitimate needs
- `internet_violation IS NOT NULL` if AI tries to bypass
- `confidence_score` remains high even with restrictions
- `has_hallucination = 0` more frequently than before
