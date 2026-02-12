"""Example repository demonstrating data access patterns."""

from typing import Any


class ExampleRepository:
    """Example repository for demonstrating data access patterns.
    
    Repositories handle data persistence and retrieval.
    They abstract away the storage mechanism (database, file, API, etc.).
    """

    def __init__(self):
        """Initialize the repository."""
        # In a real implementation, this would receive a database connection
        # or other storage mechanism
        self._storage: dict[str, Any] = {}

    async def get(self, key: str) -> Any | None:
        """Retrieve data by key.
        
        Args:
            key: The key to look up
            
        Returns:
            The stored data or None if not found
        """
        return self._storage.get(key)

    async def save(self, key: str, value: Any) -> None:
        """Save data with a key.
        
        Args:
            key: The key to store under
            value: The value to store
        """
        self._storage[key] = value

    async def delete(self, key: str) -> bool:
        """Delete data by key.
        
        Args:
            key: The key to delete
            
        Returns:
            True if the key existed, False otherwise
        """
        if key in self._storage:
            del self._storage[key]
            return True
        return False

    async def list_all(self) -> list[str]:
        """List all keys.
        
        Returns:
            List of all stored keys
        """
        return list(self._storage.keys())
