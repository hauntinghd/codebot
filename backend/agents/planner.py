"""Planner Agent.

The architect of the system. Analyzes requirements and creates
comprehensive project plans with:
- UML diagrams (Mermaid syntax)
- Project structure
- Data models
- API design
- Component hierarchy
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from .base import Agent, AgentRole, AgentContext, AgentResult

logger = logging.getLogger("codebot.agents")


PLANNER_SYSTEM_PROMPT = """You are the Planner Agent - a world-class software architect with 20+ years of experience designing scalable systems.

Your role is to create comprehensive, actionable project plans. You think in terms of:
- User experience and journeys
- System architecture and data flow
- Scalability and maintainability
- Edge cases and failure modes

You communicate through structured plans that other agents can execute.

CRITICAL RULES:
1. Focus on PRODUCT understanding first, technical details second
2. Create visual diagrams using Mermaid syntax
3. Be specific about file structures and naming
4. Identify all dependencies upfront
5. Anticipate integration points and potential issues
6. Design for testability from the start
"""


class PlannerAgent(Agent):
    """Planner Agent - Creates architecture and project plans.
    
    Capabilities:
    - Product requirement analysis
    - UML diagram generation (Mermaid)
    - Project structure design
    - API design
    - Database schema design
    - Component hierarchy planning
    """
    
    def __init__(self, ai_client: Any, model: str = "gpt-4o"):
        super().__init__(
            ai_client=ai_client,
            role=AgentRole.PLANNER,
            name="Planner",
            description="Analyzes requirements and creates comprehensive project plans",
            model=model,
        )
    
    @property
    def system_prompt(self) -> str:
        return PLANNER_SYSTEM_PROMPT
    
    async def execute(
        self,
        context: AgentContext,
        include_uml: bool = True,
        include_api: bool = True,
        depth: str = "detailed",  # "quick", "standard", "detailed"
        **kwargs
    ) -> AgentResult:
        """Create a comprehensive project plan.
        
        Args:
            context: Agent context with user request
            include_uml: Whether to include UML diagrams
            include_api: Whether to include API design
            depth: Level of detail ("quick", "standard", "detailed")
        """
        start_time = __import__("time").time()
        
        # Build the planning prompt based on depth
        if depth == "quick":
            plan_prompt = self._build_quick_prompt(context)
        elif depth == "detailed":
            plan_prompt = self._build_detailed_prompt(context, include_uml, include_api)
        else:
            plan_prompt = self._build_standard_prompt(context, include_uml)
        
        # Get memory context if available
        memory_context = ""
        if context.memory:
            memory_context = f"\n\nPREVIOUS CONTEXT:\n{context.memory.get('summary', 'No previous context.')}"
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": plan_prompt + memory_context},
        ]
        
        try:
            response, tokens = await self._call_ai(
                messages,
                temperature=0.7,
                max_tokens=4000 if depth == "detailed" else 2000,
            )
            
            # Parse the response to extract structured data
            artifacts = self._parse_plan(response)
            
            return AgentResult(
                success=True,
                output=response,
                artifacts=artifacts,
                tokens_used=tokens,
                execution_time=__import__("time").time() - start_time,
                next_agent=AgentRole.CODER,  # Suggest Coder as next
            )
            
        except Exception as e:
            logger.error(f"Planner execution failed: {e}")
            return AgentResult(
                success=False,
                output="",
                errors=[str(e)],
                execution_time=__import__("time").time() - start_time,
            )
    
    def _build_quick_prompt(self, context: AgentContext) -> str:
        """Build a quick planning prompt."""
        return f"""Create a quick project overview for:

USER REQUEST: {context.user_request}

Output a brief plan covering:
1. **What** - One paragraph describing the product
2. **Core Features** - 3-5 key features as bullet points  
3. **Tech Stack** - List of technologies to use
4. **File Structure** - Just the main files/folders

Keep it concise - this is for quick iteration."""
    
    def _build_standard_prompt(
        self,
        context: AgentContext,
        include_uml: bool
    ) -> str:
        """Build a standard planning prompt."""
        uml_section = """
## System Architecture (Mermaid)
Create a component diagram showing main modules and their relationships.

```mermaid
graph TD
    [YOUR DIAGRAM HERE]
```
""" if include_uml else ""
        
        return f"""Create a comprehensive project plan for:

USER REQUEST: {context.user_request}

{f"EXISTING FILES: {list(context.files.keys())}" if context.files else ""}

Output a structured plan with these sections:

## 🎯 Product Understanding

### What You're Building
[Describe the product - what it does, who it's for]

### Core Value
[One sentence - why does this exist?]

### User Journeys
[2-3 main user flows through the application]

{uml_section}

## 📁 Project Structure
```
[Full file tree with descriptions]
```

## 📊 Data Model
[Define entities, fields, and relationships]

## 🧩 Component Design
[List main components and their responsibilities]

## 📦 Dependencies
[NPM packages needed with brief justification]

## ⚠️ Risks & Mitigations
[3-5 potential issues and how to prevent them]

Be specific and actionable. This plan guides all subsequent development."""
    
    def _build_detailed_prompt(
        self,
        context: AgentContext,
        include_uml: bool,
        include_api: bool
    ) -> str:
        """Build a detailed planning prompt."""
        api_section = """
## 🔌 API Design

### Endpoints
| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| ... | ... | ... | ... | ... |

### Authentication
[Describe auth strategy]

### Error Handling
[Standard error response format]
""" if include_api else ""
        
        return f"""Create a comprehensive, production-ready project plan for:

USER REQUEST: {context.user_request}

{f"EXISTING FILES: {list(context.files.keys())}" if context.files else ""}
{f"PREVIOUS ERRORS TO AVOID: {context.errors}" if context.errors else ""}

## 🎯 Product Understanding

### What You're Building
[Comprehensive description - problem, solution, target users]

### Core Value Proposition
[Why would someone use this over alternatives?]

### User Personas
[1-2 user personas with goals and pain points]

### User Journeys
[3-5 detailed user flows with steps]

### Success Metrics
[How do we know if this is successful?]

## 🏗️ System Architecture

### High-Level Architecture (Mermaid)
```mermaid
graph TB
    subgraph Frontend
        UI[React UI]
        State[State Management]
    end
    subgraph Backend
        API[API Layer]
        BL[Business Logic]
        DB[(Database)]
    end
    UI --> State
    State --> API
    API --> BL
    BL --> DB
```

### Component Diagram (Mermaid)
```mermaid
graph LR
    [DETAILED COMPONENT DIAGRAM]
```

### Data Flow
[Describe how data moves through the system]

## 📁 Project Structure
```
project/
├── src/
│   ├── components/     # UI components
│   │   ├── common/     # Shared components
│   │   └── features/   # Feature-specific
│   ├── hooks/          # Custom React hooks
│   ├── stores/         # State management
│   ├── services/       # API calls
│   ├── types/          # TypeScript types
│   ├── utils/          # Utility functions
│   └── pages/          # Page components
├── tests/              # Test files
└── [config files]
```
[Explain each major directory]

## 📊 Data Model

### Entity Relationship (Mermaid)
```mermaid
erDiagram
    [ER DIAGRAM]
```

### Entities
[Detailed field definitions for each entity]

{api_section}

## 🧩 Component Hierarchy
[Detailed component tree with props interfaces]

## 📦 Dependencies

### Production
| Package | Version | Purpose |
|---------|---------|---------|
| ... | ... | ... |

### Development
| Package | Version | Purpose |
|---------|---------|---------|
| ... | ... | ... |

## 🧪 Testing Strategy

### Unit Tests
[What to test at unit level]

### Integration Tests
[Key integration test scenarios]

### E2E Tests
[Critical user flows to test]

## ⚠️ Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| ... | ... | ... | ... |

## 🚀 Implementation Order
[Numbered list of implementation steps for the Coder agent]

Be extremely specific. This plan is the blueprint for the entire system."""
    
    def _parse_plan(self, response: str) -> Dict[str, Any]:
        """Parse the plan response to extract structured data."""
        artifacts: Dict[str, Any] = {
            "raw_plan": response,
            "sections": {},
            "mermaid_diagrams": [],
            "files": [],
            "dependencies": [],
        }
        
        # Extract Mermaid diagrams
        mermaid_pattern = r"```mermaid\n(.*?)```"
        diagrams = re.findall(mermaid_pattern, response, re.DOTALL)
        artifacts["mermaid_diagrams"] = diagrams
        
        # Extract file paths from code blocks
        file_pattern = r"(?:├──|└──|\|── )\s*([a-zA-Z0-9_/.-]+)"
        files = re.findall(file_pattern, response)
        artifacts["files"] = [f for f in files if "." in f or f.endswith("/")]
        
        # Extract dependencies table rows
        dep_pattern = r"\|\s*([a-z@/-]+)\s*\|\s*([0-9.^~]+)?\s*\|\s*(.+?)\s*\|"
        deps = re.findall(dep_pattern, response, re.IGNORECASE)
        artifacts["dependencies"] = [
            {"package": d[0].strip(), "version": d[1].strip(), "purpose": d[2].strip()}
            for d in deps if d[0].strip() and not d[0].strip().startswith("...")
        ]
        
        # Extract section headers
        section_pattern = r"##\s+(.+)"
        sections = re.findall(section_pattern, response)
        artifacts["sections"] = sections
        
        return artifacts
    
    async def refine_plan(
        self,
        context: AgentContext,
        feedback: str,
        current_plan: str
    ) -> AgentResult:
        """Refine an existing plan based on feedback."""
        prompt = f"""You created this plan:

{current_plan[:3000]}

USER FEEDBACK:
{feedback}

Refine the plan to address this feedback. Output the complete updated plan."""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        
        start_time = __import__("time").time()
        
        try:
            response, tokens = await self._call_ai(messages, temperature=0.7)
            
            return AgentResult(
                success=True,
                output=response,
                artifacts=self._parse_plan(response),
                tokens_used=tokens,
                execution_time=__import__("time").time() - start_time,
            )
        except Exception as e:
            return AgentResult(
                success=False,
                output="",
                errors=[str(e)],
            )
