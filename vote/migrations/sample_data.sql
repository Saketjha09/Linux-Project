-- Sample data for demonstrating all 10 new features
-- Run this to populate your database with test competitions

-- Insert competitions with all new features
INSERT INTO competitions (name, description, option_a, option_b, tags, image_url, status, created_by) VALUES
(
  'Best Programming Language 2025',
  'Vote for the most popular programming language in 2025. Python offers simplicity and versatility, while JavaScript dominates web development.',
  'Python',
  'JavaScript',
  ARRAY['technology', 'programming', 'coding'],
  'https://picsum.photos/seed/prog/200',
  'active',
  1
),
(
  'Favorite NBA Team',
  'Which basketball team has the most dedicated fanbase? Lakers with their historic legacy or Warriors with their modern dynasty?',
  'Lakers',
  'Warriors',
  ARRAY['sports', 'basketball', 'NBA'],
  'https://picsum.photos/seed/nba/200',
  'active',
  1
),
(
  'Best Marvel Superhero',
  'The ultimate showdown! Iron Man with his technology and genius, or Captain America with his leadership and valor?',
  'Iron Man',
  'Captain America',
  ARRAY['entertainment', 'movies', 'marvel'],
  'https://picsum.photos/seed/marvel/200',
  'active',
  1
),
(
  'Favorite Coffee Type',
  'Coffee lovers unite! Do you prefer the smooth, rich taste of a Latte or the bold intensity of an Espresso?',
  'Latte',
  'Espresso',
  ARRAY['food', 'drinks', 'coffee'],
  'https://picsum.photos/seed/coffee/200',
  'active',
  1
),
(
  'Best Operating System',
  'For developers and power users: Windows with its compatibility, or Linux with its customization and open-source nature?',
  'Windows',
  'Linux',
  ARRAY['technology', 'software', 'OS'],
  'https://picsum.photos/seed/os/200',
  'closed',
  1
);

-- Add some votes to show percentages
-- Competition 1: Python vs JavaScript (75% vs 25%)
INSERT INTO votes (competition_id, vote, created_at) VALUES
(1, 'a', NOW() - INTERVAL '1 hour'),
(1, 'a', NOW() - INTERVAL '2 hours'),
(1, 'a', NOW() - INTERVAL '3 hours'),
(1, 'a', NOW() - INTERVAL '4 hours'),
(1, 'a', NOW() - INTERVAL '5 hours'),
(1, 'a', NOW() - INTERVAL '6 hours'),
(1, 'a', NOW() - INTERVAL '7 hours'),
(1, 'a', NOW() - INTERVAL '8 hours'),
(1, 'a', NOW() - INTERVAL '9 hours'),
(1, 'a', NOW() - INTERVAL '10 hours'),
(1, 'a', NOW() - INTERVAL '11 hours'),
(1, 'a', NOW() - INTERVAL '12 hours'),
(1, 'a', NOW() - INTERVAL '13 hours'),
(1, 'a', NOW() - INTERVAL '14 hours'),
(1, 'a', NOW() - INTERVAL '15 hours'),
(1, 'b', NOW() - INTERVAL '16 hours'),
(1, 'b', NOW() - INTERVAL '17 hours'),
(1, 'b', NOW() - INTERVAL '18 hours'),
(1, 'b', NOW() - INTERVAL '19 hours'),
(1, 'b', NOW() - INTERVAL '20 hours');

-- Competition 2: Lakers vs Warriors (40% vs 60%)
INSERT INTO votes (competition_id, vote, created_at) VALUES
(2, 'a', NOW() - INTERVAL '1 hour'),
(2, 'a', NOW() - INTERVAL '2 hours'),
(2, 'a', NOW() - INTERVAL '3 hours'),
(2, 'a', NOW() - INTERVAL '4 hours'),
(2, 'a', NOW() - INTERVAL '5 hours'),
(2, 'a', NOW() - INTERVAL '6 hours'),
(2, 'a', NOW() - INTERVAL '7 hours'),
(2, 'a', NOW() - INTERVAL '8 hours'),
(2, 'b', NOW() - INTERVAL '9 hours'),
(2, 'b', NOW() - INTERVAL '10 hours'),
(2, 'b', NOW() - INTERVAL '11 hours'),
(2, 'b', NOW() - INTERVAL '12 hours'),
(2, 'b', NOW() - INTERVAL '13 hours'),
(2, 'b', NOW() - INTERVAL '14 hours'),
(2, 'b', NOW() - INTERVAL '15 hours'),
(2, 'b', NOW() - INTERVAL '16 hours'),
(2, 'b', NOW() - INTERVAL '17 hours'),
(2, 'b', NOW() - INTERVAL '18 hours'),
(2, 'b', NOW() - INTERVAL '19 hours'),
(2, 'b', NOW() - INTERVAL '20 hours');

-- Competition 3: Iron Man vs Captain America (50% vs 50%)
INSERT INTO votes (competition_id, vote, created_at) VALUES
(3, 'a', NOW() - INTERVAL '1 hour'),
(3, 'a', NOW() - INTERVAL '2 hours'),
(3, 'a', NOW() - INTERVAL '3 hours'),
(3, 'a', NOW() - INTERVAL '4 hours'),
(3, 'a', NOW() - INTERVAL '5 hours'),
(3, 'a', NOW() - INTERVAL '6 hours'),
(3, 'a', NOW() - INTERVAL '7 hours'),
(3, 'a', NOW() - INTERVAL '8 hours'),
(3, 'a', NOW() - INTERVAL '9 hours'),
(3, 'a', NOW() - INTERVAL '10 hours'),
(3, 'b', NOW() - INTERVAL '11 hours'),
(3, 'b', NOW() - INTERVAL '12 hours'),
(3, 'b', NOW() - INTERVAL '13 hours'),
(3, 'b', NOW() - INTERVAL '14 hours'),
(3, 'b', NOW() - INTERVAL '15 hours'),
(3, 'b', NOW() - INTERVAL '16 hours'),
(3, 'b', NOW() - INTERVAL '17 hours'),
(3, 'b', NOW() - INTERVAL '18 hours'),
(3, 'b', NOW() - INTERVAL '19 hours'),
(3, 'b', NOW() - INTERVAL '20 hours');

-- Competition 4: Latte vs Espresso (65% vs 35%)
INSERT INTO votes (competition_id, vote, created_at) VALUES
(4, 'a', NOW() - INTERVAL '1 hour'),
(4, 'a', NOW() - INTERVAL '2 hours'),
(4, 'a', NOW() - INTERVAL '3 hours'),
(4, 'a', NOW() - INTERVAL '4 hours'),
(4, 'a', NOW() - INTERVAL '5 hours'),
(4, 'a', NOW() - INTERVAL '6 hours'),
(4, 'a', NOW() - INTERVAL '7 hours'),
(4, 'a', NOW() - INTERVAL '8 hours'),
(4, 'a', NOW() - INTERVAL '9 hours'),
(4, 'a', NOW() - INTERVAL '10 hours'),
(4, 'a', NOW() - INTERVAL '11 hours'),
(4, 'a', NOW() - INTERVAL '12 hours'),
(4, 'a', NOW() - INTERVAL '13 hours'),
(4, 'b', NOW() - INTERVAL '14 hours'),
(4, 'b', NOW() - INTERVAL '15 hours'),
(4, 'b', NOW() - INTERVAL '16 hours'),
(4, 'b', NOW() - INTERVAL '17 hours'),
(4, 'b', NOW() - INTERVAL '18 hours'),
(4, 'b', NOW() - INTERVAL '19 hours'),
(4, 'b', NOW() - INTERVAL '20 hours');

-- Competition 5: Windows vs Linux (30% vs 70%)
INSERT INTO votes (competition_id, vote, created_at) VALUES
(5, 'a', NOW() - INTERVAL '1 hour'),
(5, 'a', NOW() - INTERVAL '2 hours'),
(5, 'a', NOW() - INTERVAL '3 hours'),
(5, 'a', NOW() - INTERVAL '4 hours'),
(5, 'a', NOW() - INTERVAL '5 hours'),
(5, 'a', NOW() - INTERVAL '6 hours'),
(5, 'b', NOW() - INTERVAL '7 hours'),
(5, 'b', NOW() - INTERVAL '8 hours'),
(5, 'b', NOW() - INTERVAL '9 hours'),
(5, 'b', NOW() - INTERVAL '10 hours'),
(5, 'b', NOW() - INTERVAL '11 hours'),
(5, 'b', NOW() - INTERVAL '12 hours'),
(5, 'b', NOW() - INTERVAL '13 hours'),
(5, 'b', NOW() - INTERVAL '14 hours'),
(5, 'b', NOW() - INTERVAL '15 hours'),
(5, 'b', NOW() - INTERVAL '16 hours'),
(5, 'b', NOW() - INTERVAL '17 hours'),
(5, 'b', NOW() - INTERVAL '18 hours'),
(5, 'b', NOW() - INTERVAL '19 hours'),
(5, 'b', NOW() - INTERVAL '20 hours');

-- Summary
SELECT 'Sample data inserted successfully!' AS message;
SELECT COUNT(*) AS total_competitions FROM competitions;
SELECT COUNT(*) AS total_votes FROM votes;
