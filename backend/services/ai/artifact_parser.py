"""Artifact Parser for CodeBot Architecture Mode.

Parses the <artifact> and <action> XML-like tags from AI responses
and converts them into executable operations.

This parser is designed to be model-agnostic, supporting future
migration to custom fine-tuned models.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Literal
from enum import Enum


class ActionType(Enum):
    FILE = "file"
    COMMAND = "command"
    START = "start"


@dataclass
class Action:
    """A single action to execute."""
    type: ActionType
    content: str
    path: Optional[str] = None  # For file actions
    
    def __repr__(self) -> str:
        if self.type == ActionType.FILE:
            return f"Action(FILE, {self.path}, {len(self.content)} chars)"
        return f"Action({self.type.value}, {self.content[:50]}...)"


@dataclass
class Artifact:
    """A complete artifact with all its actions."""
    id: str
    title: str
    actions: List[Action] = field(default_factory=list)
    
    def get_files(self) -> List[tuple[str, str]]:
        """Get all file actions as (path, content) tuples."""
        return [
            (a.path, a.content) 
            for a in self.actions 
            if a.type == ActionType.FILE and a.path
        ]
    
    def get_commands(self) -> List[str]:
        """Get all command actions."""
        return [
            a.content 
            for a in self.actions 
            if a.type == ActionType.COMMAND
        ]


@dataclass 
class Plan:
    """Parsed planning section."""
    raw: str
    project_structure: str = ""
    data_model: str = ""
    component_hierarchy: str = ""
    state_management: str = ""
    api_design: str = ""
    dependencies: str = ""
    potential_issues: str = ""


@dataclass
class ParseResult:
    """Complete parse result."""
    plan: Optional[Plan] = None
    artifact: Optional[Artifact] = None
    validation_issues: List[str] = field(default_factory=list)
    raw_response: str = ""


class ArtifactParser:
    """Parser for CodeBot artifact format.
    
    Handles streaming and complete responses.
    Extracts <plan>, <artifact>, <action>, and <validation> sections.
    """
    
    # Regex patterns for parsing
    PLAN_PATTERN = re.compile(
        r'<plan>(.*?)</plan>',
        re.DOTALL | re.IGNORECASE
    )
    
    ARTIFACT_PATTERN = re.compile(
        r'<artifact\s+id=["\']([^"\']+)["\']\s+title=["\']([^"\']+)["\']>(.*?)</artifact>',
        re.DOTALL | re.IGNORECASE
    )
    
    ACTION_FILE_PATTERN = re.compile(
        r'<action\s+type=["\']file["\']\s+path=["\']([^"\']+)["\']>(.*?)</action>',
        re.DOTALL | re.IGNORECASE
    )
    
    ACTION_COMMAND_PATTERN = re.compile(
        r'<action\s+type=["\']command["\']>(.*?)</action>',
        re.DOTALL | re.IGNORECASE
    )
    
    VALIDATION_PATTERN = re.compile(
        r'<validation>(.*?)</validation>',
        re.DOTALL | re.IGNORECASE
    )
    
    # Section patterns for plan parsing
    SECTION_PATTERNS = {
        'project_structure': re.compile(r'###\s*1\.\s*Project Structure\s*(.*?)(?=###|\Z)', re.DOTALL),
        'data_model': re.compile(r'###\s*2\.\s*Data Model\s*(.*?)(?=###|\Z)', re.DOTALL),
        'component_hierarchy': re.compile(r'###\s*3\.\s*Component Hierarchy\s*(.*?)(?=###|\Z)', re.DOTALL),
        'state_management': re.compile(r'###\s*4\.\s*State Management\s*(.*?)(?=###|\Z)', re.DOTALL),
        'api_design': re.compile(r'###\s*5\.\s*API Design\s*(.*?)(?=###|\Z)', re.DOTALL),
        'dependencies': re.compile(r'###\s*6\.\s*Dependencies\s*(.*?)(?=###|\Z)', re.DOTALL),
        'potential_issues': re.compile(r'###\s*7\.\s*Potential Issues\s*(.*?)(?=###|\Z)', re.DOTALL),
    }
    
    def __init__(self):
        self.buffer = ""
        self.result = ParseResult()
    
    def feed(self, chunk: str) -> None:
        """Feed a chunk of streaming response."""
        self.buffer += chunk
    
    def parse(self, response: Optional[str] = None) -> ParseResult:
        """Parse the complete response or buffered content."""
        content = response if response else self.buffer
        self.result.raw_response = content
        
        # Parse plan section
        self._parse_plan(content)
        
        # Parse artifact section
        self._parse_artifact(content)
        
        # Parse validation section
        self._parse_validation(content)
        
        return self.result
    
    def _parse_plan(self, content: str) -> None:
        """Extract and parse the planning section."""
        match = self.PLAN_PATTERN.search(content)
        if not match:
            return
        
        plan_content = match.group(1).strip()
        plan = Plan(raw=plan_content)
        
        # Extract each section
        for section_name, pattern in self.SECTION_PATTERNS.items():
            section_match = pattern.search(plan_content)
            if section_match:
                setattr(plan, section_name, section_match.group(1).strip())
        
        self.result.plan = plan
    
    def _parse_artifact(self, content: str) -> None:
        """Extract and parse the artifact section."""
        match = self.ARTIFACT_PATTERN.search(content)
        if not match:
            return
        
        artifact_id = match.group(1)
        artifact_title = match.group(2)
        artifact_content = match.group(3)
        
        artifact = Artifact(id=artifact_id, title=artifact_title)
        
        # Find all actions in order
        actions = []
        
        # Find file actions with their positions
        for file_match in self.ACTION_FILE_PATTERN.finditer(artifact_content):
            path = file_match.group(1)
            file_content = file_match.group(2).strip()
            actions.append((
                file_match.start(),
                Action(type=ActionType.FILE, path=path, content=file_content)
            ))
        
        # Find command actions with their positions
        for cmd_match in self.ACTION_COMMAND_PATTERN.finditer(artifact_content):
            command = cmd_match.group(1).strip()
            actions.append((
                cmd_match.start(),
                Action(type=ActionType.COMMAND, content=command)
            ))
        
        # Sort by position to maintain order
        actions.sort(key=lambda x: x[0])
        artifact.actions = [a[1] for a in actions]
        
        self.result.artifact = artifact
    
    def _parse_validation(self, content: str) -> None:
        """Extract validation issues."""
        match = self.VALIDATION_PATTERN.search(content)
        if not match:
            return
        
        validation_content = match.group(1).strip()
        
        if validation_content.upper() == "NO_ISSUES":
            self.result.validation_issues = []
        else:
            # Split by newlines and filter empty lines
            issues = [
                line.strip() 
                for line in validation_content.split('\n') 
                if line.strip()
            ]
            self.result.validation_issues = issues
    
    def reset(self) -> None:
        """Reset the parser for a new response."""
        self.buffer = ""
        self.result = ParseResult()


class StreamingArtifactParser:
    """Streaming parser that emits events as content is parsed.
    
    Useful for real-time UI updates as the AI generates content.
    """
    
    def __init__(self, on_plan_start=None, on_plan_section=None, 
                 on_artifact_start=None, on_file_start=None, on_file_content=None,
                 on_file_end=None, on_command=None, on_artifact_end=None):
        self.buffer = ""
        self.in_plan = False
        self.in_artifact = False
        self.in_file = False
        self.in_command = False
        self.current_file_path = None
        self.current_file_content = ""
        
        # Callbacks
        self.on_plan_start = on_plan_start or (lambda: None)
        self.on_plan_section = on_plan_section or (lambda section, content: None)
        self.on_artifact_start = on_artifact_start or (lambda id, title: None)
        self.on_file_start = on_file_start or (lambda path: None)
        self.on_file_content = on_file_content or (lambda path, chunk: None)
        self.on_file_end = on_file_end or (lambda path, content: None)
        self.on_command = on_command or (lambda cmd: None)
        self.on_artifact_end = on_artifact_end or (lambda: None)
    
    def feed(self, chunk: str) -> None:
        """Feed a chunk and emit events."""
        self.buffer += chunk
        self._process_buffer()
    
    def _process_buffer(self) -> None:
        """Process buffer and emit events for complete elements."""
        # Check for plan start
        if not self.in_plan and '<plan>' in self.buffer:
            self.in_plan = True
            self.on_plan_start()
        
        # Check for plan end
        if self.in_plan and '</plan>' in self.buffer:
            self.in_plan = False
            # Extract plan content and emit sections
            match = re.search(r'<plan>(.*?)</plan>', self.buffer, re.DOTALL)
            if match:
                plan_content = match.group(1)
                # Emit each section found
                sections = [
                    ('structure', r'### 1\. Project Structure'),
                    ('data', r'### 2\. Data Model'),
                    ('components', r'### 3\. Component Hierarchy'),
                    ('state', r'### 4\. State Management'),
                    ('api', r'### 5\. API Design'),
                    ('deps', r'### 6\. Dependencies'),
                    ('issues', r'### 7\. Potential Issues'),
                ]
                for section_id, pattern in sections:
                    if re.search(pattern, plan_content):
                        self.on_plan_section(section_id, "completed")
        
        # Check for artifact start
        artifact_start = re.search(
            r'<artifact\s+id=["\']([^"\']+)["\']\s+title=["\']([^"\']+)["\']>',
            self.buffer
        )
        if artifact_start and not self.in_artifact:
            self.in_artifact = True
            self.on_artifact_start(artifact_start.group(1), artifact_start.group(2))
        
        # Check for file actions
        if self.in_artifact:
            # Look for complete file actions
            file_pattern = re.compile(
                r'<action\s+type=["\']file["\']\s+path=["\']([^"\']+)["\']>(.*?)</action>',
                re.DOTALL
            )
            for match in file_pattern.finditer(self.buffer):
                path = match.group(1)
                content = match.group(2).strip()
                self.on_file_start(path)
                self.on_file_end(path, content)
            
            # Look for command actions
            cmd_pattern = re.compile(
                r'<action\s+type=["\']command["\']>(.*?)</action>',
                re.DOTALL
            )
            for match in cmd_pattern.finditer(self.buffer):
                self.on_command(match.group(1).strip())
        
        # Check for artifact end
        if self.in_artifact and '</artifact>' in self.buffer:
            self.in_artifact = False
            self.on_artifact_end()


def parse_response(response: str) -> ParseResult:
    """Convenience function to parse a complete response."""
    parser = ArtifactParser()
    return parser.parse(response)


def extract_files(response: str) -> List[tuple[str, str]]:
    """Extract all files from a response as (path, content) tuples."""
    result = parse_response(response)
    if result.artifact:
        return result.artifact.get_files()
    return []


def extract_commands(response: str) -> List[str]:
    """Extract all commands from a response."""
    result = parse_response(response)
    if result.artifact:
        return result.artifact.get_commands()
    return []
