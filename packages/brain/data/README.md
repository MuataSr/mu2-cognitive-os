# Mu2 Cognitive OS - Data Directory

This directory contains all data files for the Mu2 Cognitive OS brain package.

## Structure

```
data/
├── openstax/
│   ├── pdfs/           # Original OpenStax textbook PDFs
│   ├── chapters/       # Individual chapter PDFs (split from originals)
│   ├── embeddings/     # Generated embeddings and vectors
│   ├── chunks/         # Chunk metadata and SQLite database
│   └── vectors/        # Raw vector embeddings (if separated)
└── README.md           # This file
```

## Data Files

### OpenStax Textbooks

OpenStax textbooks are CC BY 4.0 licensed educational materials:

- **American Government 3e**: Source: https://openstax.org/details/books/american-government-3e
- **Prealgebra 2e**: Source: https://openstax.org/details/books/prealgebra-2e

### Embeddings

- `american-government-3e_embeddings.json`: Chunk metadata with concepts and definitions
- `american-government-3e_vectors.json`: 768-dim vectors for each chunk
- `chunks.db`: SQLite database with vector similarity search

### Processing Pipeline

The data pipeline follows these steps:

1. **PDF Download** → `pdfs/`
2. **Chapter Splitting** → `chapters/`
3. **Content Extraction** → Generates embeddings
4. **Embedding Generation** → `embeddings/`
5. **Vector Storage** → PostgreSQL/pgvector + SQLite fallback

## Configuration

The data directory path is configured in `src/core/config.py`:

```python
# Default data directory
DATA_DIR = Path(__file__).parent.parent / "data"
OPENSTAX_DATA_DIR = DATA_DIR / "openstax"
```

## Adding New Textbooks

To process a new OpenStax textbook:

1. Download the PDF to `data/openstax/pdfs/`
2. Run the pipeline:
   ```bash
   cd packages/brain
   python test_openstax_pipeline.py --book <book-name>
   ```
3. Embeddings will be generated in `data/openstax/embeddings/`

## Database

All processed data is stored in:
- **PostgreSQL/pgvector**: Production vector store
- **SQLite**: Local fallback for development

## Backup

This directory should be backed up regularly as it contains:
- Generated embeddings (computationally expensive to recreate)
- Knowledge graph data
- Processed textbook content

## License

All OpenStax content is licensed under CC BY 4.0:
https://creativecommons.org/licenses/by/4.0/
