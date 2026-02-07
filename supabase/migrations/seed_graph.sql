-- ============================================================================
-- Seed Graph Data for KDA Curriculum
-- Apache AGE Graph Initialization with Science Concepts Ontology
-- ============================================================================

-- This script populates the kda_curriculum graph with a foundational
-- ontology of 8th-grade science concepts covering:
-- - Biology (Cells, Photosynthesis, Ecosystems)
-- - Physics (Energy, Forces, Motion)
-- - Chemistry (Matter, Atoms, Elements)
-- - Earth Science (Water Cycle, Weather, Plate Tectonics)

-- ============================================================================
-- Note: This script should be run AFTER migration 002 and AFTER
-- initializing the Apache AGE graph with: SELECT create_graph('kda_curriculum');
-- ============================================================================

-- Load Apache AGE extension
LOAD 'age';
SET search_path TO ag_catalog, "$user", public;

-- ============================================================================
-- GRAPH INITIALIZATION
-- ============================================================================

-- Create the graph (idempotent - will fail if exists, that's OK)
DO $$
BEGIN
    PERFORM create_graph('kda_curriculum');
EXCEPTION
    WHEN duplicate_table THEN
        RAISE NOTICE 'Graph kda_curriculum already exists';
END $$;

-- ============================================================================
-- HELPER FUNCTION: Create Node and Return ID
-- ============================================================================

CREATE OR REPLACE FUNCTION cortex.create_concept_node(
    p_label TEXT,
    p_properties JSONB DEFAULT '{}'
)
RETURNS BIGINT AS $$
DECLARE
    v_graph_name TEXT := 'kda_curriculum';
    v_query TEXT;
    v_result BIGINT;
BEGIN
    -- Create node using cypher function
    v_query := format(
        'SELECT * FROM cypher(''%s'', $$
            CREATE (n:Concept {%s})
            RETURN n
        $$) as (n agtype)',
        v_graph_name,
        CASE
            WHEN p_properties = '{}' THEN
                format('label: "%s"', p_label)
            ELSE
                format('label: "%s", %s', p_label, p_properties::text)
        END
    );

    EXECUTE v_query INTO v_result;

    -- Also create entry in relational mirror
    INSERT INTO cortex.graph_nodes (node_id, label, properties, graph_name)
    VALUES (v_result, p_label, p_properties, v_graph_name)
    ON CONFLICT (graph_name, node_id) DO NOTHING;

    RETURN v_result;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- HELPER FUNCTION: Create Edge Between Nodes
-- ============================================================================

CREATE OR REPLACE FUNCTION cortex.create_concept_edge(
    p_start_label TEXT,
    p_end_label TEXT,
    p_edge_label TEXT,
    p_properties JSONB DEFAULT '{}'
)
RETURNS BIGINT AS $$
DECLARE
    v_graph_name TEXT := 'kda_curriculum';
    v_query TEXT;
    v_result BIGINT;
    v_start_id BIGINT;
    v_end_id BIGINT;
BEGIN
    -- Get node IDs
    SELECT node_id INTO v_start_id
    FROM cortex.graph_nodes
    WHERE graph_name = v_graph_name AND label = p_start_label
    LIMIT 1;

    SELECT node_id INTO v_end_id
    FROM cortex.graph_nodes
    WHERE graph_name = v_graph_name AND label = p_end_label
    LIMIT 1;

    IF v_start_id IS NULL OR v_end_id IS NULL THEN
        RAISE EXCEPTION 'Cannot find nodes: % -> %', p_start_label, p_end_label;
    END IF;

    -- Create edge using cypher
    v_query := format(
        'SELECT * FROM cypher(''%s'', $$
            MATCH (a:Concept), (b:Concept)
            WHERE id(a) = %s AND id(b) = %s
            CREATE (a)-[r:%s {%s}]->(b)
            RETURN r
        $$) as (r agtype)',
        v_graph_name,
        v_start_id,
        v_end_id,
        p_edge_label,
        CASE
            WHEN p_properties = '{}' THEN ''
            ELSE p_properties::text
        END
    );

    EXECUTE v_query INTO v_result;

    -- Also create entry in relational mirror
    INSERT INTO cortex.graph_edges (edge_id, start_node_id, end_node_id, edge_label, properties, graph_name)
    VALUES (v_result, v_start_id, v_end_id, p_edge_label, p_properties, v_graph_name)
    ON CONFLICT (graph_name, edge_id) DO NOTHING;

    RETURN v_result;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- BIOLOGY DOMAIN: Cells, Photosynthesis, Ecosystems
-- ============================================================================

-- Core Concepts
-- Note: Using direct INSERT into graph_nodes for simplicity
-- In production, use AGE Cypher queries

-- Cell Biology Concepts
INSERT INTO cortex.graph_nodes (graph_name, node_id, label, properties) VALUES
('kda_curriculum', 1, 'Cell', '{"domain": "Biology", "grade_level": 8, "description": "The basic unit of life"}'),
('kda_curriculum', 2, 'Nucleus', '{"domain": "Biology", "grade_level": 8, "description": "Control center of the cell containing DNA"}'),
('kda_curriculum', 3, 'Mitochondria', '{"domain": "Biology", "grade_level": 8, "description": "Powerhouse of the cell, produces energy"}'),
('kda_curriculum', 4, 'Chloroplast', '{"domain": "Biology", "grade_level": 8, "description": "Organelle where photosynthesis occurs"}'),
('kda_curriculum', 5, 'Cell Membrane', '{"domain": "Biology", "grade_level": 8, "description": "Protective boundary controlling what enters/exits"}'),
('kda_curriculum', 6, 'Cytoplasm', '{"domain": "Biology", "grade_level": 8, "description": "Gel-like fluid inside the cell"}'),
('kda_curriculum', 7, 'Photosynthesis', '{"domain": "Biology", "grade_level": 8, "description": "Process plants use to make food from sunlight"}'),
('kda_curriculum', 8, 'Sunlight', '{"domain": "Biology", "grade_level": 8, "description": "Energy source for photosynthesis"}'),
('kda_curriculum', 9, 'Oxygen', '{"domain": "Biology", "grade_level": 8, "description": "Gas produced by photosynthesis"}'),
('kda_curriculum', 10, 'Carbon Dioxide', '{"domain": "Biology", "grade_level": 8, "description": "Gas used in photosynthesis"}'),
('kda_curriculum', 11, 'Glucose', '{"domain": "Biology", "grade_level": 8, "description": "Sugar produced during photosynthesis"}'),
('kda_curriculum', 12, 'Water', '{"domain": "Biology", "grade_level": 8, "description": "Essential for photosynthesis"}')
ON CONFLICT (graph_name, node_id) DO NOTHING;

-- Ecosystem Concepts
INSERT INTO cortex.graph_nodes (graph_name, node_id, label, properties) VALUES
('kda_curriculum', 20, 'Ecosystem', '{"domain": "Biology", "grade_level": 8, "description": "Community of living and non-living things"}'),
('kda_curriculum', 21, 'Producer', '{"domain": "Biology", "grade_level": 8, "description": "Organism that makes its own food"}'),
('kda_curriculum', 22, 'Consumer', '{"domain": "Biology", "grade_level": 8, "description": "Organism that eats other organisms"}'),
('kda_curriculum', 23, 'Decomposer', '{"domain": "Biology", "grade_level": 8, "description": "Organism that breaks down dead matter"}'),
('kda_curriculum', 24, 'Food Chain', '{"domain": "Biology", "grade_level": 8, "description": "Sequence of who eats whom"}'),
('kda_curriculum', 25, 'Food Web', '{"domain": "Biology", "grade_level": 8, "description": "Interconnected food chains"}')
ON CONFLICT (graph_name, node_id) DO NOTHING;

-- Cell Structure Relationships
INSERT INTO cortex.graph_edges (graph_name, edge_id, start_node_id, end_node_id, edge_label, properties) VALUES
('kda_curriculum', 101, 1, 2, 'CONTAINS', '{"context": "Cell contains nucleus"}'),
('kda_curriculum', 102, 1, 3, 'CONTAINS', '{"context": "Cell contains mitochondria"}'),
('kda_curriculum', 103, 1, 4, 'CONTAINS', '{"context": "Plant cells contain chloroplasts"}'),
('kda_curriculum', 104, 1, 5, 'HAS', '{"context": "Cell has a membrane"}'),
('kda_curriculum', 105, 1, 6, 'CONTAINS', '{"context": "Cell contains cytoplasm"}'),
('kda_curriculum', 106, 2, 3, 'REGULATES', '{"context": "Nucleus regulates mitochondria"}'),
('kda_curriculum', 107, 3, 11, 'PRODUCES', '{"context": "Mitochondria produces energy from glucose"}')
ON CONFLICT (graph_name, edge_id) DO NOTHING;

-- Photosynthesis Relationships
INSERT INTO cortex.graph_edges (graph_name, edge_id, start_node_id, end_node_id, edge_label, properties) VALUES
('kda_curriculum', 201, 7, 8, 'REQUIRES', '{"importance": "high", "context": "Photosynthesis needs sunlight"}'),
('kda_curriculum', 202, 7, 10, 'USES', '{"importance": "high", "context": "Uses carbon dioxide"}'),
('kda_curriculum', 203, 7, 12, 'USES', '{"importance": "high", "context": "Uses water"}'),
('kda_curriculum', 204, 7, 9, 'PRODUCES', '{"importance": "high", "context": "Produces oxygen"}'),
('kda_curriculum', 205, 7, 11, 'PRODUCES', '{"importance": "high", "context": "Produces glucose"}'),
('kda_curriculum', 206, 4, 7, 'SITE_OF', '{"context": "Chloroplast is site of photosynthesis"}'),
('kda_curriculum', 207, 11, 3, 'FEEDS', '{"context": "Glucose feeds mitochondria"}')
ON CONFLICT (graph_name, edge_id) DO NOTHING;

-- Ecosystem Relationships
INSERT INTO cortex.graph_edges (graph_name, edge_id, start_node_id, end_node_id, edge_label, properties) VALUES
('kda_curriculum', 301, 20, 7, 'INCLUDES', '{"context": "Ecosystems include photosynthesis"}'),
('kda_curriculum', 302, 20, 21, 'INCLUDES', '{"context": "Ecosystems have producers"}'),
('kda_curriculum', 303, 20, 22, 'INCLUDES', '{"context": "Ecosystems have consumers"}'),
('kda_curriculum', 304, 20, 23, 'INCLUDES', '{"context": "Ecosystems have decomposers"}'),
('kda_curriculum', 305, 21, 7, 'PERFORMS', '{"context": "Producers perform photosynthesis"}'),
('kda_curriculum', 306, 22, 21, 'EATS', '{"context": "Consumers eat producers"}'),
('kda_curriculum', 307, 24, 21, 'STARTS_WITH', '{"context": "Food chains start with producers"}'),
('kda_curriculum', 308, 25, 24, 'INCLUDES', '{"context": "Food webs include food chains"}')
ON CONFLICT (graph_name, edge_id) DO NOTHING;

-- ============================================================================
-- PHYSICS DOMAIN: Energy, Forces, Motion
-- ============================================================================

INSERT INTO cortex.graph_nodes (graph_name, node_id, label, properties) VALUES
('kda_curriculum', 50, 'Energy', '{"domain": "Physics", "grade_level": 8, "description": "Ability to do work or cause change"}'),
('kda_curriculum', 51, 'Kinetic Energy', '{"domain": "Physics", "grade_level": 8, "description": "Energy of motion"}'),
('kda_curriculum', 52, 'Potential Energy', '{"domain": "Physics", "grade_level": 8, "description": "Stored energy"}'),
('kda_curriculum', 53, 'Force', '{"domain": "Physics", "grade_level": 8, "description": "Push or pull on an object"}'),
('kda_curriculum', 54, 'Gravity', '{"domain": "Physics", "grade_level": 8, "description": "Force that pulls objects toward each other"}'),
('kda_curriculum', 55, 'Motion', '{"domain": "Physics", "grade_level": 8, "description": "Change in position over time"}'),
('kda_curriculum', 56, 'Speed', '{"domain": "Physics", "grade_level": 8, "description": "How fast something moves"}'),
('kda_curriculum', 57, 'Velocity', '{"domain": "Physics", "grade_level": 8, "description": "Speed in a specific direction"}'),
('kda_curriculum', 58, 'Acceleration', '{"domain": "Physics", "grade_level": 8, "description": "Change in velocity over time"}')
ON CONFLICT (graph_name, node_id) DO NOTHING;

-- Physics Relationships
INSERT INTO cortex.graph_edges (graph_name, edge_id, start_node_id, end_node_id, edge_label, properties) VALUES
('kda_curriculum', 501, 50, 51, 'INCLUDES', '{"context": "Energy includes kinetic energy"}'),
('kda_curriculum', 502, 50, 52, 'INCLUDES', '{"context": "Energy includes potential energy"}'),
('kda_curriculum', 503, 51, 55, 'CAUSES', '{"context": "Kinetic energy causes motion"}'),
('kda_curriculum', 504, 52, 51, 'BECOMES', '{"context": "Potential energy becomes kinetic"}'),
('kda_curriculum', 505, 53, 55, 'CAUSES', '{"context": "Force causes motion"}'),
('kda_curriculum', 506, 54, 53, 'IS_A', '{"context": "Gravity is a force"}'),
('kda_curriculum', 507, 53, 58, 'CAUSES', '{"context": "Force causes acceleration"}'),
('kda_curriculum', 508, 55, 56, 'HAS', '{"context": "Motion has speed"}'),
('kda_curriculum', 509, 55, 57, 'HAS', '{"context": "Motion can have velocity"}'),
('kda_curriculum', 510, 57, 58, 'CAN_HAVE', '{"context": "Velocity can have acceleration"}')
ON CONFLICT (graph_name, edge_id) DO NOTHING;

-- ============================================================================
-- CHEMISTRY DOMAIN: Matter, Atoms, Elements
-- ============================================================================

INSERT INTO cortex.graph_nodes (graph_name, node_id, label, properties) VALUES
('kda_curriculum', 70, 'Matter', '{"domain": "Chemistry", "grade_level": 8, "description": "Anything that has mass and takes up space"}'),
('kda_curriculum', 71, 'Atom', '{"domain": "Chemistry", "grade_level": 8, "description": "Smallest unit of an element"}'),
('kda_curriculum', 72, 'Element', '{"domain": "Chemistry", "grade_level": 8, "description": "Pure substance made of only one type of atom"}'),
('kda_curriculum', 73, 'Molecule', '{"domain": "Chemistry", "grade_level": 8, "description": "Two or more atoms bonded together"}'),
('kda_curriculum', 74, 'Compound', '{"domain": "Chemistry", "grade_level": 8, "description": "Substance made of two or more elements"}'),
('kda_curriculum', 75, 'Proton', '{"domain": "Chemistry", "grade_level": 8, "description": "Positive particle in nucleus"}'),
('kda_curriculum', 76, 'Neutron', '{"domain": "Chemistry", "grade_level": 8, "description": "Neutral particle in nucleus"}'),
('kda_curriculum', 77, 'Electron', '{"domain": "Chemistry", "grade_level": 8, "description": "Negative particle orbiting nucleus"}')
ON CONFLICT (graph_name, node_id) DO NOTHING;

-- Chemistry Relationships
INSERT INTO cortex.graph_edges (graph_name, edge_id, start_node_id, end_node_id, edge_label, properties) VALUES
('kda_curriculum', 601, 70, 71, 'MADE_OF', '{"context": "Matter is made of atoms"}'),
('kda_curriculum', 602, 72, 71, 'CONTAINS', '{"context": "Elements contain atoms"}'),
('kda_curriculum', 603, 73, 71, 'MADE_OF', '{"context": "Molecules are made of atoms"}'),
('kda_curriculum', 604, 74, 72, 'MADE_OF', '{"context": "Compounds are made of elements"}'),
('kda_curriculum', 605, 71, 75, 'CONTAINS', '{"context": "Atoms contain protons"}'),
('kda_curriculum', 606, 71, 76, 'CONTAINS', '{"context": "Atoms contain neutrons"}'),
('kda_curriculum', 607, 71, 77, 'CONTAINS', '{"context": "Atoms contain electrons"}'),
('kda_curriculum', 608, 11, 73, 'IS_A', '{"context": "Glucose is a molecule"}'),
('kda_curriculum', 609, 12, 73, 'IS_A', '{"context": "Water is a molecule"}')
ON CONFLICT (graph_name, edge_id) DO NOTHING;

-- ============================================================================
-- EARTH SCIENCE DOMAIN: Water Cycle, Weather, Plate Tectonics
-- ============================================================================

INSERT INTO cortex.graph_nodes (graph_name, node_id, label, properties) VALUES
('kda_curriculum', 90, 'Water Cycle', '{"domain": "Earth Science", "grade_level": 8, "description": "Continuous movement of water on Earth"}'),
('kda_curriculum', 91, 'Evaporation', '{"domain": "Earth Science", "grade_level": 8, "description": "Water changing from liquid to gas"}'),
('kda_curriculum', 92, 'Condensation', '{"domain": "Earth Science", "grade_level": 8, "description": "Water changing from gas to liquid"}'),
('kda_curriculum', 93, 'Precipitation', '{"domain": "Earth Science", "grade_level": 8, "description": "Water falling from clouds"}'),
('kda_curriculum', 94, 'Weather', '{"domain": "Earth Science", "grade_level": 8, "description": "Condition of atmosphere at a place and time"}'),
('kda_curriculum', 95, 'Climate', '{"domain": "Earth Science", "grade_level": 8, "description": "Average weather over long period"}'),
('kda_curriculum', 96, 'Plate Tectonics', '{"domain": "Earth Science", "grade_level": 8, "description": "Theory of Earth moving plates"}'),
('kda_curriculum', 97, 'Earthquake', '{"domain": "Earth Science", "grade_level": 8, "description": "Shaking from plate movement"}'),
('kda_curriculum', 98, 'Volcano', '{"domain": "Earth Science", "grade_level": 8, "description": "Opening where lava erupts"}')
ON CONFLICT (graph_name, node_id) DO NOTHING;

-- Earth Science Relationships
INSERT INTO cortex.graph_edges (graph_name, edge_id, start_node_id, end_node_id, edge_label, properties) VALUES
('kda_curriculum', 701, 90, 91, 'INCLUDES', '{"context": "Water cycle includes evaporation"}'),
('kda_curriculum', 702, 90, 92, 'INCLUDES', '{"context": "Water cycle includes condensation"}'),
('kda_curriculum', 703, 90, 93, 'INCLUDES', '{"context": "Water cycle includes precipitation"}'),
('kda_curriculum', 704, 94, 90, 'AFFECTED_BY', '{"context": "Weather affected by water cycle"}'),
('kda_curriculum', 705, 95, 94, 'RELATED_TO', '{"context": "Climate related to weather"}'),
('kda_curriculum', 706, 96, 97, 'CAUSES', '{"context": "Plate tectonics causes earthquakes"}'),
('kda_curriculum', 707, 96, 98, 'CAUSES', '{"context": "Plate tectonics causes volcanoes"}'),
('kda_curriculum', 708, 20, 90, 'INCLUDES', '{"context": "Ecosystem includes water cycle"}')
ON CONFLICT (graph_name, edge_id) DO NOTHING;

-- ============================================================================
-- CROSS-DOMAIN CONNECTIONS
-- ============================================================================

-- Biology-Chemistry Connections
INSERT INTO cortex.graph_edges (graph_name, edge_id, start_node_id, end_node_id, edge_label, properties) VALUES
('kda_curriculum', 801, 1, 71, 'MADE_OF', '{"context": "Cells are made of atoms"}'),
('kda_curriculum', 802, 7, 73, 'PRODUCES', '{"context": "Photosynthesis produces molecules"}')
ON CONFLICT (graph_name, edge_id) DO NOTHING;

-- Physics-Biology Connections
INSERT INTO cortex.graph_edges (graph_name, edge_id, start_node_id, end_node_id, edge_label, properties) VALUES
('kda_curriculum', 901, 8, 50, 'IS', '{"context": "Sunlight is energy"}'),
('kda_curriculum', 902, 7, 50, 'TRANSFORMS', '{"context": "Photosynthesis transforms energy"}'),
('kda_curriculum', 903, 54, 12, 'AFFECTS', '{"context": "Gravity affects water"}')
ON CONFLICT (graph_name, edge_id) DO NOTHING;

-- Physics-Earth Science Connections
INSERT INTO cortex.graph_edges (graph_name, edge_id, start_node_id, end_node_id, edge_label, properties) VALUES
('kda_curriculum', 1001, 53, 97, 'CAUSES', '{"context": "Forces cause earthquakes"}'),
('kda_curriculum', 1002, 50, 91, 'PROVIDES', '{"context": "Energy provides for evaporation"}')
ON CONFLICT (graph_name, edge_id) DO NOTHING;

-- ============================================================================
-- GRANTS AND FINAL SETUP
-- ============================================================================

-- Ensure proper permissions
GRANT SELECT ON cortex.graph_nodes TO authenticated;
GRANT SELECT ON cortex.graph_edges TO authenticated;
GRANT SELECT, INSERT ON cortex.chunk_concept_links TO authenticated;

-- Create a view to visualize the graph statistics
CREATE OR REPLACE VIEW cortex.curriculum_graph_stats AS
SELECT
    g.domain,
    COUNT(DISTINCT gn.node_id) as concept_count,
    COUNT(DISTINCT ge.edge_id) as relationship_count,
    array_agg(DISTINCT gn.label) as sample_concepts
FROM cortex.graph_nodes gn
LEFT JOIN cortex.graph_edges ge ON gn.node_id = ge.start_node_id OR gn.node_id = ge.end_node_id
CROSS JOIN LATERAL jsonb_to_recordset(gn.properties) as g(domain TEXT)
GROUP BY g.domain;

-- Add helpful comments
COMMENT ON VIEW cortex.curriculum_graph_stats IS 'Statistics about the KDA curriculum knowledge graph by domain';

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Run these to verify the graph was created successfully:

-- Check node count by domain:
-- SELECT * FROM cortex.curriculum_graph_stats;

-- Count all nodes:
-- SELECT COUNT(*) FROM cortex.graph_nodes WHERE graph_name = 'kda_curriculum';

-- Count all edges:
-- SELECT COUNT(*) FROM cortex.graph_edges WHERE graph_name = 'kda_curriculum';

-- View photosynthesis context:
-- SELECT * FROM cortex.get_concept_context('Photosynthesis');

-- View relationships for a concept:
-- SELECT
--     start.label as from_concept,
--     e.edge_label as relationship,
--     end.label as to_concept
-- FROM cortex.graph_edges e
-- JOIN cortex.graph_nodes start ON e.start_node_id = start.node_id
-- JOIN cortex.graph_nodes end ON e.end_node_id = end.node_id
-- WHERE start.label = 'Photosynthesis' OR end.label = 'Photosynthesis';

-- ============================================================================
-- END OF SEED SCRIPT
-- ============================================================================
