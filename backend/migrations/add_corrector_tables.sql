-- Corrector Layer Tables
-- Run with: sqlite3 database.db < backend/migrations/add_corrector_tables.sql

-- Hallucination and error reports from users
CREATE TABLE IF NOT EXISTS hallucination_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    issue_type TEXT NOT NULL, -- 'hallucination', 'incorrect_code', 'wrong_file', 'vague', 'other'
    description TEXT NOT NULL,
    code_snippet TEXT,
    reported_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending', -- 'pending', 'confirmed', 'fixed', 'dismissed'
    admin_notes TEXT,
    FOREIGN KEY (reported_by) REFERENCES users(id)
);

-- Trusted sources for different technologies
CREATE TABLE IF NOT EXISTS trusted_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    technology TEXT NOT NULL, -- 'python', 'javascript', 'react', etc
    source_url TEXT NOT NULL,
    source_type TEXT, -- 'official_docs', 'github', 'tutorial', 'reference'
    reliability_score REAL DEFAULT 1.0,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(technology, source_url)
);

-- Cache of corrections to prevent repeat hallucinations
CREATE TABLE IF NOT EXISTS correction_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_hash TEXT NOT NULL UNIQUE,
    original_response TEXT NOT NULL,
    corrected_response TEXT NOT NULL,
    correction_type TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    use_count INTEGER DEFAULT 0
);

-- Message verification metadata
CREATE TABLE IF NOT EXISTS message_verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    confidence_score REAL NOT NULL,
    has_hallucination BOOLEAN DEFAULT 0,
    issues_detected TEXT, -- JSON array
    sources_used TEXT, -- JSON array
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id)
);

-- Insert default trusted sources
INSERT OR IGNORE INTO trusted_sources (technology, source_url, source_type, reliability_score) VALUES
('python', 'https://docs.python.org/3/', 'official_docs', 1.0),
('python', 'https://peps.python.org/', 'official_docs', 1.0),
('python', 'https://realpython.com/', 'tutorial', 0.9),
('javascript', 'https://developer.mozilla.org/', 'official_docs', 1.0),
('javascript', 'https://javascript.info/', 'tutorial', 0.95),
('typescript', 'https://www.typescriptlang.org/docs/', 'official_docs', 1.0),
('react', 'https://react.dev/', 'official_docs', 1.0),
('react', 'https://github.com/facebook/react', 'github', 0.95),
('fastapi', 'https://fastapi.tiangolo.com/', 'official_docs', 1.0),
('fastapi', 'https://github.com/tiangolo/fastapi', 'github', 0.95),
('nodejs', 'https://nodejs.org/docs/', 'official_docs', 1.0),
('express', 'https://expressjs.com/', 'official_docs', 1.0),
('vue', 'https://vuejs.org/', 'official_docs', 1.0),
('tailwindcss', 'https://tailwindcss.com/docs', 'official_docs', 1.0),
('sqlite', 'https://www.sqlite.org/docs.html', 'official_docs', 1.0),
('postgresql', 'https://www.postgresql.org/docs/', 'official_docs', 1.0);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_hallucination_reports_message ON hallucination_reports(message_id);
CREATE INDEX IF NOT EXISTS idx_hallucination_reports_user ON hallucination_reports(reported_by);
CREATE INDEX IF NOT EXISTS idx_hallucination_reports_status ON hallucination_reports(status);
CREATE INDEX IF NOT EXISTS idx_trusted_sources_tech ON trusted_sources(technology);
CREATE INDEX IF NOT EXISTS idx_correction_cache_hash ON correction_cache(query_hash);
CREATE INDEX IF NOT EXISTS idx_message_verifications_message ON message_verifications(message_id);
