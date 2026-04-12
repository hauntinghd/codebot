"""Paced streaming response handler for Architecture mode.

This module provides Bolt.new-style paced, deliberate streaming responses
that make the AI feel more thoughtful and professional.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import AsyncGenerator, Optional

logger = logging.getLogger("codebot")


# Timing configurations for different response types
class PacingConfig:
    """Configuration for response pacing timing."""
    
    # Planning mode - thoughtful, measured pace
    PLANNING = {
        "initial_delay": 0.3,      # Delay before first character
        "char_delay_min": 0.008,   # Min delay between characters
        "char_delay_max": 0.025,   # Max delay between characters
        "word_pause": 0.05,        # Extra pause after words
        "sentence_pause": 0.15,    # Extra pause after sentences
        "paragraph_pause": 0.3,    # Extra pause after paragraphs
        "thinking_delay": 0.8,     # Delay for "thinking" indicator
    }
    
    # Build mode - faster but still deliberate
    BUILD = {
        "initial_delay": 0.2,
        "char_delay_min": 0.003,
        "char_delay_max": 0.012,
        "word_pause": 0.02,
        "sentence_pause": 0.08,
        "paragraph_pause": 0.15,
        "step_delay": 0.4,         # Delay between build steps
    }
    
    # Iteration mode - quick and responsive
    ITERATION = {
        "initial_delay": 0.15,
        "char_delay_min": 0.002,
        "char_delay_max": 0.008,
        "word_pause": 0.015,
        "sentence_pause": 0.05,
        "paragraph_pause": 0.1,
    }


async def stream_paced_text(
    text: str,
    config: dict = None,
    chunk_size: int = 1
) -> AsyncGenerator[str, None]:
    """
    Stream text character-by-character with natural pacing.
    
    This creates the Bolt.new-style effect where text appears
    gradually as if being typed by a thoughtful AI.
    
    Args:
        text: The full text to stream
        config: Pacing configuration (defaults to PLANNING)
        chunk_size: Number of characters per chunk (1 for smoothest)
    
    Yields:
        Characters or small chunks of text
    """
    if config is None:
        config = PacingConfig.PLANNING
    
    # Initial thinking delay
    await asyncio.sleep(config.get("initial_delay", 0.3))
    
    i = 0
    while i < len(text):
        # Get next chunk
        chunk = text[i:i + chunk_size]
        yield chunk
        
        # Calculate delay based on what we just sent
        last_char = chunk[-1] if chunk else ""
        
        if last_char in ".!?":
            # End of sentence - longer pause
            delay = config.get("sentence_pause", 0.15)
        elif last_char in ",;:":
            # Punctuation - medium pause
            delay = config.get("word_pause", 0.05) * 1.5
        elif last_char == " ":
            # Word boundary - small pause
            delay = config.get("word_pause", 0.05)
        elif last_char == "\n":
            # Line break - check for paragraph
            if i + 1 < len(text) and text[i + 1] == "\n":
                delay = config.get("paragraph_pause", 0.3)
            else:
                delay = config.get("sentence_pause", 0.15)
        else:
            # Regular character - random delay in range
            delay = random.uniform(
                config.get("char_delay_min", 0.008),
                config.get("char_delay_max", 0.025)
            )
        
        await asyncio.sleep(delay)
        i += chunk_size


async def stream_planning_response(
    response_text: str,
    project_id: str
) -> AsyncGenerator[str, None]:
    """
    Stream a planning response with SSE formatting and pacing.
    
    Args:
        response_text: The AI's planning response
        project_id: The project ID for context
    
    Yields:
        SSE-formatted chunks for the frontend
    """
    config = PacingConfig.PLANNING
    
    # Initial thinking indicator
    yield f"data: {json.dumps({'type': 'thinking', 'message': 'Analyzing your request...'})}\n\n"
    await asyncio.sleep(config["thinking_delay"])
    
    # Stream the response character by character
    buffer = ""
    async for char in stream_paced_text(response_text, config):
        buffer += char
        yield f"data: {json.dumps({'type': 'content', 'chunk': char, 'buffer': buffer})}\n\n"
    
    # Signal completion
    yield f"data: {json.dumps({'type': 'done', 'full_response': response_text})}\n\n"


async def stream_build_progress(
    steps: list,
    project_id: str
) -> AsyncGenerator[str, None]:
    """
    Stream build progress with deliberate pacing.
    
    Args:
        steps: List of build step dictionaries with 'message', 'progress'
        project_id: The project ID
    
    Yields:
        SSE-formatted build progress updates
    """
    config = PacingConfig.BUILD
    
    for step in steps:
        # Yield the step
        yield f"data: {json.dumps(step)}\n\n"
        
        # Calculate delay based on step type
        step_name = step.get("step", "")
        if step_name in ["ai_router", "ai_engineer", "ai_auditor"]:
            # AI steps take longer
            delay = config["step_delay"] * 2
        elif step_name == "init":
            delay = config["step_delay"]
        elif step_name in ["done", "error"]:
            delay = 0.1  # Quick completion signal
        else:
            delay = config["step_delay"]
        
        await asyncio.sleep(delay)


async def stream_build_log_message(
    message: str,
    step: str,
    progress: int
) -> AsyncGenerator[str, None]:
    """
    Stream a single build log message with typing effect.
    
    Args:
        message: The log message
        step: The step identifier
        progress: Progress percentage
    
    Yields:
        SSE-formatted log chunks
    """
    config = PacingConfig.BUILD
    
    # Stream message character by character for terminal feel
    buffer = ""
    async for char in stream_paced_text(message, config, chunk_size=2):
        buffer += char
        yield f"data: {json.dumps({'step': step, 'message': buffer, 'progress': progress, 'streaming': True})}\n\n"
    
    # Final message
    yield f"data: {json.dumps({'step': step, 'message': message, 'progress': progress, 'streaming': False})}\n\n"


class PacedResponseBuilder:
    """Helper class to build paced responses with consistent timing."""
    
    def __init__(self, mode: str = "planning"):
        """
        Initialize with a pacing mode.
        
        Args:
            mode: One of 'planning', 'build', 'iteration'
        """
        self.mode = mode
        if mode == "build":
            self.config = PacingConfig.BUILD
        elif mode == "iteration":
            self.config = PacingConfig.ITERATION
        else:
            self.config = PacingConfig.PLANNING
        
        self.accumulated_text = ""
    
    async def stream_text(self, text: str) -> AsyncGenerator[dict, None]:
        """
        Stream text with appropriate pacing.
        
        Args:
            text: Text to stream
        
        Yields:
            Dictionary with chunk and accumulated text
        """
        async for char in stream_paced_text(text, self.config):
            self.accumulated_text += char
            yield {
                "chunk": char,
                "accumulated": self.accumulated_text
            }
    
    async def pause(self, duration: Optional[float] = None):
        """
        Add a pause in the stream.
        
        Args:
            duration: Override duration, or use config default
        """
        if duration is None:
            duration = self.config.get("sentence_pause", 0.15)
        await asyncio.sleep(duration)
    
    def get_accumulated(self) -> str:
        """Get all accumulated text."""
        return self.accumulated_text
    
    def reset(self):
        """Reset accumulated text."""
        self.accumulated_text = ""
