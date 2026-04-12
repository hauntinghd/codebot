"""Architecture mode database migrations."""

CREATE_ARCHITECTURE_TABLES = """
-- Architecture projects table
CREATE TABLE IF NOT EXISTS architecture_projects (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    template TEXT DEFAULT 'blank',
    built INTEGER DEFAULT 0,
    status TEXT DEFAULT 'planning',
    preview_url TEXT,
    file_tree TEXT,
    created_at INTEGER DEFAULT (strftime('%s','now')),
    updated_at INTEGER DEFAULT (strftime('%s','now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_architecture_projects_user ON architecture_projects(user_id);

-- Architecture tasks table
CREATE TABLE IF NOT EXISTS architecture_tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    phase TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending',
    result TEXT,
    created_at INTEGER DEFAULT (strftime('%s','now')),
    updated_at INTEGER DEFAULT (strftime('%s','now')),
    FOREIGN KEY (project_id) REFERENCES architecture_projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_architecture_tasks_project ON architecture_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_architecture_tasks_phase ON architecture_tasks(phase);

-- Architecture preview servers table
CREATE TABLE IF NOT EXISTS architecture_previews (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL UNIQUE,
    status TEXT DEFAULT 'stopped',
    preview_url TEXT,
    ports TEXT,
    started_at INTEGER,
    stopped_at INTEGER,
    FOREIGN KEY (project_id) REFERENCES architecture_projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_architecture_previews_project ON architecture_previews(project_id);

-- Architecture planning messages table
CREATE TABLE IF NOT EXISTS architecture_messages (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at INTEGER DEFAULT (strftime('%s','now')),
    FOREIGN KEY (project_id) REFERENCES architecture_projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_architecture_messages_project ON architecture_messages(project_id);
"""


def apply_architecture_migrations(conn):
    """Apply architecture mode migrations."""
    conn.executescript(CREATE_ARCHITECTURE_TABLES)
    # Ensure `built` column exists for older databases
    cur = conn.execute("PRAGMA table_info(architecture_projects)").fetchall()
    cols = [c[1] for c in cur]
    if "built" not in cols:
        try:
            conn.execute("ALTER TABLE architecture_projects ADD COLUMN built INTEGER DEFAULT 0")
        except Exception:
            # If ALTER fails for any reason, continue; CREATE TABLE covers new installs
            pass
    conn.commit()
