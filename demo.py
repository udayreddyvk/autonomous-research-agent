#!/usr/bin/env python3
"""
Demonstration script showing agent swarm in action.
"""

import asyncio
import json
import sys
from datetime import datetime
from swarm_orchestrator import orchestrator
from phase_agents import run_research_swarm

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


async def demo():
    """Run a demonstration research session."""

    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║     🔬 Autonomous Research Agent - DEMO                     ║
    ║                                                              ║
    ║        Agent Swarm Coordination Demonstration               ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    # Create a research session
    print("\n📝 Creating research session...")
    topic = "Impact of AI on software engineering jobs"
    session_id = orchestrator.create_session(
        topic=topic,
        depth=3,
        verify=True,
        model="deepseek/deepseek-v4-pro"
    )
    print(f"✓ Created session: {session_id}")

    # Display session info
    session = orchestrator.get_session(session_id)
    print(f"\n📊 Session Configuration:")
    print(f"   Topic: {session.topic}")
    print(f"   Depth: {session.depth}")
    print(f"   Verification: {session.verify}")
    print(f"   Model: {session.model}")

    # Run the swarm
    print(f"\n🚀 Starting agent swarm execution...")
    print(f"   Sequential phases: 1 → 2 → 3 → 4")

    success = await run_research_swarm(session_id)

    # Display final results
    print(f"\n{'='*60}")
    session = orchestrator.get_session(session_id)

    if success:
        print("✅ RESEARCH COMPLETE")
    else:
        print("❌ RESEARCH FAILED")

    print(f"\n📈 Final Statistics:")
    print(f"   Status: {session.status}")
    print(f"   Phase: {session.phase}")
    print(f"   Evidence collected: {len(session.evidence_bank)}")
    print(f"   Errors: {len(session.errors)}")

    # Display evidence
    if session.evidence_bank:
        print(f"\n📚 Evidence Bank ({len(session.evidence_bank)} claims):")
        for i, claim in enumerate(session.evidence_bank[:5], 1):
            print(f"\n   {i}. {claim['claim']}")
            print(f"      Source: {claim['source_url']}")
            print(f"      Confidence: {claim['confidence']}")

        if len(session.evidence_bank) > 5:
            print(f"\n   ... and {len(session.evidence_bank) - 5} more claims")

    # Display phase progress
    print(f"\n📊 Phase Progress:")
    for phase_name, phase_data in session.progress.items():
        status = phase_data.get("status", "pending")
        icon = "✓" if status == "completed" else "✗" if status == "failed" else "→"
        print(f"   [{icon}] {phase_name}: {status}")

    # Display errors if any
    if session.errors:
        print(f"\n⚠️  Errors ({len(session.errors)}):")
        for error in session.errors:
            print(f"   - {error.get('error')}")

    # Display report path
    if session.progress.get("phase_3", {}).get("report_path"):
        report_path = session.progress["phase_3"]["report_path"]
        print(f"\n📄 Report saved to:")
        print(f"   {report_path}")

        # Show first few lines
        try:
            with open(report_path, "r") as f:
                lines = f.readlines()[:10]
                print(f"\n📖 Report Preview:")
                for line in lines:
                    print(f"   {line.rstrip()}")
                if len(lines) >= 10:
                    print(f"   ...")
        except FileNotFoundError:
            print("   (Report file not found)")

    print(f"\n{'='*60}")
    print(f"\n🎯 Demo Complete!")
    print(f"\nNext Steps:")
    print(f"1. Start the web server: python start.py")
    print(f"2. Open dashboard: http://localhost:8000")
    print(f"3. View session: {session_id}")
    print(f"\n")


if __name__ == "__main__":
    asyncio.run(demo())
