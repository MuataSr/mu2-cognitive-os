"""
Graph Store Service for Mu2 Cognitive OS
Integrates with Apache AGE for concept relationship queries
"""

import asyncio
from typing import List, Dict, Any, Optional
import json
import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from src.core.config import settings


class GraphStoreService:
    """Service for managing Apache AGE graph operations"""

    def __init__(self):
        self.conn: Optional[psycopg.AsyncConnection] = None
        self._initialized = False

    async def initialize(self):
        """Initialize the graph store connection"""
        if self._initialized:
            return

        # Connect to PostgreSQL
        self.conn = await psycopg.AsyncConnection.connect(
            conninfo=settings.database_url,
            autocommit=True,
        )

        # Load AGE extension
        await self._load_age_extension()

        # Initialize graph schema if not exists
        await self._ensure_graph_schema()

        self._initialized = True

    async def _load_age_extension(self):
        """Load Apache AGE extension"""
        async with self.conn.cursor() as cur:
            await cur.execute("LOAD 'age';")
            await cur.execute("SET search_path = ag_catalog, '$user', public;")

    async def _ensure_graph_schema(self):
        """Ensure the graph schema exists"""
        # Check if graph exists
        graph_exists = await self.graph_exists("kda_curriculum")

        if not graph_exists:
            await self.create_graph("kda_curriculum")
            # Create sample curriculum data
            await self._seed_curriculum_data()

    async def ensure_initialized(self):
        """Ensure the service is initialized"""
        if not self._initialized:
            await self.initialize()

    async def create_graph(self, graph_name: str) -> bool:
        """
        Create a new graph in Apache AGE

        Args:
            graph_name: Name of the graph

        Returns:
            True if successful
        """
        await self.ensure_initialized()

        async with self.conn.cursor() as cur:
            try:
                await cur.execute(
                    sql.SQL("SELECT create_graph(%s);"), [graph_name]
                )
                return True
            except Exception as e:
                # Graph might already exist
                print(f"Graph creation note: {e}")
                return False

    async def graph_exists(self, graph_name: str) -> bool:
        """Check if a graph exists"""
        await self.ensure_initialized()

        async with self.conn.cursor() as cur:
            await cur.execute(
                "SELECT * FROM ag_graph WHERE name = %s;", [graph_name]
            )
            result = await cur.fetchone()
            return result is not None

    async def add_concept(
        self,
        concept_id: str,
        name: str,
        description: str,
        grade_level: int,
        subject: str = "science",
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Add a concept node to the graph

        Args:
            concept_id: Unique identifier for the concept
            name: Concept name
            description: Concept description
            grade_level: Target grade level
            subject: Subject area
            properties: Additional properties

        Returns:
            True if successful
        """
        await self.ensure_initialized()

        props = {
            "id": concept_id,
            "name": name,
            "description": description,
            "grade_level": grade_level,
            "subject": subject,
            **(properties or {}),
        }

        query = f"""
        SELECT * FROM cypher('kda_curriculum', $$
            CREATE (c:Concept {{
                id: '{concept_id}',
                name: '{name}',
                description: '{description.replace("'", "\\'")}',
                grade_level: {grade_level},
                subject: '{subject}',
                properties: '{json.dumps(props)}'
            }})
            RETURN c
        $$) as (c agtype);
        """

        async with self.conn.cursor() as cur:
            await cur.execute(query)
            return True

    async def add_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Add a relationship between two concepts

        Args:
            source_id: Source concept ID
            target_id: Target concept ID
            rel_type: Relationship type (e.g., "PREREQUISITE", "RELATED_TO")
            properties: Additional properties

        Returns:
            True if successful
        """
        await self.ensure_initialized()

        props_json = json.dumps(properties or {})

        query = f"""
        SELECT * FROM cypher('kda_curriculum', $$
            MATCH (source:Concept {{id: '{source_id}'}})
            MATCH (target:Concept {{id: '{target_id}'}})
            CREATE (source)-[r:{rel_type} {{properties: '{props_json}'}}]->(target)
            RETURN r
        $$) as (r agtype);
        """

        async with self.conn.cursor() as cur:
            await cur.execute(query)
            return True

    async def get_concept(
        self, concept_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a concept by ID

        Args:
            concept_id: Concept ID

        Returns:
            Concept data or None
        """
        await self.ensure_initialized()

        query = f"""
        SELECT * FROM cypher('kda_curriculum', $$
            MATCH (c:Concept {{id: '{concept_id}'}})
            RETURN c
        $$) as (c agtype);
        """

        async with self.conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query)
            result = await cur.fetchone()

            if result:
                concept_data = json.loads(result["c"])
                return {
                    "id": concept_data["id"],
                    "name": concept_data["name"],
                    "description": concept_data["description"],
                    "grade_level": concept_data["grade_level"],
                    "subject": concept_data["subject"],
                    "properties": concept_data.get("properties", {}),
                }
            return None

    async def get_concept_relationships(
        self, concept_name: str, depth: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Get relationships for a concept

        Args:
            concept_name: Name of the concept
            depth: Depth of traversal (default: 2)

        Returns:
            List of related concepts with relationships
        """
        await self.ensure_initialized()

        query = f"""
        SELECT * FROM cypher('kda_curriculum', $$
            MATCH (c:Concept {{name: '{concept_name}'}})-[r]-(related:Concept)
            RETURN c.name as source, type(r) as relationship,
                   related.name as target, related.description as description,
                   related.grade_level as grade_level
            LIMIT 20
        $$) as (source varchar, relationship varchar, target varchar,
                description varchar, grade_level int);
        """

        async with self.conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query)
            results = await cur.fetchall()

            return [
                {
                    "source": row["source"],
                    "relationship": row["relationship"],
                    "target": row["target"],
                    "description": row["description"],
                    "grade_level": row["grade_level"],
                }
                for row in results
            ]

    async def find_path(
        self, source_concept: str, target_concept: str
    ) -> List[Dict[str, Any]]:
        """
        Find a path between two concepts

        Args:
            source_concept: Source concept name
            target_concept: Target concept name

        Returns:
            List of concepts forming the path
        """
        await self.ensure_initialized()

        query = f"""
        SELECT * FROM cypher('kda_curriculum', $$
            MATCH path = shortestPath(
                (source:Concept {{name: '{source_concept}'}})-[*..5]-(target:Concept {{name: '{target_concept}'}})
            )
            RETURN [node in nodes(path) | node.name] as concept_path,
                   [rel in relationships(path) | type(rel)] as relationships
        $$) as (concept_path varchar[], relationships varchar[]);
        """

        async with self.conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query)
            result = await cur.fetchone()

            if result:
                return {
                    "concepts": result["concept_path"],
                    "relationships": result["relationships"],
                }
            return []

    async def search_concepts(
        self, search_term: str, subject: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for concepts by name or description

        Args:
            search_term: Search term
            subject: Optional subject filter

        Returns:
            List of matching concepts
        """
        await self.ensure_initialized()

        subject_filter = f"AND c.subject = '{subject}'" if subject else ""

        query = f"""
        SELECT * FROM cypher('kda_curriculum', $$
            MATCH (c:Concept)
            WHERE c.name CONTAINS '{search_term}' OR c.description CONTAINS '{search_term}'
            {subject_filter}
            RETURN c.name as name, c.description as description,
                   c.grade_level as grade_level, c.subject as subject, c.id as id
            LIMIT 10
        $$) as (name varchar, description varchar, grade_level int, subject varchar, id varchar);
        """

        async with self.conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query)
            results = await cur.fetchall()

            return [
                {
                    "name": row["name"],
                    "description": row["description"],
                    "grade_level": row["grade_level"],
                    "subject": row["subject"],
                    "id": row["id"],
                }
                for row in results
            ]

    async def get_prerequisites(
        self, concept_name: str
    ) -> List[Dict[str, Any]]:
        """
        Get prerequisites for a concept

        Args:
            concept_name: Concept name

        Returns:
            List of prerequisite concepts
        """
        await self.ensure_initialized()

        query = f"""
        SELECT * FROM cypher('kda_curriculum', $$
            MATCH (c:Concept {{name: '{concept_name}'}})<-[r:PREREQUISITE]-(prereq:Concept)
            RETURN prereq.name as name, prereq.description as description,
                   prereq.grade_level as grade_level
            ORDER BY prereq.grade_level
        $$) as (name varchar, description varchar, grade_level int);
        """

        async with self.conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query)
            results = await cur.fetchall()

            return [
                {
                    "name": row["name"],
                    "description": row["description"],
                    "grade_level": row["grade_level"],
                }
                for row in results
            ]

    async def _seed_curriculum_data(self):
        """Seed the graph with sample curriculum data"""
        # Add concepts
        concepts = [
            {
                "id": "photosynthesis",
                "name": "Photosynthesis",
                "description": "The process by which plants convert light energy into chemical energy",
                "grade_level": 6,
                "subject": "science",
            },
            {
                "id": "sunlight",
                "name": "Sunlight",
                "description": "Solar energy that provides light and heat to Earth",
                "grade_level": 3,
                "subject": "science",
            },
            {
                "id": "chlorophyll",
                "name": "Chlorophyll",
                "description": "Green pigment in plants that absorbs light for photosynthesis",
                "grade_level": 7,
                "subject": "science",
            },
            {
                "id": "energy",
                "name": "Energy",
                "description": "The capacity to do work or cause change",
                "grade_level": 4,
                "subject": "science",
            },
            {
                "id": "glucose",
                "name": "Glucose",
                "description": "A type of sugar produced during photosynthesis",
                "grade_level": 6,
                "subject": "science",
            },
        ]

        for concept in concepts:
            await self.add_concept(**concept)

        # Add relationships
        await self.add_relationship("sunlight", "photosynthesis", "ENABLES")
        await self.add_relationship("chlorophyll", "photosynthesis", "REQUIRED_FOR")
        await self.add_relationship("energy", "photosynthesis", "TRANSFORMS_INTO")
        await self.add_relationship("photosynthesis", "glucose", "PRODUCES")
        await self.add_relationship("sunlight", "energy", "SOURCE_OF")

    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the graph store service

        Returns:
            Health status information
        """
        try:
            await self.ensure_initialized()

            # Test query
            result = await self.search_concepts("photosynthesis")

            return {
                "status": "healthy",
                "graph_exists": await self.graph_exists("kda_curriculum"),
                "connection_active": self.conn is not None,
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def close(self):
        """Close the database connection"""
        if self.conn:
            await self.conn.close()
            self._initialized = False


# Global singleton instance
graph_store_service = GraphStoreService()
