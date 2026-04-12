"""
Migration: Add rate_limits table for BYOK rate limiting
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.database import db

def migrate():
    """Create rate_limits table."""
    print("Creating rate_limits table...")
    
    with db() as conn:
        cursor = conn.cursor()
        
        # Check if table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rate_limits'")
        if cursor.fetchone():
            print("✓ rate_limits table already exists, skipping")
            return
        
        cursor.execute("""
            CREATE TABLE rate_limits (
                user_id TEXT PRIMARY KEY,
                window_start INTEGER NOT NULL,
                request_count INTEGER DEFAULT 0,
                reset_at INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)
        
        cursor.execute("CREATE INDEX idx_rate_limits_reset ON rate_limits(reset_at)")
        
        conn.commit()
        print("✓ rate_limits table created")
        print("  - Tracks request counts per user per hour")
        print("  - BYOK users: 500 req/hour")
        print("  - Regular users: 50 req/hour")

if __name__ == "__main__":
    try:
        migrate()
        print("\n✅ Migration successful!")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
