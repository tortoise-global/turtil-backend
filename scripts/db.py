#!/usr/bin/env python3
"""Database management script for Turtil Backend.

This script provides functions to create and delete database tables and ENUM types.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy import text
from app.db.database import engine
from app.models.cms.models import Base


def load_environment():
    """Load environment variables from .env file."""
    load_dotenv()
    print("✅ Environment variables loaded")


def create_enums():
    """Create all PostgreSQL ENUM types required by the application."""
    enums = [
        ("cms_user_role", ["principal", "admin", "head", "staff"]),
        ("cms_access_scope", ["self", "department", "branch", "college", "system"]),
        ("student_user_role", ["student"]),
        ("timetable_day", ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"])
    ]
    
    with engine.connect() as conn:
        for enum_name, enum_values in enums:
            try:
                values_str = "', '".join(enum_values)
                query = f"CREATE TYPE {enum_name} AS ENUM ('{values_str}')"
                conn.execute(text(query))
                conn.commit()
                print(f"✅ Created ENUM type: {enum_name}")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"ℹ️  ENUM type {enum_name} already exists")
                else:
                    print(f"❌ Error creating ENUM {enum_name}: {e}")


def drop_enums():
    """Drop all PostgreSQL ENUM types."""
    enums = ["cms_user_role", "cms_access_scope", "student_user_role", "timetable_day"]
    
    with engine.connect() as conn:
        for enum_name in enums:
            try:
                conn.execute(text(f"DROP TYPE IF EXISTS {enum_name} CASCADE"))
                conn.commit()
                print(f"✅ Dropped ENUM type: {enum_name}")
            except Exception as e:
                print(f"❌ Error dropping ENUM {enum_name}: {e}")


def create_tables():
    """Create all database tables."""
    try:
        # First create ENUMs if using PostgreSQL
        database_url = os.getenv("DATABASE_URL", "")
        if database_url.startswith("postgresql"):
            print("📝 Creating PostgreSQL ENUM types...")
            create_enums()
        
        print("📝 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ All database tables created successfully")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)


def drop_tables():
    """Drop all database tables."""
    try:
        print("🗑️  Dropping all database tables...")
        Base.metadata.drop_all(bind=engine)
        print("✅ All database tables deleted successfully")
        
        # Drop ENUMs if using PostgreSQL
        database_url = os.getenv("DATABASE_URL", "")
        if database_url.startswith("postgresql"):
            print("🗑️  Dropping PostgreSQL ENUM types...")
            drop_enums()
            
    except Exception as e:
        print(f"❌ Error dropping tables: {e}")
        sys.exit(1)


def reset_database():
    """Drop and recreate all database tables."""
    print("🔄 Resetting database...")
    drop_tables()
    create_tables()
    print("✅ Database reset completed")


def show_help():
    """Show help message."""
    help_text = """
Database Management Script for Turtil Backend

Usage: python scripts/db.py [command]

Commands:
  create    Create all database tables and ENUM types
  delete    Delete all database tables and ENUM types  
  reset     Delete and recreate all database tables
  help      Show this help message

Examples:
  python scripts/db.py create
  python scripts/db.py delete
  python scripts/db.py reset
"""
    print(help_text)


def main():
    """Main function to handle command line arguments."""
    load_environment()
    
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "create":
        create_tables()
    elif command == "delete":
        drop_tables()
    elif command == "reset":
        reset_database()
    elif command == "help":
        show_help()
    else:
        print(f"❌ Unknown command: {command}")
        show_help()
        sys.exit(1)


if __name__ == "__main__":
    main()