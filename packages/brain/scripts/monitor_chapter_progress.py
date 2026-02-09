#!/usr/bin/env python3
"""
Monitor Chapter Processing Progress
====================================

Real-time monitoring of parallel chapter processing progress.
Shows completion percentage, time elapsed, and estimated remaining time.
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Config
OUTPUT_DIR = Path("/tmp/claude-1000/-home-papi-Documents-mu2-cognitive-os/tasks")
PROGRESS_FILE = Path("/home/papi/Documents/mu2-cognitive-os/packages/brain/data/openstax/embeddings/processing_progress.json")
EMBEDDINGS_DIR = Path("/home/papi/Documents/mu2-cognitive-os/packages/brain/data/openstax/embeddings")


def get_background_output():
    """Read the background task output"""
    output_file = OUTPUT_DIR / "b5d4650.output"
    if output_file.exists():
        with open(output_file, 'r') as f:
            return f.read()
    return ""


def parse_progress_from_output(output: str) -> dict:
    """Parse progress from background task output"""
    lines = output.split('\n')

    completed = []
    failed = []
    current_status = {}

    for line in lines:
        if "Progress:" in line and "Current:" in line:
            try:
                # Extract progress info
                parts = line.split()
                for i, part in enumerate(parts):
                    if "/" in part and "%" in part:
                        progress_info = part.strip()
                        current_status["progress"] = progress_info
                    elif "Current:" in part or i > 0:
                        current_chapter = parts[-1] if "Current:" not in part else part.split("Current:")[-1].strip()
                        current_status["current_chapter"] = current_chapter
            except:
                pass

        if "✓" in line and "Complete in" in line:
            try:
                chapter = line.split("[")[1].split("]")[0].strip()
                time_str = line.split("Complete in")[1].split("s")[0].strip()
                completed.append({
                    "chapter": chapter,
                    "time": float(time_str)
                })
            except:
                pass

        if "✗" in line and "Failed after" in line:
            try:
                chapter = line.split("[")[1].split("]")[0].strip()
                completed.append({
                    "chapter": chapter,
                    "failed": True
                })
            except:
                pass

    return {
        "completed": completed,
        "failed": failed,
        "current": current_status
    }


def get_chapter_count():
    """Get total number of chapters"""
    import subprocess
    result = subprocess.run(
        ["ls", "/tmp/openstax_chapters/AmericanGovernment3e_chapter*_Chapter_*.pdf"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        # Count actual chapter PDFs (full content files, not metadata)
        return len([line for line in result.stdout.split('\n') if line and '_Chapter_' in line and line.count('_') > 3])
    return 21


def display_progress():
    """Display current progress"""
    # Get background output
    output = get_background_output()

    # Parse progress
    progress_data = parse_progress_from_output(output)

    # Get total chapters
    total = get_chapter_count()
    completed = len(progress_data["completed"])
    failed = len([c for c in progress_data["completed"] if c.get("failed", False)])
    successful = completed - failed

    # Calculate percentage
    pct = (completed / total * 100) if total > 0 else 0

    # Clear screen and display
    print("\033[2J\033[H", end="")  # Clear screen
    print("=" * 70)
    print("OpenStax Chapter Processing Progress Monitor")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Progress bar
    bar_width = 50
    filled = int(bar_width * pct / 100)
    bar = "█" * filled + "░" * (bar_width - filled)
    print(f"Progress: [{bar}] {pct:.1f}%")
    print(f"Completed: {completed}/{total} chapters")
    print(f"  ✓ Successful: {successful}")
    print(f"  ✗ Failed: {failed}")
    print()

    # Current activity
    if progress_data["current"]:
        current = progress_data["current"]
        if "progress" in current:
            print(f"Current: {current.get('current_chapter', 'Processing...')}")
            print(f"Status: {current.get('progress', 'Initializing...')}")
    else:
        print("Status: Waiting for first chapter to complete...")

    print()

    # Recent completions
    if progress_data["completed"]:
        print("Recent Completions:")
        recent = progress_data["completed"][-5:]  # Last 5
        for item in reversed(recent):
            if item.get("failed"):
                print(f"  ✗ {item['chapter']}: FAILED")
            else:
                print(f"  ✓ {item['chapter']}: {item.get('time', 0):.1f}s")

    print()
    print("=" * 70)

    # Embedding files count
    embedding_files = list(EMBEDDINGS_DIR.glob("*_embeddings.json"))
    if embedding_files:
        print(f"Embedding files created: {len(embedding_files)}")
        print(f"Latest: {embedding_files[-1].name}")

    # Return True if monitoring should continue
    return completed < total


def main():
    """Main monitoring loop"""

    print("Starting progress monitor...")
    print("Press Ctrl+C to stop")
    print()

    try:
        while True:
            should_continue = display_progress()

            if not should_continue:
                print("\n✓ All chapters processed!")
                break

            time.sleep(10)  # Update every 10 seconds

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")


if __name__ == "__main__":
    main()
