#!/usr/bin/env python3
"""
Database setup script for the Hyperliquid Trading Bot Suite.
This script creates the database tables and indexes.
"""

import os
import sys
from pathlib import Path

# Add the backend src directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from src.database import DatabaseManager, DatabaseConfig
from src.database.models import Base, create_additional_indexes


def main():
    """Set up database tables and indexes."""
    print("🔧 Setting up Hyperliquid Trading Bot database...")
    
    # Create database manager
    config = DatabaseConfig()
    db_manager = DatabaseManager(config)
    
    print(f"📡 Connecting to database: {config.host}:{config.port}/{config.database}")
    
    # Test connection
    if not db_manager.check_connection():
        print("❌ Failed to connect to database. Please check your configuration.")
        print(f"   Database URL: {config.database_url}")
        return 1
    
    print("✅ Database connection successful")
    
    # Create tables
    try:
        print("📋 Creating database tables...")
        db_manager.create_tables(drop_existing=False)
        print("✅ Database tables created successfully")
        
        print("🔍 Creating additional indexes...")
        create_additional_indexes(db_manager.engine)
        print("✅ Additional indexes created successfully")
        
        print("\n🎉 Database setup complete!")
        print("\nTables created:")
        print("  📊 strategy_rules       - Store trading strategy rules")
        print("  📈 trade_records       - Store trade execution records")
        print("  🧠 learning_entries    - Store AI learning insights")
        print("  📉 candle_data         - Store price/volume data")
        print("  🧪 backtest_configs    - Store backtest configurations")
        print("  📝 backtest_results    - Store backtest results")
        print("  ⚙️  ingestion_tasks     - Store content ingestion tasks")
        
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        return 1
    
    return 0


def reset_database():
    """Drop and recreate all database tables."""
    print("🔥 Resetting Hyperliquid Trading Bot database...")
    print("⚠️  This will DELETE ALL DATA!")
    
    response = input("Are you sure? Type 'yes' to continue: ")
    if response.lower() != 'yes':
        print("❌ Database reset cancelled")
        return 1
    
    # Create database manager
    config = DatabaseConfig()
    db_manager = DatabaseManager(config)
    
    try:
        print("🗑️  Dropping existing tables...")
        db_manager.drop_tables()
        print("✅ Tables dropped successfully")
        
        print("📋 Creating new tables...")
        db_manager.create_tables(drop_existing=False)
        print("✅ Tables created successfully")
        
        print("🔍 Creating indexes...")
        create_additional_indexes(db_manager.engine)
        print("✅ Indexes created successfully")
        
        print("\n🎉 Database reset complete!")
        
    except Exception as e:
        print(f"❌ Error resetting database: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database setup script")
    parser.add_argument("--reset", action="store_true", 
                       help="Reset database (drop all tables and recreate)")
    
    args = parser.parse_args()
    
    if args.reset:
        sys.exit(reset_database())
    else:
        sys.exit(main())