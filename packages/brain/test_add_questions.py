"""
Test script to add sample questions directly to cloud Supabase
"""
import asyncio
import sys
sys.path.insert(0, '/home/papi/Documents/mu2-cognitive-os/packages/brain/src')

from services.supabase_vector_store import Question, get_supabase_vector_store

async def add_sample_questions():
    """Add sample questions to test the pipeline"""
    store = get_supabase_vector_store()

    # Sample questions
    sample_questions = [
        Question(
            question_id="test_001",
            question_text="What is the process by which plants convert light energy into chemical energy?",
            question_type="multiple_choice",
            subject="Biology",
            topic="Photosynthesis",
            difficulty="medium",
            grade_level=8,
            correct_answer="Photosynthesis",
            incorrect_answers=["Respiration", "Transpiration", "Germination"],
            explanation="Photosynthesis is the process used by plants, algae and some bacteria to convert light energy into chemical energy.",
            source="test",
            metadata={"test": True, "category": "Biology"}
        ),
        Question(
            question_id="test_002",
            question_text="What is the equation for cellular respiration?",
            question_type="multiple_choice",
            subject="Biology",
            topic="Cellular Respiration",
            difficulty="medium",
            grade_level=9,
            correct_answer="C6H12O6 + 6O2 → 6CO2 + 6H2O + ATP",
            incorrect_answers=["6CO2 + 6H2O → C6H12O6 + 6O2", "CO2 + H2O → ATP", "O2 + glucose → energy"],
            explanation="Cellular respiration is the process by which cells break down glucose to produce ATP.",
            source="test"
        ),
        Question(
            question_id="test_003",
            question_text="What is Newton's first law of motion?",
            question_type="multiple_choice",
            subject="Physics",
            topic="Newton's Laws",
            difficulty="easy",
            grade_level=8,
            correct_answer="An object at rest stays at rest unless acted on by an external force",
            incorrect_answers=["For every action there is an equal and opposite reaction", "F = ma", "Energy cannot be created or destroyed"],
            explanation="Newton's first law states that an object will remain at rest or in uniform motion unless acted upon by an external force.",
            source="test"
        ),
        Question(
            question_id="test_004",
            question_text="What is the chemical formula for water?",
            question_type="multiple_choice",
            subject="Chemistry",
            topic="Atomic Structure",
            difficulty="easy",
            grade_level=6,
            correct_answer="H2O",
            incorrect_answers=["H2O2", "CO2", "NaCl"],
            explanation="Water is composed of two hydrogen atoms and one oxygen atom.",
            source="test"
        ),
        Question(
            question_id="test_005",
            question_text="What is the powerhouse of the cell?",
            question_type="multiple_choice",
            subject="Biology",
            topic="Cell Structure",
            difficulty="easy",
            grade_level=7,
            correct_answer="Mitochondria",
            incorrect_answers=["Nucleus", "Ribosome", "Endoplasmic reticulum"],
            explanation="Mitochondria produce ATP through cellular respiration.",
            source="test"
        ),
    ]

    print(f"Adding {len(sample_questions)} sample questions...")

    for i, q in enumerate(sample_questions, 1):
        try:
            await store.add_question(q)
            print(f"  [{i}] Added: {q.question_id[:30]}...")
        except Exception as e:
            print(f"  [{i}] Error adding {q.question_id}: {e}")

    # Get statistics
    stats = await store.get_statistics()
    print(f"\nTotal questions in database: {stats['total_questions']}")

    # Test search
    print("\nTesting semantic search for 'photosynthesis'...")
    results = await store.search_similar_questions(
        query="photosynthesis",
        limit=3
    )
    print(f"Found {len(results)} results")
    for r in results:
        print(f"  - {r.question_id}: {r.similarity:.3f} - {r.question_text[:50]}...")

    print("\nTesting random questions...")
    random_qs = await store.get_random_questions(limit=3)
    print(f"Got {len(random_qs)} random questions")
    for q in random_qs:
        print(f"  - {q.question_id}: {q.question_text[:50]}...")

if __name__ == "__main__":
    asyncio.run(add_sample_questions())
