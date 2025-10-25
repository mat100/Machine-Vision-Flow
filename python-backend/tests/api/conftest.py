"""
Pytest configuration for API integration tests
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="function")
def client():
    """
    Create a test client with properly initialized app state.
    Each test gets a fresh client to avoid state contamination.
    """
    import shutil
    import tempfile

    from core.camera_manager import CameraManager
    from core.history_buffer import HistoryBuffer
    from core.image_manager import ImageManager
    from core.template_manager import TemplateManager
    from main import app

    # Create temporary template directory
    temp_dir = tempfile.mkdtemp()

    # Initialize managers (lightweight for testing)
    image_manager = ImageManager(max_size_mb=100, max_images=10)
    camera_manager = CameraManager()
    template_manager = TemplateManager(temp_dir)
    history_buffer = HistoryBuffer(max_size=100)

    # Create test config
    test_config = {
        "debug": {
            "save_debug_images": False,
            "show_overlays": False,
        }
    }

    # Set in app state
    app.state.image_manager = image_manager
    app.state.camera_manager = camera_manager
    app.state.template_manager = template_manager
    app.state.history_buffer = history_buffer
    app.state.config = test_config

    # Create test client (no context manager to avoid blocking)
    test_client = TestClient(app, raise_server_exceptions=False)

    yield test_client

    # Quick cleanup (don't wait for async)
    try:
        image_manager.cleanup()
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:  # noqa: E722
        pass


@pytest.fixture(autouse=True)
def clear_history_before_test(client):
    """Clear history before each test to avoid interference"""
    try:
        client.post("/api/history/clear")
    except Exception:  # noqa: E722
        pass  # Ignore errors if endpoint doesn't exist or fails

    yield
