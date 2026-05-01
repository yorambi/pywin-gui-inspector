from __future__ import annotations

import time


class TTLCache:
    """Simple time-to-live dict cache.

    Stores arbitrary key-value pairs along with insertion timestamps.
    Entries are considered stale and are ignored once their age exceeds
    the configured TTL.

    Attributes:
        ttl: Maximum age in seconds before a cached entry is considered
            expired.
    """

    def __init__(self, ttl: float = 2.0) -> None:
        """Initializes the cache with the given time-to-live duration.

        Args:
            ttl: Number of seconds an entry remains valid after insertion.
                Defaults to 2.0.
        """
        self._store: dict = {}
        self.ttl = ttl

    def get(self, key):
        """Retrieves a cached value if it exists and has not expired.

        Args:
            key: The cache key to look up.

        Returns:
            A two-tuple ``(value, True)`` when a non-expired entry is found,
            or ``(None, False)`` when the key is absent or its entry has
            exceeded the TTL.
        """
        if key in self._store:
            val, ts = self._store[key]
            if time.time() - ts < self.ttl:
                return val, True
        return None, False

    def set(self, key, val) -> None:
        """Inserts or replaces an entry in the cache with the current timestamp.

        Args:
            key: The cache key under which *val* will be stored.
            val: The value to cache.
        """
        self._store[key] = (val, time.time())

    def clear(self) -> None:
        """Removes all entries from the cache."""
        self._store.clear()