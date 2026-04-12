"""Database schema for multi-media and Stripe integration.

Run this once to create new tables for:
- file_uploads: Store multimedia file metadata
- user_subscriptions: Track Stripe subscriptions
- billing_events: Audit trail for payment events
"""

import sqlite3
from pathlib import Path

def migrate_multimedia_schema(db_path: str):
    """Create multimedia and billing tables."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        # File uploads table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_uploads (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL,  -- images, video, audio, code, archive
                file_size INTEGER,         -- bytes
                file_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_uploads_user_id 
            ON file_uploads(user_id)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_uploads_type 
            ON file_uploads(user_id, file_type)
        """)
        
        # User subscriptions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                plan_key TEXT NOT NULL,  -- pioneer, voyager
                status TEXT NOT NULL,     -- active, past_due, canceled
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT UNIQUE,
                current_period_start INTEGER,
                current_period_end INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id 
            ON user_subscriptions(user_id)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_subscriptions_status 
            ON user_subscriptions(user_id, status)
        """)
        
        # Billing events table (audit trail)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS billing_events (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                event_type TEXT NOT NULL,  -- payment_succeeded, payment_failed, subscription_updated
                stripe_id TEXT,
                metadata TEXT,              -- JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_billing_events_user_id 
            ON billing_events(user_id, created_at)
        """)
        
        conn.commit()
        print("✓ Multimedia and billing tables created successfully")
        return True
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    import os
    db_path = Path(os.environ.get("DB_PATH", "./data/codebot.db"))
    success = migrate_multimedia_schema(str(db_path))
    exit(0 if success else 1)
