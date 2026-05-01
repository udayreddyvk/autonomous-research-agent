#!/usr/bin/env python3
"""
Startup script for Autonomous Research Agent.
"""

import subprocess
import sys
import time
import webbrowser
from pathlib import Path
import platform

def main():
    print("""
    ========================================================
    Autonomous Research Agent \u2014 Sci-Fi Edition

    Initializing probe arrays & holographic interface...
    ========================================================
    """)

    # Check Python version
    if sys.version_info < (3, 8):
        print("[ERROR] Python 3.8+ required")
        sys.exit(1)

    # Check dependencies
    print("\n[*] Verifying neural core integrity...")
    try:
        import fastapi
        import uvicorn
        import pydantic
        print("[+] Core systems online")
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        print("\nInstall with:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

    # Create required directories
    print("\n[*] Establishing data vaults...")
    Path("logs").mkdir(exist_ok=True)
    Path("reports").mkdir(exist_ok=True)
    Path("ui").mkdir(exist_ok=True)
    print("[+] Vaults secured")

    # Check .env
    print("\n[*] Scanning configuration matrices...")
    if not Path(".env").exists():
        print("[!] .env file not found")
        print("\nCreate a .env file with:")
        print("  KIMI_API_URL=https://openrouter.ai/api/v1")
        print("  KIMI_API_KEY=your_openrouter_api_key_here")
        print("  KIMI_MODEL=deepseek/deepseek-v4-pro")
        print("\nContinuing without an API key will use fallback report behavior.")
    else:
        print("[+] Configuration matrices loaded")

    # Start server
    print("\n[*] Powering up neural interface...")
    print("    Holographic Interface: http://localhost:8000")
    print("    Core API: http://localhost:8000/docs")
    print("\n    Press Ctrl+C to stop\n")

    try:
        # Wait a moment for the message to display
        time.sleep(1)

        # Try to open browser
        try:
            webbrowser.open("http://localhost:8000", new=2)
            print("[+] Opening holographic interface...\n")
        except:
            print("[*] Open http://localhost:8000 in your visor\n")

        # Start the server
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "backend:app",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--reload"
        ])

    except KeyboardInterrupt:
        print("\n\n[*] Server stopped by user")
        print("[*] Goodbye!\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
