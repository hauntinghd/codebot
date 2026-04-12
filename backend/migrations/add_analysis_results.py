"""
Migration: Add analysis_results table for caching code analysis
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.database import db

def migrate():
    """Create analysis_results table."""
    print("Creating analysis_results table...")
    
    with db() as conn:
        cursor = conn.cursor()
        
        # Check if table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analysis_results'")
        if cursor.fetchone():
            print("✓ analysis_results table already exists, skipping")
            return
        
        cursor.execute("""
            CREATE TABLE analysis_results (
                code_hash TEXT PRIMARY KEY,
                metrics TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)
        
        cursor.execute("CREATE INDEX idx_analysis_created ON analysis_results(created_at)")
        
        conn.commit()
        print("✓ analysis_results table created")
        print("  - Caches code analysis results")
        print("  - Reduces redundant analysis")
        print("  - 1 hour cache TTL")

if __name__ == "__main__":
    try:
        migrate()
        print("\n✅ Migration successful!")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
