#!/usr/bin/env python3
"""
Migration management script for the Hyperliquid Trading Bot Suite.
Provides an easy interface for managing database migrations with Alembic.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add the backend src directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from src.database import DatabaseConfig


def run_alembic_command(args: list[str], check_db: bool = True) -> int:
    """Run an Alembic command with proper environment setup."""
    
    if check_db:
        # Check database connection
        config = DatabaseConfig()
        print(f"🔗 Using database: {config.host}:{config.port}/{config.database}")
        
        # Test connection
        from src.database import check_connection
        if not check_connection():
            print("❌ Cannot connect to database. Please check your configuration.")
            print(f"   Database URL: {config.database_url}")
            return 1
    
    # Set up environment
    env = os.environ.copy()
    env['PYTHONPATH'] = str(backend_dir)
    
    # Run alembic command
    cmd = ['alembic'] + args
    print(f"🚀 Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=backend_dir,
            env=env,
            check=True
        )
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}")
        return e.returncode
    except FileNotFoundError:
        print("❌ Alembic not found. Make sure it's installed in your virtual environment.")
        return 1


def current():
    """Show current database revision."""
    print("📍 Checking current database revision...")
    return run_alembic_command(['current'])


def history():
    """Show migration history."""
    print("📚 Showing migration history...")
    return run_alembic_command(['history'])


def upgrade(revision: str = 'head'):
    """Upgrade database to a specific revision."""
    print(f"⬆️  Upgrading database to revision: {revision}")
    return run_alembic_command(['upgrade', revision])


def downgrade(revision: str):
    """Downgrade database to a specific revision."""
    print(f"⬇️  Downgrading database to revision: {revision}")
    return run_alembic_command(['downgrade', revision])


def stamp(revision: str):
    """Stamp database with a specific revision without running migrations."""
    print(f"🏷️  Stamping database with revision: {revision}")
    return run_alembic_command(['stamp', revision])


def generate_migration(message: str):
    """Generate a new migration file."""
    print(f"📝 Generating new migration: {message}")
    return run_alembic_command(['revision', '--autogenerate', '-m', message])


def create_migration(message: str):
    """Create a new empty migration file."""
    print(f"📄 Creating empty migration: {message}")
    return run_alembic_command(['revision', '-m', message], check_db=False)


def sql_upgrade(revision: str = 'head'):
    """Generate SQL for upgrade without executing."""
    print(f"📜 Generating SQL for upgrade to: {revision}")
    return run_alembic_command(['upgrade', '--sql', revision], check_db=False)


def init_database():
    """Initialize database with the current schema (stamps as head without running migrations)."""
    print("🏗️  Initializing database with current schema...")
    
    # First, create tables using SQLAlchemy
    from src.database import create_tables, check_connection
    
    if not check_connection():
        print("❌ Cannot connect to database")
        return 1
    
    try:
        create_tables()
        print("✅ Tables created successfully")
        
        # Then stamp the database as head
        print("🏷️  Marking database as up-to-date...")
        return stamp('head')
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return 1


def main():
    """Main CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migration management for Hyperliquid Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s current              Show current revision
  %(prog)s upgrade              Upgrade to latest revision
  %(prog)s upgrade +1           Upgrade by one revision
  %(prog)s downgrade -1         Downgrade by one revision
  %(prog)s generate "add user table"  Generate new migration
  %(prog)s init                 Initialize fresh database
  %(prog)s history              Show migration history
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Current command
    subparsers.add_parser('current', help='Show current database revision')
    
    # History command
    subparsers.add_parser('history', help='Show migration history')
    
    # Upgrade command
    upgrade_parser = subparsers.add_parser('upgrade', help='Upgrade database')
    upgrade_parser.add_argument('revision', nargs='?', default='head',
                               help='Target revision (default: head)')
    
    # Downgrade command
    downgrade_parser = subparsers.add_parser('downgrade', help='Downgrade database')
    downgrade_parser.add_argument('revision', help='Target revision')
    
    # Stamp command
    stamp_parser = subparsers.add_parser('stamp', help='Stamp database with revision')
    stamp_parser.add_argument('revision', help='Revision to stamp')
    
    # Generate migration command
    generate_parser = subparsers.add_parser('generate', help='Generate new migration')
    generate_parser.add_argument('message', help='Migration message')
    
    # Create migration command
    create_parser = subparsers.add_parser('create', help='Create empty migration')
    create_parser.add_argument('message', help='Migration message')
    
    # SQL upgrade command
    sql_parser = subparsers.add_parser('sql', help='Generate SQL without executing')
    sql_parser.add_argument('revision', nargs='?', default='head',
                           help='Target revision (default: head)')
    
    # Init command
    subparsers.add_parser('init', help='Initialize database with current schema')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    if args.command == 'current':
        return current()
    elif args.command == 'history':
        return history()
    elif args.command == 'upgrade':
        return upgrade(args.revision)
    elif args.command == 'downgrade':
        return downgrade(args.revision)
    elif args.command == 'stamp':
        return stamp(args.revision)
    elif args.command == 'generate':
        return generate_migration(args.message)
    elif args.command == 'create':
        return create_migration(args.message)
    elif args.command == 'sql':
        return sql_upgrade(args.revision)
    elif args.command == 'init':
        return init_database()
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())