-- Sample textbook content about photosynthesis
INSERT INTO cortex.textbook_chunks (chapter_id, section_id, content, grade_level, subject, metadata) VALUES
('photosynthesis-101', 'intro', 'Photosynthesis is the process by which plants convert light energy from the sun into chemical energy stored in glucose. This fundamental biological process is essential for life on Earth, as it produces oxygen and forms the base of most food chains.', 8, 'biology', '{"topic": "photosynthesis", "keywords": ["energy", "glucose", "oxygen"]}'::jsonb),
('photosynthesis-101', 'chloroplasts', 'Chloroplasts are the organelles in plant cells where photosynthesis takes place. They contain chlorophyll, a green pigment that captures light energy from the sun.', 8, 'biology', '{"topic": "chloroplasts", "keywords": ["organelle", "chlorophyll"]}'::jsonb),
('photosynthesis-101', 'light-reactions', 'The light-dependent reactions of photosynthesis occur in the thylakoid membranes of chloroplasts. During these reactions, light energy is converted into ATP and NADPH, which are energy carriers used in the next stage.', 9, 'biology', '{"topic": "light reactions", "keywords": ["ATP", "NADPH", "thylakoid"]}'::jsonb),
('photosynthesis-101', 'calvin-cycle', 'The Calvin cycle is the light-independent phase of photosynthesis. It uses ATP and NADPH from the light reactions to convert carbon dioxide into glucose. This cycle is also called the dark reactions or the Calvin-Benson cycle.', 9, 'biology', '{"topic": "calvin cycle", "keywords": ["CO2", "glucose", "ATP", "NADPH"]}'::jsonb);

-- Verify insert
SELECT chapter_id, section_id, LEFT(content, 50) as content_preview FROM cortex.textbook_chunks;
