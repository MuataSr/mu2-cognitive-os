#!/usr/bin/env python3
"""
Test Question Bank Service - Phase D Implementation
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.question_bank import question_bank, Question, QuestionType, Subject, DifficultyLevel


async def test_question_bank():
    """Test question bank service"""
    print("=== Testing Question Bank Service ===\n")

    # Get singleton instance
    bank = question_bank

    # Test 1: Add sample questions
    print("Test 1: Adding sample questions...")
    sample_questions = [
        Question(
            id="test-bio-001",
            type=QuestionType.MULTIPLE_CHOICE,
            subject=Subject.BIOLOGY,
            difficulty=DifficultyLevel.MIDDLE,
            stem="What is the primary function of the cell membrane?",
            options=[
                "To control what enters and exits the cell",
                "To store energy and nutrients",
                "To provide a site for protein synthesis",
                "To facilitate cell communication"
            ],
            correct_answer="To control what enters and exits the cell",
            explanation="The cell membrane is selectively permeable and regulates what enters and exits the cell.",
            chapter_ref="2.1",
            section_ref="2.1"
        ),
        Question(
            id="test-bio-002",
            type=QuestionType.MULTIPLE_CHOICE,
            subject=Subject.BIOLOGY,
            difficulty=DifficultyLevel.MIDDLE,
            stem="Which molecule is primarily responsible for the fluidity of the cell membrane?",
            options=[
                "Cholesterol",
                "Phospholipids",
                "Proteins",
                "Carbohydrates"
            ],
            correct_answer="Cholesterol",
            explanation="Cholesterol helps maintain membrane fluidity across different temperatures.",
            chapter_ref="2.3",
            section_ref="2.3"
        ),
    ]

    for q in sample_questions:
        result = await bank.add_question(q)
        print(f"  ✓ Added question: {q.id}")

    # Test 2: Get statistics
    print("\nTest 2: Getting statistics...")
    stats = bank.get_stats()
    print(f"  Total questions: {stats['total_questions']}")
    print(f"  By subject: {stats['by_subject']}")
    print(f"  By difficulty: {stats['by_difficulty']}")

    # Test 3: Get by subject
    print("\nTest 3: Get questions by subject...")
    bio_questions = await bank.get_questions_by_subject("biology")
    print(f"  Biology questions: {len(bio_questions)}")

    # Test 4: Get by difficulty
    print("\nTest 4: Get questions by difficulty...")
    middle_questions = await bank.get_questions_by_difficulty("middle")
    print(f"  Middle difficulty questions: {len(middle_questions)}")

    # Test 5: Get by chapter
    print("\nTest 5: Get questions by chapter...")
    ch21_questions = await bank.get_questions_by_chapter("2.1")
    print(f"  Chapter 2.1 questions: {len(ch21_questions)}")

    # Test 6: Search questions
    print("\nTest 6: Search questions...")
    results = await bank.search_questions("membrane", limit=5)
    print(f"  Search results for 'membrane': {len(results)} questions")
    for q in results:
        print(f"    - {q.id}: {q.stem[:50]}...")

    # Test 7: Random questions
    print("\nTest 7: Get random questions...")
    random_qs = await bank.get_random_questions(count=2)
    print(f"  Random questions: {len(random_qs)}")
    for q in random_qs:
        print(f"    - {q.id}: {q.stem[:50]}...")

    # Test 8: Import from JSON
    print("\nTest 8: Import from JSON file...")
    json_path = Path(__file__).parent.parent / "data/questions/biology-2e/sample-questions.json"
    if json_path.exists():
        count = await bank.import_from_json(str(json_path))
        print(f"  ✓ Imported {count} questions from JSON")
        stats = bank.get_stats()
        print(f"  Total questions after import: {stats['total_questions']}")
    else:
        print(f"  ⚠ JSON file not found: {json_path}")

    print("\n=== All Tests Complete ===")


if __name__ == "__main__":
    asyncio.run(test_question_bank())
