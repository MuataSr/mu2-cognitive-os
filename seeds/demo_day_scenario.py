#!/usr/bin/env python3
"""
Mu2 Cognitive OS - Demo Day Scenario
=====================================

This script seeds the database with a clean, predictable demo narrative
for investor presentations featuring "Darius the Engineer."

Hardcoded Narrative:
- Student: "Darius Johnson" (Engineering Interest)
- Event 1: "Morning Circle" check-in with sentiment: 0.3 (Tired) -> Trigger Intervention
- Event 2: Math Sprint with mastery: 0.95 (Success)
- Event 3: PBL query about "Water Pumps" -> Returns OpenStax Ch 5 citation

Usage:
    python seeds/demo_day_scenario.py

Requirements:
    - Database must be running (docker-compose up -d)
    - psycopg2 or asyncpg installed
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add the brain package to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "brain"))

try:
    import asyncpg
    from src.services.mastery_engine import MasteryState, LearningEvent, mastery_engine
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure the database is running and dependencies are installed:")
    print("  pip install asyncpg")
    sys.exit(1)


# ============================================================================
# DEMO CONFIGURATION - The "Darius" Story
# ============================================================================

DEMO_STUDENT = {
    "user_id": "darius-johnson-001",
    "full_name": "Darius Johnson",
    "interest_area": "Engineering",
    "grade_level": 8,
}

DEMO_EVENTS = [
    {
        "name": "Morning Circle - Emotional Check-in",
        "description": "Darius arrives tired after late night studying",
        "sentiment_score": 0.3,  # Negative/Tired - triggers intervention
        "timestamp": (datetime.now() - timedelta(hours=4)).isoformat(),
        "expected_response": "System suggests Focus Mode and offers encouragement",
    },
    {
        "name": "Math Sprint - Quadratic Equations",
        "description": "Darius excels at math practice",
        "skill_id": "quadratic-equations-basics",
        "skill_name": "Quadratic Equations",
        "is_correct": True,
        "attempts": 1,
        "mastery_after": 0.95,  # High mastery - success story
        "timestamp": (datetime.now() - timedelta(hours=3)).isoformat(),
        "expected_response": "System celebrates achievement, suggests advanced challenges",
    },
    {
        "name": "PBL Inquiry - Water Pump Engineering",
        "description": "Darius asks about real-world engineering applications",
        "query": "How do water pumps work in engineering?",
        "expected_citation": "OpenStax College Physics, Chapter 5: Fluid Mechanics",
        "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
        "expected_response": "System returns textbook citation with practical examples",
    },
]


# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

async def get_db_connection():
    """Connect to the Mu2 Cognitive OS database"""
    try:
        conn = await asyncpg.connect(
            host="localhost",
            port=54322,
            user="postgres",
            password="",
            database="postgres"
        )
        return conn
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        print("Please ensure:")
        print("  1. docker-compose is running (docker-compose up -d)")
        print("  2. Database is accessible on localhost:54322")
        sys.exit(1)


async def wipe_demo_data(conn):
    """Clean any existing demo data to ensure clean slate"""
    print("\n[STEP 1] Wiping existing demo data...")

    await conn.execute("""
        DELETE FROM cortex.user_sessions
        WHERE user_id = $1
    """, DEMO_STUDENT["user_id"])

    await conn.execute("""
        DELETE FROM cortex.learning_events
        WHERE user_id = $1
    """, DEMO_STUDENT["user_id"])

    await conn.execute("""
        DELETE FROM cortex.mastery_states
        WHERE user_id = $1
    """, DEMO_STUDENT["user_id"])

    print(f"  Cleaned data for student: {DEMO_STUDENT['user_id']}")


async def create_student_session(conn):
    """Create the initial session for Darius"""
    print("\n[STEP 2] Creating student session...")

    session_id = await conn.fetchval("""
        INSERT INTO cortex.user_sessions (
            user_id,
            session_start,
            current_mode,
            focus_level,
            metadata
        ) VALUES (
            $1, NOW(), 'standard', 50,
            $2::jsonb
        )
        RETURNING id
    """, DEMO_STUDENT["user_id"], {
        "full_name": DEMO_STUDENT["full_name"],
        "interest_area": DEMO_STUDENT["interest_area"],
        "grade_level": DEMO_STUDENT["grade_level"],
        "is_demo_student": True,
    })

    print(f"  Session created: {session_id}")
    print(f"  Student: {DEMO_STUDENT['full_name']}")
    print(f"  Interest: {DEMO_STUDENT['interest_area']}")

    return session_id


async def seed_morning_circle_event(conn, session_id):
    """Seed Event 1: Morning Circle with tired sentiment"""
    print("\n[STEP 3] Seeding Morning Circle event...")

    event = DEMO_EVENTS[0]

    await conn.execute("""
        INSERT INTO cortex.user_sessions (
            user_id,
            session_start,
            current_mode,
            focus_level,
            metadata
        ) VALUES (
            $1, $2, 'focus', 30,
            $3::jsonb
        )
    """, DEMO_STUDENT["user_id"], event["timestamp"], {
        "event_name": event["name"],
        "sentiment_score": event["sentiment_score"],
        "intervention_triggered": True,
        "is_demo_data": True,
    })

    print(f"  Event: {event['name']}")
    print(f"  Sentiment: {event['sentiment_score']} (Tired)")
    print(f"  Expected: System triggers Focus Mode intervention")


async def seed_mastery_event(conn, session_id):
    """Seed Event 2: Math Sprint with high mastery"""
    print("\n[STEP 4] Seeding Math Sprint mastery event...")

    event = DEMO_EVENTS[1]

    # Create mastery state directly
    await conn.execute("""
        INSERT INTO cortex.mastery_states (
            user_id,
            skill_id,
            probability_mastery,
            total_attempts,
            correct_attempts,
            consecutive_correct,
            last_attempt_at,
            metadata
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7,
            $8::jsonb
        )
        ON CONFLICT (user_id, skill_id) DO UPDATE SET
            probability_mastery = $3,
            total_attempts = $4,
            correct_attempts = $5,
            consecutive_correct = $6,
            last_attempt_at = $7
    """, DEMO_STUDENT["user_id"], event["skill_id"],
       event["mastery_after"], 12, 11, 5, event["timestamp"], {
        "skill_name": event["skill_name"],
        "is_demo_data": True,
    })

    print(f"  Event: {event['name']}")
    print(f"  Skill: {event['skill_name']}")
    print(f"  Mastery: {event['mastery_after']} (EXCELLENT)")
    print(f"  Expected: Green dot status, celebration message")


async def seed_textbook_content_for_pbl(conn):
    """Seed textbook content about water pumps for PBL query"""
    print("\n[STEP 5] Seeding textbook content for PBL query...")

    event = DEMO_EVENTS[2]

    # Clear existing water pump content first
    await conn.execute("""
        DELETE FROM cortex.textbook_chunks
        WHERE metadata->>'demo_content' = 'true'
    """)

    # Insert water pump content from OpenStax style
    await conn.execute("""
        INSERT INTO cortex.textbook_chunks (
            chapter_id,
            section_id,
            content,
            grade_level,
            subject,
            metadata
        ) VALUES (
            'openstax-physics-ch05', 'fluid-mechanics-pumps',
            $1,
            12, 'college',
            $2::jsonb
        )
    """, f"""
    Water pumps are devices that move fluids by mechanical action, typically
    converting electrical energy into hydraulic energy. The basic principle
    involves creating a pressure differential that drives fluid flow.

    In engineering applications, pumps are classified into two main categories:
    1. Positive displacement pumps - trap a fixed amount of fluid and force it
       into the discharge pipe (e.g., piston pumps, gear pumps)
    2. Centugal pumps - convert rotational kinetic energy to hydrodynamic
       energy (e.g., the common water pumps used in buildings)

    The efficiency of a pump is determined by its ability to minimize energy
    losses due to friction and turbulence. Modern engineering applications
    often use multistage centrifugal pumps for high-pressure applications
    like high-rise building water supply.

    Key engineering concepts:
    - Flow rate (Q): Volume of fluid moved per unit time
    - Head (H): Height the pump can raise the fluid
    - Power (P): Energy required to drive the pump
    - Efficiency (η): Ratio of output power to input power

    Source: OpenStax College Physics, Chapter 5: Fluid Mechanics and Applications
    """, {
        "source": "OpenStax College Physics",
        "chapter": 5,
        "section": "Fluid Mechanics",
        "topic": "water-pumps",
        "demo_content": "true",
    })

    print(f"  Seeded content: Water pumps from OpenStax Ch 5")
    print(f"  Query: {event['query']}")
    print(f"  Expected: System retrieves this exact content with citation")


async def verify_demo_data(conn):
    """Verify all demo data was inserted correctly"""
    print("\n[STEP 6] Verifying demo data...")

    # Check user sessions
    sessions = await conn.fetchval("""
        SELECT COUNT(*) FROM cortex.user_sessions
        WHERE user_id = $1
    """, DEMO_STUDENT["user_id"])

    # Check mastery states
    mastery = await conn.fetchval("""
        SELECT COUNT(*) FROM cortex.mastery_states
        WHERE user_id = $1
    """, DEMO_STUDENT["user_id"])

    # Check textbook content
    content = await conn.fetchval("""
        SELECT COUNT(*) FROM cortex.textbook_chunks
        WHERE metadata->>'demo_content' = 'true'
    """)

    print(f"\n  ✓ User Sessions: {sessions}")
    print(f"  ✓ Mastery States: {mastery}")
    print(f"  ✓ Textbook Chunks: {content}")

    if sessions > 0 and mastery > 0 and content > 0:
        print("\n  Demo data verification: PASSED")
        return True
    else:
        print("\n  Demo data verification: FAILED")
        return False


async def print_demo_script():
    """Print the demo script for the presenter"""
    print("\n" + "="*70)
    print("DEMO DAY SCRIPT - Present to Investors")
    print("="*70)

    print("\n🎭 NARRATIVE: Meet Darius Johnson")
    print("-" * 70)
    print(f"   Grade: {DEMO_STUDENT['grade_level']}")
    print(f"   Interest: {DEMO_STUDENT['interest_area']}")
    print(f"   Story: A bright student who needs personalized support")

    print("\n📅 SCENE 1: Morning Circle (Emotional Check-in)")
    print("-" * 70)
    print(f"   {DEMO_EVENTS[0]['description']}")
    print(f"   Sentiment Score: {DEMO_EVENTS[0]['sentiment_score']}")
    print(f"   System Action: {DEMO_EVENTS[0]['expected_response']}")
    print("   💡 POINT: System adapts to student emotional state")

    print("\n📚 SCENE 2: Math Sprint (Mastery Tracking)")
    print("-" * 70)
    print(f"   {DEMO_EVENTS[1]['description']}")
    print(f"   Skill: {DEMO_EVENTS[1]['skill_name']}")
    print(f"   Mastery: {DEMO_EVENTS[1]['mastery_after']} (GREEN DOT)")
    print(f"   System Action: {DEMO_EVENTS[1]['expected_response']}")
    print("   💡 POINT: System tracks and celebrates mastery")

    print("\n🔬 SCENE 3: PBL Inquiry (Knowledge Retrieval)")
    print("-" * 70)
    print(f"   {DEMO_EVENTS[2]['description']}")
    print(f"   Query: \"{DEMO_EVENTS[2]['query']}\"")
    print(f"   Citation: {DEMO_EVENTS[2]['expected_citation']}")
    print(f"   System Action: {DEMO_EVENTS[2]['expected_response']}")
    print("   💡 POINT: Grounded retrieval prevents hallucination")

    print("\n🔒 COMPLIANCE: FERPA-First Design")
    print("-" * 70)
    print("   ✓ All data on localhost (no cloud)")
    print("   ✓ No telemetry or analytics")
    print("   ✓ Teacher sees masked IDs (redacted)")
    print("   💡 POINT: Student data never leaves the classroom")

    print("\n" + "="*70)


async def main():
    """Main execution function"""
    print("\n" + "="*70)
    print("Mu2 Cognitive OS - Demo Day Scenario Seeder")
    print("="*70)
    print("\nThis script will seed the database with the Darius demo narrative.")
    print("All existing data for the demo student will be wiped.")

    conn = None
    try:
        # Connect to database
        conn = await get_db_connection()

        # Wipe existing demo data
        await wipe_demo_data(conn)

        # Create student session
        session_id = await create_student_session(conn)

        # Seed demo events
        await seed_morning_circle_event(conn, session_id)
        await seed_mastery_event(conn, session_id)
        await seed_textbook_content_for_pbl(conn)

        # Verify data
        success = await verify_demo_data(conn)

        if success:
            # Print demo script
            await print_demo_script()

            print("\n✅ Demo scenario seeded successfully!")
            print("\nNext steps:")
            print("  1. Open http://localhost:3000")
            print("  2. Login as teacher to view Darius's dashboard")
            print("  3. Try the chat query: 'How do water pumps work?'")
            print("  4. Verify OpenStax Ch 5 citation appears")
            print("")

        else:
            print("\n❌ Demo scenario seeding failed!")
            sys.exit(1)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        if conn:
            await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
