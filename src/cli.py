"""CLI entry point for noGojira - starts MCP + Web UI."""

import subprocess
import sys
import threading
from pathlib import Path


def main():
    """
    Start noGojira: MCP Server (stdio) + Web UI (http://localhost:3000).
    
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
    print("🌐 Starting Web UI at http://localhost:3000", file=sys.stderr)
    
    def run_web():
        try:
            # Get project root directory
            project_root = Path(__file__).parent.parent
            
            # Run reflex in the project directory
            # Keep stderr visible to see any errors
            subprocess.run(
                ["reflex", "run", "--loglevel", "warning"],
                cwd=project_root,
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
