"""
Shared test fixtures and configuration.
"""

import pytest
from sqlalchemy import create_engine, Column, Text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.types import TypeDecorator
import json


# Custom ARRAY type for SQLite compatibility
class ArrayType(TypeDecorator):
    """JSON-based ARRAY type for SQLite testing."""
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return json.dumps(value)
    
    def process_result_value(self, value, dialect):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []


# Monkey-patch ARRAY before importing database models
from sqlalchemy.dialects import postgresql
original_array = postgresql.ARRAY
postgresql.ARRAY = lambda *args, **kwargs: ArrayType()

# Now import database models (they will use our ArrayType)
from src.database.models import Base


@pytest.fixture(scope="function")
def test_db_engine():
    """Create in-memory SQLite database for testing."""
    engine = create_engine('sqlite:///:memory:', echo=False)
    
    # Remove PostgreSQL-specific constraints for SQLite testing
    for table in Base.metadata.tables.values():
        constraints_to_remove = []
        for constraint in table.constraints:
            if hasattr(constraint, 'sqltext'):
                sqltext = str(constraint.sqltext)
                if 'ARRAY_LENGTH' in sqltext.upper():
                    constraints_to_remove.append(constraint)
        
        for constraint in constraints_to_remove:
            table.constraints.remove(constraint)
    
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def test_session(test_db_engine):
    """Create test database session."""
    Session = sessionmaker(bind=test_db_engine)
    session = Session()
    yield session
    session.close()
