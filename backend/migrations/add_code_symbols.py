"""
Migration: Add code_symbols table for intelligent code indexing
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.database import db

def migrate():
    """Create code_symbols table for project-wide symbol indexing."""
    print("Creating code_symbols table...")
    
    with db() as conn:
        cursor = conn.cursor()
        
        # Check if table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='code_symbols'")
        if cursor.fetchone():
            print("✓ code_symbols table already exists, skipping")
            return
        
        cursor.execute("""
            CREATE TABLE code_symbols (
                id TEXT PRIMARY KEY,
                file_upload_id TEXT NOT NULL,
                symbol_name TEXT NOT NULL,
                symbol_type TEXT NOT NULL,
                line_start INTEGER NOT NULL,
                line_end INTEGER NOT NULL,
                docstring TEXT,
                dependencies TEXT,
                called_by TEXT,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (file_upload_id) REFERENCES file_uploads(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("CREATE INDEX idx_code_symbols_file ON code_symbols(file_upload_id)")
        cursor.execute("CREATE INDEX idx_code_symbols_name ON code_symbols(symbol_name)")
        cursor.execute("CREATE INDEX idx_code_symbols_type ON code_symbols(symbol_type)")
        
        conn.commit()
        print("✓ code_symbols table created")
        print("  - Stores functions, classes, types, imports")
        print("  - Enables intelligent context building")
        print("  - Supports symbol search and jump-to-definition")

if __name__ == "__main__":
    try:
        migrate()
        print("\n✅ Migration successful!")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
