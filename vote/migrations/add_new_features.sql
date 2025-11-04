-- Migration script to add all new features
-- Run this to upgrade the database schema

-- Add new columns to competitions table
ALTER TABLE competitions 
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS image_url VARCHAR(500),
ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'active',
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS created_by INTEGER;

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_competitions_status ON competitions(status);
CREATE INDEX IF NOT EXISTS idx_competitions_archived ON competitions(is_archived);
CREATE INDEX IF NOT EXISTS idx_competitions_deleted ON competitions(deleted_at);
CREATE INDEX IF NOT EXISTS idx_competitions_tags ON competitions USING GIN(tags);

-- Add trigger to update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_competitions_updated_at ON competitions;
CREATE TRIGGER update_competitions_updated_at 
    BEFORE UPDATE ON competitions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Add users table if not exists (for created_by foreign key)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create default admin user if not exists (password: admin123)
INSERT INTO users (username, email, password_hash, is_admin)
VALUES ('admin', 'admin@voting.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5lW7HLqUVdkMm', TRUE)
ON CONFLICT (username) DO NOTHING;

-- Add foreign key constraint
ALTER TABLE competitions 
ADD CONSTRAINT fk_competitions_created_by 
FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;

-- Create competition history table for audit trail
CREATE TABLE IF NOT EXISTS competition_history (
    id SERIAL PRIMARY KEY,
    competition_id INTEGER NOT NULL,
    action VARCHAR(50) NOT NULL,
    changed_by INTEGER,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    old_data JSONB,
    new_data JSONB,
    FOREIGN KEY (competition_id) REFERENCES competitions(id) ON DELETE CASCADE,
    FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_competition_history_comp_id ON competition_history(competition_id);

COMMENT ON TABLE competitions IS 'Stores voting competitions with enhanced features';
COMMENT ON COLUMN competitions.description IS 'Detailed description of the competition';
COMMENT ON COLUMN competitions.tags IS 'Array of tags for organization and filtering';
COMMENT ON COLUMN competitions.image_url IS 'URL or path to competition image/icon';
COMMENT ON COLUMN competitions.status IS 'active, closed, scheduled';
COMMENT ON COLUMN competitions.updated_at IS 'Last modification timestamp';
COMMENT ON COLUMN competitions.deleted_at IS 'Soft delete timestamp';
COMMENT ON COLUMN competitions.is_archived IS 'Whether competition is archived';
COMMENT ON COLUMN competitions.archived_at IS 'When competition was archived';
