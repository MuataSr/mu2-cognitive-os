# Phase D - OpenStax Instructor Test Bank Integration

**Status**: 🔄 IN PROGRESS (Updated to OpenStax instead of LibreTexts ADAPT)

**Date**: 2025-02-13

---

## Overview

Since **Khan Academy's API was removed** and **LibreTexts ADAPT is no longer available**, Phase D was updated to use **OpenStax Instructor Test Banks**.

OpenStax provides downloadable test banks that align with the existing Biology 2e content.

---

## What Was Implemented

### 1. Configuration Updates (`src/core/config.py`)

Added OpenStax Instructor Resources configuration:
```python
# OpenStax Instructor Resources Base URL
openstax_instructor_base: str = "https://openstax.org"

# Available instructor test banks
openstax_test_banks: list[str] = [
    "biology-2e",           # Matches our loaded content
    "anatomy-physiology",
    "chemistry-of-life",
    "concepts-biology",
]

# Import settings
question_import_batch_size: int = 50
question_import_max_count: int = 500
question_storage_path: str = "questions"
```

### 2. Question Bank Service (`src/services/question_bank.py`)

Created comprehensive question bank service:
```python
class Question(BaseModel):
    id, type, subject, difficulty, stem, options,
    correct_answer, explanation, chapter_ref, section_ref, metadata

class QuestionBank:
    - add_question()           # Add single question
    - get_question()           # Get by ID
    - get_questions_by_subject()   # Filter by subject
    - get_questions_by_difficulty() # Filter by difficulty
    - get_questions_by_chapter()    # Filter by chapter
    - get_random_questions()      # Get random set
    - search_questions()          # Full-text search
    - get_stats()             # Statistics
    - export_to_json() / import_from_json()
```

### 3. OpenStax Importer Service (`src/services/openstax_import.py`)

Created OpenStax test bank importer:
```python
class OpenStaxQuestion(BaseModel):
    # Question model matching OpenStax format

class OpenStaxImporter:
    - _get_test_bank_url()   # Get URL for test bank
    - _get_pdf_urls()        # Get direct PDF links
    - download_test_bank_pdf()  # Download PDFs
    - import_from_json()       # Import from JSON files
    - import_subject_questions() # Import all questions for subject
    - get_import_statistics()  # Get import stats
```

**Features**:
- JSON-based import (no PDF parsing needed initially)
- In-memory question storage (production would use database)
- Progress tracking during import
- FERPA compliant (local-only, no PII)

### 4. Main.py Import Updates

Updated imports:
```python
from src.services.openstax_import import openstax_importer
from src.services.question_bank import question_bank, Question, ...
```

Updated API models:
```python
class ImportQuestionsInput(BaseModel):
    subject: Optional[str]    # Subject filter
    difficulty: Optional[str]    # Difficulty filter
    chapter: Optional[str]      # Chapter filter
    count: int                 # Number to questions

class SearchQuestionsInput(BaseModel):
    query: str               # Text search
    subject: Optional[str]     # Subject filter
    difficulty: Optional[str]  # Difficulty filter
    limit: int              # Max results
```

---

## API Endpoints

### Updated Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| POST `/api/v1/questions/import` | Import from JSON |
| GET `/api/v1/questions/search` | Semantic search |
| GET `/api/v1/questions/random` | Random quiz questions |
| GET `/api/v1/questions/statistics` | Bank statistics |

### Legacy ADAPT Endpoints (Kept for Compatibility)

| Endpoint | Purpose |
|----------|---------|
| POST `/api/v1/adapt/import` | Renamed to `/api/v1/questions/import` |
| POST `/api/v1/adapt/search` | Replaced with search endpoint |
| GET `/api/v1/adapt/topics` | Deprecated |
| GET `/api/v1/adapt/statistics` | Redirects to questions statistics |
| GET `/api/v1/adapt/health` | Question bank health check |

---

## Files Created

| File | Purpose | Lines |
|-------|---------|-------|
| `src/services/question_bank.py` | Question bank service | ~400 |
| `src/services/openstax_import.py` | OpenStax importer service | ~350 |
| `src/core/config.py` | Updated with OpenStax config | +15 |
| `packages/brain/data/questions/` | Storage directory for JSON test banks |

---

## What's NOT Implemented Yet

### 1. PDF Test Bank Parsing

The importer service has placeholder `parse_pdf_questions()` that needs to:
- Extract questions from OpenStax test bank PDFs
- Parse multiple choice, true/false, and short answer questions
- Handle PDF tables and formatting

**Estimated effort**: 4-6 hours

### 2. OpenStax Download Automation

The importer currently has basic PDF URL patterns:
```python
pdf_patterns = [
    f"{base_url}/{subject}/instructor/resources",
    f"{base_url}/books/{subject}/instructor",
    "https://openstax.org/contents/biology-2e",
]
```

**Needed**:
- Discover actual PDF URLs from OpenStax instructor pages
- Handle authentication if required
- Batch download for multiple test banks

**Estimated effort**: 2-3 hours

### 3. Test Bank JSON Files

Create sample JSON files matching OpenStax instructor test bank format:
```json
{
  "questions": [
    {
      "id": "bio-2e-ch2-1",
      "type": "multiple_choice",
      "subject": "biology",
      "difficulty": "medium",
      "stem": "What is the primary function of the cell membrane?",
      "options": [
        "To control what enters and exits the cell",
        "To store energy and nutrients",
        "To provide a site for protein synthesis",
        "To facilitate cell communication"
      ],
      "correct_answer": "To control what enters and exits the cell",
      "explanation": "The cell membrane is selectively permeable...",
      "chapter_ref": "2.1",
      "section_ref": "2.1",
      "metadata": {
        "source": "openstax-instructor",
        "openstax_slug": "biology-2e"
      }
    }
  ]
}
```

### 4. Frontend Question Management

Not yet implemented - would include:
- Question upload interface for instructors
- Question editor with preview
- Bulk import from JSON
- Export/sharing capabilities

**Estimated effort**: 8-12 hours

### 5. Integration with OpenStax Content

**Goal**: Link questions to existing OpenStax chapters (2.1-2.21) so that:
- Questions relate to specific textbook content
- Chapter-based question filtering
- Section-level granularity

**Implementation**:
- Map question `chapter_ref` and `section_ref` to OpenStax chapters
- Enhance retrieval to include relevant questions
- Display chapter context with questions

**Estimated effort**: 6-8 hours

---

## Next Steps

### Immediate (High Priority)

1. **Create Sample Test Bank JSON**
   ```bash
   mkdir -p packages/brain/data/questions/biology-2e
   # Create sample-questions.json with 10-20 questions
   ```

2. **Test Question Bank Service**
   ```python
   cd packages/brain
   python -c "
   from services.question_bank import question_bank
   import asyncio

   async def test():
       bank = question_bank()

       # Add sample questions
       for i in range(5):
           await bank.add_question(Question(
               id=f'q-{i}',
               type='multiple_choice',
               subject='biology',
               difficulty='medium',
               stem='Test question',
               options=['A', 'B', 'C', 'D'],
               correct_answer='A',
               explanation='Sample explanation'
           ))

       # Get stats
       stats = bank.get_stats()
       print(f'Total: {stats[\"total_questions\"]}')
       print(f'by_subject: {stats[\"by_subject\"]}')

   asyncio.run(test())
   "
   ```

3. **Create Import Test**
   ```bash
   # Test import endpoint
   curl -X POST http://localhost:8000/api/v1/questions/import \
     -H "Content-Type: application/json" \
     -d @sample-questions.json
   ```

### Medium Priority

1. **Implement PDF Download** - Complete OpenStax importer `download_test_bank_pdf()`
2. **Create Frontend Components** - Question management UI
3. **Chapter Mapping** - Map OpenStax chapters to question references

### Future Enhancements

1. **OER Commons Integration** - Import from OER Commons question banks
2. **Science Bowl Integration** - Import from Science Bowl question archive
3. **Crowdsourced Question Curation** - Community-contributed questions

---

## Usage Example

### Import Sample Questions

```bash
# Create sample test bank JSON
cat > /tmp/sample-questions.json << 'EOF'
{
  "questions": [
    {
      "id": "bio-2e-ch2-1",
      "type": "multiple_choice",
      "subject": "biology",
      "difficulty": "medium",
      "stem": "What is the primary function of the cell membrane?",
      "options": [
        "To control what enters and exits the cell",
        "To store energy and nutrients",
        "To provide a site for protein synthesis",
        "To facilitate cell communication"
      ],
      "correct_answer": "To control what enters and exits the cell",
      "explanation": "The cell membrane is selectively permeable...",
      "chapter_ref": "2.1",
      "section_ref": "2.1"
    }
  ]
}
EOF

# Import via API
curl -X POST http://localhost:8000/api/v1/questions/import \
  -H "Content-Type: application/json" \
  -d @/tmp/sample-questions.json
```

### Search Questions

```bash
# Search for photosynthesis questions
curl -X GET "http://localhost:8000/api/v1/questions/search?query=photosynthesis&limit=5"
```

### Get Random Quiz

```bash
# Get 10 random biology questions for a quiz
curl -X GET "http://localhost:8000/api/v1/questions/random?subject=biology&count=10"
```

---

## Definition of Done Checklist

- [x] D1: Configuration updated for OpenStax instructor resources
- [x] D2: Question bank service created (400+ lines)
- [x] D3: OpenStax importer service created (350+ lines)
- [x] D4: Main.py imports updated (openstax_importer, question_bank)
- [x] D5: API models updated (new filters for questions)
- [x] D6: API endpoints renamed/repurposed (ADAPT → Questions)
- [x] D8: Sample test bank JSON created (5 biology questions in `data/questions/biology-2e/sample-questions.json`)
- [x] D12: Server starts successfully with question_bank imports
- [x] D13: Question bank service tests passing (all 8 tests)
- [ ] D7: PDF test bank download and parsing
- [ ] D9: Frontend question management UI
- [ ] D10: Chapter mapping to OpenStax content
- [ ] D11: Integration tests created

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Mu2 Cognitive OS                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────┐ │
│  │   Student    │    │   Frontend    │    │  Backend  │ │
│  │  Interaction │    │  Management UI │    │  Services  │ │
│  └─────────────┘    └──────────────┘    └──────────┘ │ │
│                                                             │
│  ┌─────────────┐    ┌──────────────────────────────┐   ┌────────┐ │
│  │OpenStax    │    │    Local Question Bank      │   │  API    │ │
│  │Instructor  │    │    (JSON files)              │   │  Endpoints│ │
│  │Test Banks   │    │                             │   │        │ │
│  └─────────────┘    └──────────────────────────────┘   └────────┘ │ │
└─────────────────────────────────────────────────────────────┘
```

**Data Flow**:
1. Instructor uploads/downloads JSON test bank
2. Questions stored in local question bank
3. Frontend fetches questions for quiz generation
4. Backend serves via REST API
5. Student receives questions linked to OpenStax content

---

## Summary

Phase D backend infrastructure is **complete and tested**. The question bank service can now store and serve questions locally (FERPA compliant).

### What Was Completed (2026-02-13 Session)
1. ✅ **Fixed import errors** in `question_bank.py` and `openstax_import.py`
2. ✅ **Added missing QuestionBank class** with full CRUD operations
3. ✅ **Fixed syntax errors** (Enum inheritance, bracket issues, import typos)
4. ✅ **Fixed main.py imports** (`QuestionBatch` → `QuestionBank`, added `List` to typing)
5. ✅ **Created sample questions JSON** (`data/questions/biology-2e/sample-questions.json`) with 5 questions
6. ✅ **Created test suite** (`tests/test_question_bank.py`) - all 8 tests passing
7. ✅ **Verified server starts** successfully with new services
8. ✅ **Sample questions import** works (5 questions loaded from JSON)

**Remaining work** focuses on:
1. PDF test bank download and parsing (estimated 4-6 hours)
2. Frontend question management UI (estimated 8-12 hours)
3. Chapter mapping to OpenStax content (estimated 6-8 hours)
4. Integration tests for API endpoints

**Estimated completion**: 20-26 hours remaining

**Current Status**: ✅ Backend services created, tested, and working. Server starts successfully.
