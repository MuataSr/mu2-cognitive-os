#!/usr/bin/env python3
"""
Mu2 Cognitive OS - Content Seeder
=================================

Populates the Vector Store and Graph with seed content for cold-start deployment.
This ensures the "Living Textbook" works immediately upon installation.

Content: OpenStax Biology Chapter 5 - Structure and Function of Plasma Membranes

Usage:
    python3 scripts/seed_content.py
    python3 scripts/seed_content.py --verify  # Verify content was seeded
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
import numpy as np


# ============================================================================
# CONTENT: OpenStax Biology Chapter 5 (Condensed)
# ============================================================================

SEED_CONTENT = {
    "chapter_id": "biology-chapter-05",
    "chapter_title": "Structure and Function of Plasma Membranes",
    "subject": "biology",
    "grade_level": 9,
    "sections": [
        {
            "section_id": "5.1",
            "title": "Components and Structure",
            "content": """
The plasma membrane, which is also called the cell membrane, is a flexible barrier
that separates the inside of the cell from the outside environment. It regulates
what enters and exits the cell. The principal components of a plasma membrane are
lipids (phospholipids and cholesterol), proteins, and carbohydrates attached to
some of the lipids and proteins.

The main fabric of the membrane is composed of amphiphilic or dual-loving,
phospholipid molecules. The hydrophilic or water-loving areas of these molecules
are in contact with the aqueous fluid both inside and outside the cell. Hydrophobic
or water-fearing molecules tend to be non-polar. A phospholipid molecule consists
of a glycerol backbone to which two fatty acid chains (hydrophobic) and a phosphate
group (hydrophilic) are attached.

The most abundant membrane lipids are the phospholipids. These have a polar head
(two fatty acids and a phosphate group) and a nonpolar tail. The fatty acid tails
are hydrophobic and cannot interact with water, whereas the phosphate heads are
hydrophilic and interact with water.
            """,
            "concepts": ["plasma membrane", "phospholipid", "hydrophilic", "hydrophobic", "amphiphilic"]
        },
        {
            "section_id": "5.2",
            "title": "Passive Transport",
            "content": """
The most direct forms of membrane transport are passive. Passive transport is a
naturally occurring phenomenon and does not require the cell to expend energy to
accomplish the movement. In passive transport, substances move from an area of
higher concentration to an area of lower concentration in a process called diffusion.
A physical space in which there is a different concentration of a single substance
is said to have a concentration gradient.

Diffusion is a passive process of transport. A single substance tends to move from
an area of high concentration to an area of low concentration until the concentration
is equal across a space. Some materials diffuse readily through the membrane, but
others require specialized proteins, such as channels and facilitative transporters,
to facilitate their passage.

Osmosis is the movement of water through a semipermeable membrane according to the
concentration gradient of water across the membrane. Aquaporins are channel proteins
that allow water to pass through the membrane at a very high rate.
            """,
            "concepts": ["passive transport", "diffusion", "concentration gradient", "osmosis", "aquaporin"]
        },
        {
            "section_id": "5.3",
            "title": "Active Transport",
            "content": """
Active transport mechanisms require the use of the cell's energy, usually in the
form of adenosine triphosphate (ATP). If a substance must move into the cell
against its concentration gradient, the cell must use energy to move the substance.
Some active transport mechanisms move small-molecular weight material, such as ions,
through the membrane.

In primary active transport, the energy comes directly from the hydrolysis of ATP.
The sodium-potassium pump is an example of primary active transport. It moves
three sodium ions out of the cell and two potassium ions into the cell, both
against their concentration gradients.

Secondary active transport uses the energy stored in the form of a concentration
gradient. The sodium-glucose symporter is an example of secondary active transport.
It uses the energy stored in the sodium concentration gradient to move glucose
into the cell against its own concentration gradient.
            """,
            "concepts": ["active transport", "ATP", "sodium-potassium pump", "primary active transport", "secondary active transport"]
        },
        {
            "section_id": "5.4",
            "title": "Bulk Transport",
            "content": """
The final type of movement is bulk transport. Bulk transport is the movement of
large particles or large quantities of particles in or out of the cell. There are
two types of bulk transport: exocytosis and endocytosis.

Exocytosis is the process by which cells move materials from within the cell into
the extracellular fluid. A vesicle containing the material fuses with the plasma
membrane, expelling its contents outside the cell.

Endocytosis is the process of capturing a substance or particle from outside the
cell by engulfing it with the cell membrane. There are three types of endocytosis:
phagocytosis (cell eating), pinocytosis (cell drinking), and receptor-mediated
endocytosis.

Phagocytosis is the process by which a cell engulfs large particles or cells.
Pinocytosis is a method of active transport across the cell membrane where the
cell engulfing extracellular fluid. Receptor-mediated endocytosis is a form of
endocytosis that uses receptor proteins in the plasma membrane to capture specific
molecules.
            """,
            "concepts": ["bulk transport", "exocytosis", "endocytosis", "phagocytosis", "pinocytosis"]
        }
    ],
    "skills": [
        {
            "skill_id": "membrane-structure",
            "skill_name": "Plasma Membrane Structure",
            "description": "Understanding the basic structure of the plasma membrane"
        },
        {
            "skill_id": "passive-transport",
            "skill_name": "Passive Transport Mechanisms",
            "description": "Understanding diffusion and osmosis"
        },
        {
            "skill_id": "active-transport",
            "skill_name": "Active Transport Mechanisms",
            "description": "Understanding ATP-powered transport"
        }
    ]
}


# ============================================================================
# GRAPH ONTOLOGY: Biology Chapter 5
# ============================================================================

GRAPH_ONTOLOGY = {
    "nodes": [
        {"label": "Plasma Membrane", "type": "concept", "properties": {"chapter": "5"}},
        {"label": "Phospholipid", "type": "concept", "properties": {"chapter": "5"}},
        {"label": "Hydrophilic", "type": "property", "properties": {"chapter": "5"}},
        {"label": "Hydrophobic", "type": "property", "properties": {"chapter": "5"}},
        {"label": "Passive Transport", "type": "process", "properties": {"chapter": "5"}},
        {"label": "Diffusion", "type": "process", "properties": {"chapter": "5"}},
        {"label": "Osmosis", "type": "process", "properties": {"chapter": "5"}},
        {"label": "Active Transport", "type": "process", "properties": {"chapter": "5"}},
        {"label": "ATP", "type": "molecule", "properties": {"chapter": "5"}},
        {"label": "Sodium-Potassium Pump", "type": "protein", "properties": {"chapter": "5"}},
        {"label": "Exocytosis", "type": "process", "properties": {"chapter": "5"}},
        {"label": "Endocytosis", "type": "process", "properties": {"chapter": "5"}},
        {"label": "Concentration Gradient", "type": "concept", "properties": {"chapter": "5"}},
        {"label": "Aquaporin", "type": "protein", "properties": {"chapter": "5"}},
    ],
    "edges": [
        {"from": "Plasma Membrane", "to": "Phospholipid", "label": "composed_of", "properties": {}},
        {"from": "Phospholipid", "to": "Hydrophilic", "label": "has_property", "properties": {}},
        {"from": "Phospholipid", "to": "Hydrophobic", "label": "has_property", "properties": {}},
        {"from": "Plasma Membrane", "to": "Passive Transport", "label": "allows", "properties": {}},
        {"from": "Passive Transport", "to": "Diffusion", "label": "includes", "properties": {}},
        {"from": "Passive Transport", "to": "Osmosis", "label": "includes", "properties": {}},
        {"from": "Osmosis", "to": "Aquaporin", "label": "uses", "properties": {}},
        {"from": "Plasma Membrane", "to": "Active Transport", "label": "allows", "properties": {}},
        {"from": "Active Transport", "to": "ATP", "label": "requires", "properties": {}},
        {"from": "Active Transport", "to": "Sodium-Potassium Pump", "label": "includes", "properties": {}},
        {"from": "Diffusion", "to": "Concentration Gradient", "label": "follows", "properties": {}},
        {"from": "Osmosis", "to": "Concentration Gradient", "label": "follows", "properties": {}},
        {"from": "Plasma Membrane", "to": "Exocytosis", "label": "facilitates", "properties": {}},
        {"from": "Plasma Membrane", "to": "Endocytosis", "label": "facilitates", "properties": {}},
    ]
}


# ============================================================================
# DATABASE CONNECTION
# ============================================================================

def get_db_connection():
    """Get database connection from environment or default."""
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres@localhost:54322/postgres"
    )
    return create_engine(database_url)


# ============================================================================
# SEEDING FUNCTIONS
# ============================================================================

def seed_skills_registry(engine) -> int:
    """Seed the skills registry table."""
    count = 0

    with engine.connect() as conn:
        for skill in SEED_CONTENT["skills"]:
            try:
                conn.execute(
                    text("""
                        INSERT INTO cortex.skills_registry (skill_id, skill_name, subject, grade_level, description)
                        VALUES (:skill_id, :skill_name, :subject, :grade_level, :description)
                        ON CONFLICT (skill_id) DO NOTHING
                    """),
                    {
                        "skill_id": skill["skill_id"],
                        "skill_name": skill["skill_name"],
                        "subject": SEED_CONTENT["subject"],
                        "grade_level": SEED_CONTENT["grade_level"],
                        "description": skill["description"]
                    }
                )
                count += 1
            except Exception as e:
                print(f"  Warning: Failed to insert skill {skill['skill_id']}: {e}")

        conn.commit()

    print(f"✓ Seeded {count} skills")
    return count


def seed_textbook_chunks(engine) -> int:
    """Seed the textbook_chunks table with chapter content."""
    count = 0

    with engine.connect() as conn:
        for section in SEED_CONTENT["sections"]:
            # Create a simple embedding (all zeros for now - would use real embeddings)
            embedding = np.zeros(768, dtype=np.float32)  # nomic-embed-text dimension

            result = conn.execute(
                text("""
                    INSERT INTO cortex.textbook_chunks (
                        chapter_id, section_id, content, embedding, grade_level, subject, metadata
                    )
                    VALUES (:chapter_id, :section_id, :content, :embedding, :grade_level, :subject, :metadata)
                    ON CONFLICT DO NOTHING
                    RETURNING id
                """),
                {
                    "chapter_id": SEED_CONTENT["chapter_id"],
                    "section_id": section["section_id"],
                    "content": section["content"].strip(),
                    "embedding": list(embedding),
                    "grade_level": SEED_CONTENT["grade_level"],
                    "subject": SEED_CONTENT["subject"],
                    "metadata": {
                        "title": section["title"],
                        "section_id": section["section_id"],
                        "concepts": section["concepts"]
                    }
                }
            )

            if result.rowcount > 0:
                count += 1

        conn.commit()

    print(f"✓ Seeded {count} textbook sections")
    return count


def seed_graph_nodes(engine) -> int:
    """Seed the graph_nodes table with ontology concepts."""
    count = 0

    with engine.connect() as conn:
        for node in GRAPH_ONTOLOGY["nodes"]:
            try:
                result = conn.execute(
                    text("""
                        INSERT INTO cortex.graph_nodes (graph_name, node_id, label, properties)
                        VALUES ('kda_curriculum', :node_id, :label, :properties)
                        ON CONFLICT (graph_name, node_id) DO UPDATE
                        SET label = EXCLUDED.label, properties = EXCLUDED.properties
                        RETURNING id
                    """),
                    {
                        "node_id": hash(node["label"]) % 1000000,  # Simple ID generation
                        "label": node["label"],
                        "properties": node["properties"]
                    }
                )

                if result.rowcount > 0:
                    count += 1

            except Exception as e:
                print(f"  Warning: Failed to insert node {node['label']}: {e}")

        conn.commit()

    print(f"✓ Seeded {count} graph nodes")
    return count


def seed_graph_edges(engine) -> int:
    """Seed the graph_edges table with ontology relationships."""
    count = 0

    with engine.connect() as conn:
        for edge in GRAPH_ONTOLOGY["edges"]:
            try:
                result = conn.execute(
                    text("""
                        INSERT INTO cortex.graph_edges (
                            graph_name, edge_id, start_node_id, end_node_id, edge_label, properties
                        )
                        VALUES (
                            'kda_curriculum',
                            :edge_id,
                            :start_node_id,
                            :end_node_id,
                            :edge_label,
                            :properties
                        )
                        ON CONFLICT (graph_name, edge_id) DO UPDATE
                        SET edge_label = EXCLUDED.edge_label, properties = EXCLUDED.properties
                        RETURNING id
                    """),
                    {
                        "edge_id": hash(f"{edge['from']}-{edge['to']}") % 1000000,
                        "start_node_id": hash(edge["from"]) % 1000000,
                        "end_node_id": hash(edge["to"]) % 1000000,
                        "edge_label": edge["label"],
                        "properties": edge.get("properties", {})
                    }
                )

                if result.rowcount > 0:
                    count += 1

            except Exception as e:
                print(f"  Warning: Failed to insert edge {edge['from']}->{edge['to']}: {e}")

        conn.commit()

    print(f"✓ Seeded {count} graph edges")
    return count


def seed_sample_user(engine) -> None:
    """Create a sample user for testing."""
    with engine.connect() as conn:
        # Create a sample learning event
        conn.execute(
            text("""
                INSERT INTO cortex.learning_events (user_id, skill_id, is_correct, attempts, metadata)
                VALUES (:user_id, :skill_id, :is_correct, :attempts, :metadata)
                ON CONFLICT DO NOTHING
            """),
            {
                "user_id": "sample-user-001",
                "skill_id": "membrane-structure",
                "is_correct": True,
                "attempts": 1,
                "metadata": {"seed_data": True}
            }
        )

        conn.commit()

    print("✓ Created sample user for testing")


def verify_content(engine) -> Dict[str, Any]:
    """Verify that content was seeded correctly."""
    with engine.connect() as conn:
        # Count textbook chunks
        chunks_result = conn.execute(
            text("SELECT COUNT(*) as count FROM cortex.textbook_chunks")
        )
        chunks_count = chunks_result.fetchone()[0]

        # Count graph nodes
        nodes_result = conn.execute(
            text("SELECT COUNT(*) as count FROM cortex.graph_nodes WHERE graph_name = 'kda_curriculum'")
        )
        nodes_count = nodes_result.fetchone()[0]

        # Count graph edges
        edges_result = conn.execute(
            text("SELECT COUNT(*) as count FROM cortex.graph_edges WHERE graph_name = 'kda_curriculum'")
        )
        edges_count = edges_result.fetchone()[0]

        # Count skills
        skills_result = conn.execute(
            text("SELECT COUNT(*) as count FROM cortex.skills_registry")
        )
        skills_count = skills_result.fetchone()[0]

        return {
            "textbook_chunks": chunks_count,
            "graph_nodes": nodes_count,
            "graph_edges": edges_count,
            "skills": skills_count
        }


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Seed Mu2 Cognitive OS with initial content")
    parser.add_argument("--verify", action="store_true", help="Verify content was seeded")
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    args = parser.parse_args()

    if not args.quiet:
        print("")
        print("╔══════════════════════════════════════════════════════════════════════╗")
        print("║  Mu2 Cognitive OS - Content Seeder                                   ║")
        print("║  OpenStax Biology Chapter 5: Plasma Membranes                       ║")
        print("╚══════════════════════════════════════════════════════════════════════╝")
        print("")

    engine = get_db_connection()

    if args.verify:
        if not args.quiet:
            print("Verifying seeded content...")
        counts = verify_content(engine)
        if not args.quiet:
            print("")
            print("Content Summary:")
            print(f"  Textbook chunks: {counts['textbook_chunks']}")
            print(f"  Graph nodes: {counts['graph_nodes']}")
            print(f"  Graph edges: {counts['graph_edges']}")
            print(f"  Skills: {counts['skills']}")
            print("")

            if counts["textbook_chunks"] > 0:
                print("✓ Content seeding verified")
                return 0
            else:
                print("✗ No content found - run without --verify to seed")
                return 1
        return 0

    # Seed all content
    if not args.quiet:
        print("Seeding content...")

    try:
        seed_skills_registry(engine)
        seed_textbook_chunks(engine)
        seed_graph_nodes(engine)
        seed_graph_edges(engine)
        seed_sample_user(engine)

        if not args.quiet:
            print("")
            print("╔══════════════════════════════════════════════════════════════════════╗")
            print("║  ✓ Content seeding complete!                                       ║")
            print("║  The Living Textbook is ready for use.                             ║")
            print("╚══════════════════════════════════════════════════════════════════════╝")
            print("")

            counts = verify_content(engine)
            print(f"  Textbook sections: {counts['textbook_chunks']}")
            print(f"  Graph concepts: {counts['graph_nodes']}")
            print(f"  Graph relationships: {counts['graph_edges']}")
            print(f"  Skills available: {counts['skills']}")
            print("")

        return 0

    except Exception as e:
        print(f"✗ Error seeding content: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
