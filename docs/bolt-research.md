# Bolt.new Architecture Research & Implementation Plan

## Overview
Bolt.new (by StackBlitz) is an AI-powered full-stack web development environment that runs entirely in the browser using WebContainers.

## Key Technologies & Concepts

### 1. WebContainers Technology
- **What it is**: Browser-based runtime for Node.js applications
- **Key features**:
  - Runs Node.js, package managers (npm/yarn/pnpm), and build tools entirely in browser
  - No server-side execution needed for development
  - Instant preview updates
  - File system access in-browser
  - Works offline after initial load

### 2. Architecture Components

#### Frontend Layer
- **AI Chat Interface**: Natural language code generation
- **Monaco Editor**: VS Code-like code editing experience
- **Live Preview Pane**: Real-time application preview
- **Terminal**: In-browser terminal for package management and commands

#### Execution Layer
- **WebContainer API**: Provides Node.js runtime in browser
- **Virtual File System**: In-memory file system for project files
- **Package Installation**: Downloads and installs npm packages client-side
- **Dev Server**: Runs development servers (Vite, Next.js, etc.) in browser

#### AI Integration
- **Prompt Engineering**: Structured prompts for code generation
- **Context Management**: Maintains project state and file structure
- **Incremental Updates**: Applies code changes without full regeneration
- **Error Handling**: Captures runtime errors and suggests fixes

## Implementation Strategy for CodeBot

### Phase 1: Live Preview Foundation (Pre-Alpha)
**Goal**: Basic live preview for static HTML/CSS/JS

1. **Static Preview Service**
   ```
   POST /api/preview/create
   - Accept HTML/CSS/JS content
   - Generate preview session ID
   - Store in temporary storage
   - Return preview URL
   
   GET /preview/{session_id}
   - Serve HTML with injected CSS/JS
   - Add sandbox security headers
   - Enable hot-reload via WebSocket
   ```

2. **Frontend Preview Component**
   - Iframe-based preview pane
   - Automatic refresh on code changes
   - Console log capture and display
   - Error boundary for crashes

3. **Security Measures**
   - Sandboxed iframe with restricted permissions
   - Content Security Policy headers
   - Session-based access control
   - Automatic cleanup after 1 hour

### Phase 2: Framework Support (Beta)
**Goal**: Support popular frameworks (React, Vue, Svelte)

1. **Build System Integration**
   - Vite integration for fast builds
   - Support for JSX/TSX transpilation
   - Module bundling for dependencies
   - Hot Module Replacement (HMR)

2. **Package Management**
   - CDN-based module loading (esm.sh, skypack)
   - Common dependencies pre-cached
   - On-demand package installation

### Phase 3: WebContainer Integration (Post-Beta)
**Goal**: Full in-browser development environment

1. **WebContainer API Integration**
   - License and integrate @webcontainer/api
   - Set up virtual file system
   - Enable npm/yarn/pnpm in browser
   - Terminal emulation

2. **Advanced Features**
   - Multiple file editing
   - Git integration
   - Collaborative editing
   - Project export/import

## Immediate Pre-Alpha Implementation

### 1. Preview API Endpoint
```python
# backend/routes/preview.py
@api.post(f"{API_PREFIX}/preview/create")
async def create_preview(payload: PreviewCreate, u: Row = Depends(current_user)):
    session_id = str(uuid.uuid4())
    # Store HTML/CSS/JS content with TTL
    await store_preview_content(session_id, payload.html, payload.css, payload.js)
    return {"session_id": session_id, "url": f"/preview/{session_id}"}

@api.get("/preview/{session_id}")
async def get_preview(session_id: str):
    content = await get_preview_content(session_id)
    if not content:
        raise HTTPException(404)
    
    html = render_preview_html(content["html"], content["css"], content["js"])
    return HTMLResponse(html, headers={
        "Content-Security-Policy": "sandbox allow-scripts allow-forms",
        "X-Frame-Options": "SAMEORIGIN"
    })
```

### 2. Preview Component
```tsx
// frontend/src/components/LivePreview.tsx
export function LivePreview({ html, css, js }: PreviewProps) {
  const [previewUrl, setPreviewUrl] = useState<string>()
  
  useEffect(() => {
    const updatePreview = async () => {
      const response = await axios.post('/api/preview/create', { html, css, js })
      setPreviewUrl(`/preview/${response.data.session_id}`)
    }
    
    const debounced = debounce(updatePreview, 500)
    debounced()
  }, [html, css, js])
  
  return (
    <iframe
      src={previewUrl}
      sandbox="allow-scripts allow-forms"
      className="w-full h-full border-0"
    />
  )
}
```

### 3. AI Prompt Enhancement
```python
# Update system prompt to generate preview-ready code
PREVIEW_PROMPT = """
When generating HTML/CSS/JavaScript:
1. Output complete, self-contained HTML
2. Include all styles inline or in <style> tags
3. Use vanilla JS or include CDN links for libraries
4. Ensure code is immediately executable
5. Add error handling and console logging
"""
```

## Benefits for CodeBot Pre-Alpha

1. **Immediate Value**
   - Users see code output instantly
   - No need to copy-paste to external tools
   - Faster iteration cycles

2. **Competitive Edge**
   - Most AI code assistants lack live preview
   - Bolt.new is premium/paid - we can offer similar features

3. **User Experience**
   - Visual feedback builds confidence
   - Easier to spot and fix issues
   - More engaging development flow

4. **Future Foundation**
   - Infrastructure ready for WebContainer integration
   - Incremental feature additions possible
   - Clear upgrade path to full IDE

## Technical Considerations

### Storage
- Use Redis for preview session storage (TTL: 1 hour)
- Fallback to filesystem with cleanup cron job
- Max preview size: 1MB per session

### Performance
- Lazy-load iframe content
- Debounce preview updates (500ms)
- Cache common library CDN URLs
- Compress preview responses

### Security
- Strict CSP headers
- Sandbox all preview iframes
- Session-based access control
- Rate limiting on preview creation
- XSS prevention in user code

## Next Steps

1. ✅ Research Bolt.new architecture
2. [ ] Implement basic preview API
3. [ ] Create LivePreview component
4. [ ] Update AI prompts for preview-ready output
5. [ ] Add preview toggle to chat interface
6. [ ] Test with various frameworks
7. [ ] Add error handling and logging
8. [ ] Implement preview sharing (optional)

## References
- WebContainers: https://webcontainers.io/
- StackBlitz API: https://developer.stackblitz.com/
- Bolt.new patterns: Similar to CodeSandbox/StackBlitz approach
