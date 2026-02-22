"""Pytest configuration."""

import pytest


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "api: tests that require API keys")
    config.addinivalue_line("markers", "local: tests that use local models")
    config.addinivalue_line(
        "markers", "youtube: tests that require YouTube credentials"
    )
