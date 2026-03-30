"""
Asset cache management.

This module provides caching functionality for downloaded assets
to avoid re-downloading the same files.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Optional


class AssetCache:
    """
    Cache for downloaded assets.

    Stores metadata about downloaded files and provides
    methods to check cache and add new entries.
    """

    def __init__(self, cache_dir: Path):
        """
        Initialize the asset cache.

        Args:
            cache_dir: Directory to store cached assets
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = cache_dir / "index.json"
        self.index = self._load_index()

    def _load_index(self) -> dict:
        """
        Load the cache index from disk.

        Returns:
            Dictionary mapping cache keys to metadata
        """
        if self.index_file.exists():
            try:
                with open(self.index_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_index(self) -> None:
        """Save the cache index to disk."""
        try:
            with open(self.index_file, "w") as f:
                json.dump(self.index, f, indent=2)
        except IOError:
            pass  # Fail silently

    def _hash_key(self, key: str) -> str:
        """
        Hash a key for cache storage.

        Args:
            key: The key to hash (e.g., URL)

        Returns:
            Hashed key (first 16 chars of SHA256)
        """
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def get(self, key: str) -> Optional[Path]:
        """
        Get a cached asset.

        Args:
            key: Cache key (e.g., URL)

        Returns:
            Path to cached asset if found, None otherwise
        """
        cache_key = self._hash_key(key)

        if cache_key in self.index:
            entry = self.index[cache_key]
            cached_path = self.cache_dir / entry["filename"]

            if cached_path.exists():
                return cached_path
            else:
                # Entry exists but file is missing, remove from index
                del self.index[cache_key]
                self._save_index()

        return None

    def put(self, key: str, local_path: Path, metadata: Optional[dict] = None) -> None:
        """
        Add an asset to the cache.

        Args:
            key: Cache key (e.g., URL)
            local_path: Path to the local file
            metadata: Optional metadata to store with the entry
        """
        cache_key = self._hash_key(key)

        entry = {
            "key": key,
            "filename": local_path.name,
            "timestamp": time.time(),
            "size": local_path.stat().st_size if local_path.exists() else 0
        }

        if metadata:
            entry["metadata"] = metadata

        self.index[cache_key] = entry
        self._save_index()

    def clear(self) -> None:
        """Clear all cache entries and delete cached files."""
        # Delete all cached files
        for entry in self.index.values():
            file_path = self.cache_dir / entry["filename"]
            if file_path.exists():
                try:
                    file_path.unlink()
                except OSError:
                    pass  # Fail silently

        # Clear index
        self.index = {}
        self._save_index()

    def get_size(self) -> int:
        """
        Get total cache size in bytes.

        Returns:
            Total size of all cached files
        """
        total = 0
        for entry in self.index.values():
            total += entry.get("size", 0)
        return total

    def get_count(self) -> int:
        """
        Get number of cached entries.

        Returns:
            Number of entries in cache
        """
        return len(self.index)

    def cleanup_old_entries(self, max_age_seconds: float) -> int:
        """
        Remove cache entries older than specified age.

        Args:
            max_age_seconds: Maximum age in seconds

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        to_remove = []

        for cache_key, entry in self.index.items():
            age = current_time - entry["timestamp"]
            if age > max_age_seconds:
                to_remove.append(cache_key)

        for cache_key in to_remove:
            entry = self.index[cache_key]
            file_path = self.cache_dir / entry["filename"]

            if file_path.exists():
                try:
                    file_path.unlink()
                except OSError:
                    pass

            del self.index[cache_key]

        if to_remove:
            self._save_index()

        return len(to_remove)

    def get_info(self) -> dict:
        """
        Get cache information.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "count": self.get_count(),
            "size_bytes": self.get_size(),
            "size_mb": self.get_size() / (1024 * 1024),
            "cache_dir": str(self.cache_dir)
        }
