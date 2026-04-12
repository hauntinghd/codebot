"""
Intelligent Live Preview System
Auto-detects browser-previewable projects and enables live preview
"""

import os
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json


class ProjectDetector:
    """
    Detects project type and determines if live preview should be enabled
    """

    # Browser-compatible project types
    PREVIEWABLE_TYPES = {
        "react": {
            "indicators": ["package.json", "src/App.jsx", "src/App.tsx", "vite.config", "webpack.config"],
            "frameworks": ["vite", "create-react-app", "next.js"],
            "confidence_threshold": 0.7,
        },
        "vue": {
            "indicators": ["package.json", "src/App.vue", "vite.config", "vue.config"],
            "frameworks": ["vite", "vue-cli"],
            "confidence_threshold": 0.7,
        },
        "static_html": {
            "indicators": ["index.html", "style.css", "main.js"],
            "frameworks": [],
            "confidence_threshold": 0.5,
        },
        "vanilla_js": {
            "indicators": ["index.html", "*.js", "package.json"],
            "frameworks": ["vite", "webpack", "parcel"],
            "confidence_threshold": 0.6,
        },
        "svelte": {
            "indicators": ["package.json", "src/App.svelte", "vite.config"],
            "frameworks": ["vite", "sveltekit"],
            "confidence_threshold": 0.7,
        },
    }

    # Projects that should NOT show preview
    EXCLUDED_TYPES = [
        "desktop_app",  # Electron, Tauri, PyQt, etc
        "vtuber_software",  # VTuber/avatar software
        "game",  # Unity, Unreal, Steam games
        "vscode_extension",  # VS Code extensions
        "cli_tool",  # Command-line tools
        "backend_only",  # Pure backend APIs
        "mobile_app",  # React Native, Flutter
        "python_script",  # Python scripts without web UI
    ]

    EXCLUSION_PATTERNS = {
        "desktop_app": ["electron", "tauri", "pyqt", "tkinter", "wxpython", "electron-builder"],
        "vtuber_software": ["vtuber", "avatar", "live2d", "vtube studio", "facial tracking"],
        "game": ["unity", "unreal", "steam", "game engine", "phaser", "three.js game"],
        "vscode_extension": ["vscode:prepublish", "@types/vscode", "vscode-languageclient"],
        "cli_tool": ["commander", "inquirer", "yargs", "argparse", "click", "#!/usr/bin/env"],
        "backend_only": ["express", "fastapi", "flask", "django", "nest.js", "no frontend"],
        "mobile_app": ["react-native", "flutter", "expo", "capacitor", "cordova"],
        "python_script": [".py files only", "no html", "no web framework"],
    }

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.files = self._list_project_files()

    def _list_project_files(self) -> List[str]:
        """List all files in project (relative paths)"""
        files = []
        try:
            for root, dirs, filenames in os.walk(self.project_path):
                # Skip node_modules, .git, etc
                dirs[:] = [d for d in dirs if d not in ["node_modules", ".git", "dist", "build", "__pycache__"]]
                for filename in filenames:
                    rel_path = os.path.relpath(os.path.join(root, filename), self.project_path)
                    files.append(rel_path)
        except Exception as e:
            print(f"[PREVIEW] Error listing files: {e}")
        return files

    async def detect(self) -> Dict:
        """
        Main detection function
        Returns: {
            'previewable': bool,
            'type': str,
            'confidence': float,
            'framework': str,
            'entry_point': str,
            'reason': str
        }
        """
        # First check exclusions
        exclusion_result = self._check_exclusions()
        if exclusion_result["excluded"]:
            return {
                "previewable": False,
                "type": exclusion_result["type"],
                "confidence": exclusion_result["confidence"],
                "framework": None,
                "entry_point": None,
                "reason": exclusion_result["reason"],
            }

        # Then check previewable types
        best_match = None
        best_score = 0.0

        for proj_type, config in self.PREVIEWABLE_TYPES.items():
            score, framework, entry = self._calculate_match_score(proj_type, config)
            if score > best_score:
                best_score = score
                best_match = {
                    "type": proj_type,
                    "framework": framework,
                    "entry_point": entry,
                    "confidence": score,
                }

        if best_match and best_score >= self.PREVIEWABLE_TYPES[best_match["type"]]["confidence_threshold"]:
            return {
                "previewable": True,
                **best_match,
                "reason": f"Detected {best_match['type']} project with {best_match['framework'] or 'no framework'}",
            }

        return {
            "previewable": False,
            "type": "unknown",
            "confidence": 0.0,
            "framework": None,
            "entry_point": None,
            "reason": "Could not detect a browser-previewable project type",
        }

    def _check_exclusions(self) -> Dict:
        """Check if project matches exclusion patterns"""
        # Read package.json if exists
        package_json = self._read_package_json()
        
        # Read first few Python files
        py_files_content = self._read_python_files(max_files=3)
        
        # Combine all text for pattern matching
        all_text = json.dumps(package_json) + "\n" + "\n".join(py_files_content) + "\n" + "\n".join(self.files)
        all_text_lower = all_text.lower()

        for exc_type, patterns in self.EXCLUSION_PATTERNS.items():
            matches = sum(1 for pattern in patterns if pattern in all_text_lower)
            if matches >= 2:  # At least 2 patterns must match
                return {
                    "excluded": True,
                    "type": exc_type,
                    "confidence": min(1.0, matches * 0.3),
                    "reason": f"Detected as {exc_type.replace('_', ' ')} (not previewable in browser)",
                }

        return {"excluded": False}

    def _calculate_match_score(self, proj_type: str, config: Dict) -> Tuple[float, Optional[str], Optional[str]]:
        """Calculate confidence score for a project type"""
        score = 0.0
        framework = None
        entry_point = None

        # Check file indicators
        for indicator in config["indicators"]:
            if "*" in indicator:
                # Glob pattern
                pattern = indicator.replace("*", ".*")
                matches = [f for f in self.files if re.match(pattern, f)]
                if matches:
                    score += 0.2
                    if not entry_point and indicator.endswith(".html"):
                        entry_point = matches[0]
            else:
                # Exact match
                if any(indicator in f for f in self.files):
                    score += 0.2
                    if not entry_point and indicator == "index.html":
                        entry_point = indicator

        # Check framework indicators in package.json
        package_json = self._read_package_json()
        if package_json:
            deps = {**package_json.get("dependencies", {}), **package_json.get("devDependencies", {})}
            for fw in config["frameworks"]:
                if fw in deps or fw in str(package_json.get("scripts", {})):
                    score += 0.3
                    framework = fw
                    break

        # Bonus for HTML + JS combo
        has_html = any(f.endswith(".html") for f in self.files)
        has_js = any(f.endswith((".js", ".jsx", ".ts", ".tsx")) for f in self.files)
        if has_html and has_js:
            score += 0.1

        return score, framework, entry_point

    def _read_package_json(self) -> Dict:
        """Read and parse package.json"""
        try:
            package_path = self.project_path / "package.json"
            if package_path.exists():
                with open(package_path) as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _read_python_files(self, max_files: int = 3) -> List[str]:
        """Read content of first N Python files for pattern matching"""
        contents = []
        py_files = [f for f in self.files if f.endswith(".py")][:max_files]
        
        for py_file in py_files:
            try:
                with open(self.project_path / py_file) as f:
                    contents.append(f.read(2000))  # First 2000 chars
            except Exception:
                pass
        
        return contents


class LivePreviewManager:
    """
    Manages live preview sessions for previewable projects
    """

    def __init__(self):
        self.active_previews = {}  # {project_id: preview_config}

    async def create_preview(self, project_id: str, project_path: str, user_id: str) -> Dict:
        """
        Create a live preview session
        Returns preview URL and configuration
        """
        detector = ProjectDetector(project_path)
        detection = await detector.detect()

        if not detection["previewable"]:
            return {
                "success": False,
                "error": detection["reason"],
                "previewable": False,
            }

        # Generate preview configuration
        preview_config = {
            "project_id": project_id,
            "user_id": user_id,
            "type": detection["type"],
            "framework": detection["framework"],
            "entry_point": detection["entry_point"] or "index.html",
            "port": self._allocate_port(),
            "created_at": None,  # Set by caller
        }

        self.active_previews[project_id] = preview_config

        return {
            "success": True,
            "previewable": True,
            "preview_url": f"/preview/{project_id}",
            "config": preview_config,
            "detection": detection,
        }

    def _allocate_port(self) -> int:
        """Allocate available port for preview server"""
        # In production, track used ports
        # For now, use range 8100-8199
        used_ports = {cfg["port"] for cfg in self.active_previews.values()}
        for port in range(8100, 8200):
            if port not in used_ports:
                return port
        return 8100  # Fallback

    async def stop_preview(self, project_id: str):
        """Stop a preview session"""
        if project_id in self.active_previews:
            del self.active_previews[project_id]

    def get_preview_status(self, project_id: str) -> Optional[Dict]:
        """Get status of a preview session"""
        return self.active_previews.get(project_id)


# Global instance
preview_manager = LivePreviewManager()
