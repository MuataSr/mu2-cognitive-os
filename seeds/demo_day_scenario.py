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
    python3 seeds/demo_day_scenario.py

Requirements:
    - Database must be running (docker-compose up -d)
    - psycopg2-binary installed
"""

import sys
import json
from datetime import datetime, timedelta

try:
    import psycopg
except ImportError:
    print("Installing psycopg...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg[binary]", "-q"])
    import psycopg

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

def get_db_connection():
    """Connect to the Mu2 Cognitive OS database"""
    # Try multiple connection methods
    connection_params = [
        # Try with password
        {
            "host": "localhost",
            "port": 54322,
            "user": "postgres",
            "password": "your-super-secret-and-long-postgres-password",
            "dbname": "postgres"
        },
        # Try without password
        {
            "host": "localhost",
            "port": 54322,
            "user": "postgres",
            "dbname": "postgres"
        },
    ]

    for params in connection_params:
        try:
            conn = psycopg.connect(**params)
            conn.autocommit = True
            print(f"Connected to database (port {params['port']})")
            return conn
        except Exception as e:
            continue

    print("Failed to connect to database with any method")
    print("Please ensure:")
    print("  1. docker-compose is running (docker-compose up -d)")
    print("  2. Database is accessible on localhost:54322")
    sys.exit(1)


def wipe_demo_data(conn):
    """Clean any existing demo data to ensure clean slate"""
    print("\n[STEP 1] Wiping existing demo data...")

    cursor = conn.cursor()

    # Check if tables exist first
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'cortex'
            AND table_name = 'user_sessions'
        );
    """)

    if cursor.fetchone()[0]:
        cursor.execute("""
            DELETE FROM cortex.user_sessions
            WHERE user_id = %s
        """, (DEMO_STUDENT["user_id"],))
        print(f"  Cleaned user_sessions for student: {DEMO_STUDENT['user_id']}")
    else:
        print("  Creating cortex schema...")

    # Check if mastery_states table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'cortex'
            AND table_name = 'mastery_states'
        );
    """)

    if cursor.fetchone()[0]:
        cursor.execute("""
            DELETE FROM cortex.mastery_states
            WHERE user_id = %s
        """, (DEMO_STUDENT["user_id"],))
        print(f"  Cleaned mastery_states for student: {DEMO_STUDENT['user_id']}")


def ensure_tables_exist(conn):
    """Ensure required tables exist"""
    print("\n[STEP 1.5] Ensuring tables exist...")

    cursor = conn.cursor()

    # Ensure cortex schema exists
    cursor.execute("CREATE SCHEMA IF NOT EXISTS cortex;")

    # Check for user_sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cortex.user_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id TEXT NOT NULL,
            session_start TIMESTAMPTZ DEFAULT NOW(),
            session_end TIMESTAMPTZ,
            current_mode TEXT DEFAULT 'standard',
            focus_level INTEGER DEFAULT 50,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)

    # Check for mastery_states table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cortex.mastery_states (
            user_id TEXT NOT NULL,
            skill_id TEXT NOT NULL,
            probability_mastery FLOAT DEFAULT 0.5,
            total_attempts INTEGER DEFAULT 0,
            correct_attempts INTEGER DEFAULT 0,
            consecutive_correct INTEGER DEFAULT 0,
            consecutive_incorrect INTEGER DEFAULT 0,
            last_attempt_at TIMESTAMPTZ,
            metadata JSONB DEFAULT '{}',
            PRIMARY KEY (user_id, skill_id)
        );
    """)

    # Check for textbook_chunks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cortex.textbook_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            chapter_id TEXT NOT NULL,
            section_id TEXT NOT NULL,
            content TEXT NOT NULL,
            grade_level INTEGER DEFAULT 8,
            subject TEXT DEFAULT 'science',
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)

    conn.commit()
    print("  All required tables exist")


def create_student_session(conn):
    """Create the initial session for Darius"""
    print("\n[STEP 2] Creating student session...")

    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO cortex.user_sessions (
            user_id,
            session_start,
            current_mode,
            focus_level,
            metadata
        ) VALUES (
            %s, NOW(), 'standard', 50,
            %s::jsonb
        )
        RETURNING id
    """, (DEMO_STUDENT["user_id"], json.dumps({
        "full_name": DEMO_STUDENT["full_name"],
        "interest_area": DEMO_STUDENT["interest_area"],
        "grade_level": DEMO_STUDENT["grade_level"],
        "is_demo_student": True,
    })))

    session_id = cursor.fetchone()[0]
    conn.commit()

    print(f"  Session created: {session_id}")
    print(f"  Student: {DEMO_STUDENT['full_name']}")
    print(f"  Interest: {DEMO_STUDENT['interest_area']}")

    return session_id


def seed_morning_circle_event(conn, session_id):
    """Seed Event 1: Morning Circle with tired sentiment"""
    print("\n[STEP 3] Seeding Morning Circle event...")

    cursor = conn.cursor()
    event = DEMO_EVENTS[0]

    cursor.execute("""
        INSERT INTO cortex.user_sessions (
            user_id,
            session_start,
            current_mode,
            focus_level,
            metadata
        ) VALUES (
            %s, %s, 'focus', 30,
            %s::jsonb
        )
    """, (DEMO_STUDENT["user_id"], event["timestamp"], json.dumps({
        "event_name": event["name"],
        "sentiment_score": event["sentiment_score"],
        "intervention_triggered": True,
        "is_demo_data": True,
    })))

    conn.commit()

    print(f"  Event: {event['name']}")
    print(f"  Sentiment: {event['sentiment_score']} (Tired)")
    print(f"  Expected: System triggers Focus Mode intervention")


def seed_mastery_event(conn, session_id):
    """Seed Event 2: Math Sprint with high mastery"""
    print("\n[STEP 4] Seeding Math Sprint mastery event...")

    cursor = conn.cursor()
    event = DEMO_EVENTS[1]

    # Create mastery state directly
    cursor.execute("""
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
            %s, %s, %s, %s, %s, %s, %s,
            %s::jsonb
        )
        ON CONFLICT (user_id, skill_id) DO UPDATE SET
            probability_mastery = EXCLUDED.probability_mastery,
            total_attempts = EXCLUDED.total_attempts,
            correct_attempts = EXCLUDED.correct_attempts,
            consecutive_correct = EXCLUDED.consecutive_correct,
            last_attempt_at = EXCLUDED.last_attempt_at
    """, (DEMO_STUDENT["user_id"], event["skill_id"],
       event["mastery_after"], 12, 11, 5, event["timestamp"], json.dumps({
        "skill_name": event["skill_name"],
        "is_demo_data": True,
    })))

    conn.commit()

    print(f"  Event: {event['name']}")
    print(f"  Skill: {event['skill_name']}")
    print(f"  Mastery: {event['mastery_after']} (EXCELLENT)")
    print(f"  Expected: Green dot status, celebration message")


def seed_textbook_content_for_pbl(conn):
    """Seed textbook content about water pumps for PBL query"""
    print("\n[STEP 5] Seeding textbook content for PBL query...")

    cursor = conn.cursor()
    event = DEMO_EVENTS[2]

    # Clear existing water pump content first
    cursor.execute("""
        DELETE FROM cortex.textbook_chunks
        WHERE metadata->>'demo_content' = 'true'
    """)

    # Insert water pump content from OpenStax style
    water_pump_content = """
    Water pumps are devices that move fluids by mechanical action, typically
    converting electrical energy into hydraulic energy. The basic principle
    involves creating a pressure differential that drives fluid flow.

    In engineering applications, pumps are classified into two main categories:
    1. Positive displacement pumps - trap a fixed amount of fluid and force it
       into the discharge pipe (e.g., piston pumps, gear pumps)
    2. Centrifugal pumps - convert rotational kinetic energy to hydrodynamic
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
    """

    cursor.execute("""
        INSERT INTO cortex.textbook_chunks (
            chapter_id,
            section_id,
            content,
            grade_level,
            subject,
            metadata
        ) VALUES (
            'openstax-physics-ch05', 'fluid-mechanics-pumps',
            %s,
            12, 'college',
            %s::jsonb
        )
    """, (water_pump_content, json.dumps({
        "source": "OpenStax College Physics",
        "chapter": 5,
        "section": "Fluid Mechanics",
        "topic": "water-pumps",
        "demo_content": "true",
    })))

    conn.commit()

    print(f"  Seeded content: Water pumps from OpenStax Ch 5")
    print(f"  Query: {event['query']}")
    print(f"  Expected: System retrieves this exact content with citation")


def verify_demo_data(conn):
    """Verify all demo data was inserted correctly"""
    print("\n[STEP 6] Verifying demo data...")

    cursor = conn.cursor()

    # Check user sessions
    cursor.execute("""
        SELECT COUNT(*) FROM cortex.user_sessions
        WHERE user_id = %s
    """, (DEMO_STUDENT["user_id"],))
    sessions = cursor.fetchone()[0]

    # Check mastery states
    cursor.execute("""
        SELECT COUNT(*) FROM cortex.mastery_states
        WHERE user_id = %s
    """, (DEMO_STUDENT["user_id"],))
    mastery = cursor.fetchone()[0]

    # Check textbook content
    cursor.execute("""
        SELECT COUNT(*) FROM cortex.textbook_chunks
        WHERE metadata->>'demo_content' = 'true'
    """)
    content = cursor.fetchone()[0]

    print(f"\n  ✓ User Sessions: {sessions}")
    print(f"  ✓ Mastery States: {mastery}")
    print(f"  ✓ Textbook Chunks: {content}")

    if sessions > 0 and mastery > 0 and content > 0:
        print("\n  Demo data verification: PASSED")
        return True
    else:
        print("\n  Demo data verification: FAILED")
        return False


def print_demo_script():
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


def main():
    """Main execution function"""
    print("\n" + "="*70)
    print("Mu2 Cognitive OS - Demo Day Scenario Seeder")
    print("="*70)
    print("\nThis script will seed the database with the Darius demo narrative.")
    print("All existing data for the demo student will be wiped.")

    conn = None
    try:
        # Connect to database
        conn = get_db_connection()

        # Ensure tables exist
        ensure_tables_exist(conn)

        # Wipe existing demo data
        wipe_demo_data(conn)

        # Create student session
        session_id = create_student_session(conn)

        # Seed demo events
        seed_morning_circle_event(conn, session_id)
        seed_mastery_event(conn, session_id)
        seed_textbook_content_for_pbl(conn)

        # Verify data
        success = verify_demo_data(conn)

        if success:
            # Print demo script
            print_demo_script()

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
            conn.close()


if __name__ == "__main__":
    main()
