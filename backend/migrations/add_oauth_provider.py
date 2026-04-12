"""
Migration: Add oauth_provider column to users table
Preserves all existing user data (stripe_customer_id, api_key_encrypted, credits, etc.)
"""

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.database import db

"""
Deprecated migration: oauth_provider removal.

This project has fully removed OAuth support. This migration used to
add an `oauth_provider` column to the users table but OAuth has been
removed and this script is intentionally a no-op to avoid reintroducing
OAuth schema changes.

If you need to remove the `oauth_provider` column from an existing
SQLite database, perform a manual migration (create new table, copy
columns, drop old table, rename). This repository intentionally avoids
automating destructive schema changes.
"""

def main():
    print("oauth_provider migration intentionally disabled — no action taken")

if __name__ == '__main__':
    main()

if __name__ == "__main__":
    try:
        migrate()
        print("\n✅ Migration successful!")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
