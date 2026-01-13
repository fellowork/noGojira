"""CLI entry point for noGojira - starts MCP + Web UI."""

import os
import subprocess
import sys
import threading
from pathlib import Path


def main():
    """
    Start noGojira: MCP Server (stdio) + Web UI (http://localhost:8383).
    
    This is the default command when called from MCP clients like Claude Desktop.
    No arguments needed, everything just works.
    """
    # Print to stderr so it doesn't interfere with MCP stdio
    print("=" * 60, file=sys.stderr)
    print("  🦖 noGojira", file=sys.stderr)
    print("  ノーゴージラ (Nō-Gō-Jira)", file=sys.stderr)
    print('  "Kill the monster. Ship the code."', file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("", file=sys.stderr)
    
    # Start Web UI in background thread using reflex run
    print("🌐 Starting Web UI at http://localhost:8383", file=sys.stderr)
    
    def run_web():
        try:
            # Get project root directory (where rxconfig.py is located)
            project_root = Path(__file__).parent.parent
            
            # Debug: Print the path we're using
            print(f"📂 Project root: {project_root}", file=sys.stderr)
            print(f"📄 rxconfig.py exists: {(project_root / 'rxconfig.py').exists()}", file=sys.stderr)
            
            # Ensure the package directory is in PYTHONPATH
            env = os.environ.copy()
            pythonpath = str(project_root)
            if 'PYTHONPATH' in env:
                pythonpath = f"{pythonpath}{os.pathsep}{env['PYTHONPATH']}"
            env['PYTHONPATH'] = pythonpath
            
            # Run reflex in the project directory
            # Keep stderr visible to see any errors
            subprocess.run(
                ["reflex", "run", "--loglevel", "warning"],
                cwd=str(project_root),  # Ensure it's a string
                env=env,
                stderr=sys.stderr,
            )
        except Exception as e:
            print(f"⚠️  Web UI error: {e}", file=sys.stderr)
    
    web_thread = threading.Thread(target=run_web, daemon=True, name="WebUI")
    web_thread.start()
    
    # Start MCP server in main thread (needs stdio)
    print("🚀 Starting MCP Server", file=sys.stderr)
    print("📡 Ready for AI agent connections", file=sys.stderr)
    print("", file=sys.stderr)
    
    from .server import run
    run()


if __name__ == "__main__":
    main()
