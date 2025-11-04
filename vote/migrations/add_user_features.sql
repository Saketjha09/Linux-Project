-- Phase 1 & 2 Database Schema Additions for User Features

-- Table for user favorites/bookmarks
CREATE TABLE IF NOT EXISTS user_favorites (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    competition_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (competition_id) REFERENCES competitions(id) ON DELETE CASCADE,
    UNIQUE(user_id, competition_id)
);

CREATE INDEX IF NOT EXISTS idx_user_favorites_user ON user_favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_user_favorites_comp ON user_favorites(competition_id);

-- Table for comments
CREATE TABLE IF NOT EXISTS competition_comments (
    id SERIAL PRIMARY KEY,
    competition_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    comment_text TEXT NOT NULL,
    parent_id INTEGER,
    likes_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    FOREIGN KEY (competition_id) REFERENCES competitions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES competition_comments(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_comments_comp ON competition_comments(competition_id);
CREATE INDEX IF NOT EXISTS idx_comments_user ON competition_comments(user_id);
CREATE INDEX IF NOT EXISTS idx_comments_parent ON competition_comments(parent_id);

-- Table for comment likes
CREATE TABLE IF NOT EXISTS comment_likes (
    id SERIAL PRIMARY KEY,
    comment_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (comment_id) REFERENCES competition_comments(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(comment_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_comment_likes_comment ON comment_likes(comment_id);
CREATE INDEX IF NOT EXISTS idx_comment_likes_user ON comment_likes(user_id);

-- Add view history to track user's voting history
CREATE TABLE IF NOT EXISTS user_vote_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    competition_id INTEGER NOT NULL,
    vote_choice VARCHAR(10) NOT NULL,
    voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (competition_id) REFERENCES competitions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_vote_history_user ON user_vote_history(user_id);
CREATE INDEX IF NOT EXISTS idx_vote_history_comp ON user_vote_history(competition_id);

-- Add trending score column to competitions
ALTER TABLE competitions ADD COLUMN IF NOT EXISTS trending_score INTEGER DEFAULT 0;
ALTER TABLE competitions ADD COLUMN IF NOT EXISTS view_count INTEGER DEFAULT 0;
ALTER TABLE competitions ADD COLUMN IF NOT EXISTS participant_count INTEGER DEFAULT 0;

-- Trigger to update comment likes count
CREATE OR REPLACE FUNCTION update_comment_likes_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE competition_comments 
        SET likes_count = likes_count + 1 
        WHERE id = NEW.comment_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE competition_comments 
        SET likes_count = likes_count - 1 
        WHERE id = OLD.comment_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_comment_likes ON comment_likes;
CREATE TRIGGER update_comment_likes
    AFTER INSERT OR DELETE ON comment_likes
    FOR EACH ROW
    EXECUTE FUNCTION update_comment_likes_count();

-- Trigger to update participant count
CREATE OR REPLACE FUNCTION update_participant_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE competitions 
        SET participant_count = (
            SELECT COUNT(DISTINCT user_id) 
            FROM votes 
            WHERE competition_id = NEW.competition_id
        )
        WHERE id = NEW.competition_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_comp_participants ON votes;
CREATE TRIGGER update_comp_participants
    AFTER INSERT ON votes
    FOR EACH ROW
    EXECUTE FUNCTION update_participant_count();

-- Trigger to update trending score (based on recent activity)
CREATE OR REPLACE FUNCTION calculate_trending_score()
RETURNS void AS $$
BEGIN
    UPDATE competitions
    SET trending_score = (
        SELECT COUNT(*) 
        FROM votes 
        WHERE votes.competition_id = competitions.id 
        AND votes.created_at > NOW() - INTERVAL '24 hours'
    )
    WHERE deleted_at IS NULL AND is_archived = FALSE;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE user_favorites IS 'Stores user bookmarked/favorite competitions';
COMMENT ON TABLE competition_comments IS 'User comments on competitions with threading support';
COMMENT ON TABLE comment_likes IS 'Likes on comments';
COMMENT ON TABLE user_vote_history IS 'Historical record of all user votes';
COMMENT ON COLUMN competitions.trending_score IS 'Score based on votes in last 24 hours';
COMMENT ON COLUMN competitions.view_count IS 'Number of times competition was viewed';
COMMENT ON COLUMN competitions.participant_count IS 'Unique users who voted';

SELECT 'Phase 1 & 2 schema additions completed successfully!' AS status;
