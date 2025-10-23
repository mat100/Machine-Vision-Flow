"""
Pytest configuration for API integration tests
"""

import pytest
from fastapi.testclient import TestClient
from contextlib import asynccontextmanager


@pytest.fixture(scope="function")
def client():
    """
    Create a test client with properly initialized app state.
    Each test gets a fresh client to avoid state contamination.
    """
    from main import app
    from core.image_manager import ImageManager
    from core.camera_manager import CameraManager
    from core.template_manager import TemplateManager
    from core.history_buffer import HistoryBuffer
    import tempfile
    import shutil

    # Create temporary template directory
    temp_dir = tempfile.mkdtemp()

    # Initialize managers (lightweight for testing)
    image_manager = ImageManager(max_size_mb=100, max_images=10)
    camera_manager = CameraManager()
    template_manager = TemplateManager(temp_dir)
    history_buffer = HistoryBuffer(max_size=100)

    # Set in app state
    app.state.image_manager = image_manager
    app.state.camera_manager = camera_manager
    app.state.template_manager = template_manager
    app.state.history_buffer = history_buffer

    # Create test client (no context manager to avoid blocking)
    test_client = TestClient(app, raise_server_exceptions=False)

    yield test_client

    # Quick cleanup (don't wait for async)
    try:
        image_manager.cleanup()
        shutil.rmtree(temp_dir, ignore_errors=True)
    except:
        pass


@pytest.fixture(autouse=True)
def clear_history_before_test(client):
    """Clear history before each test to avoid interference"""
    try:
        client.post("/api/history/clear")
    except:
        pass  # Ignore errors if endpoint doesn't exist or fails

    yield
