"""
Pytest configuration and fixtures for Machine Vision Flow tests
"""

import pytest
import numpy as np
import cv2
from unittest.mock import Mock, MagicMock

from core.camera_manager import CameraManager
from core.image_manager import ImageManager
from core.template_manager import TemplateManager
from core.history_buffer import HistoryBuffer
from services.camera_service import CameraService
from services.image_service import ImageService
from services.vision_service import VisionService


@pytest.fixture
def test_image():
    """Create a test image for testing"""
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    # Add some content
    cv2.rectangle(image, (100, 100), (300, 300), (255, 255, 255), -1)
    cv2.circle(image, (450, 350), 50, (128, 128, 128), -1)
    return image


@pytest.fixture
def test_template():
    """Create a test template image"""
    template = np.zeros((50, 50, 3), dtype=np.uint8)
    cv2.rectangle(template, (10, 10), (40, 40), (255, 255, 255), -1)
    return template


@pytest.fixture
def image_manager():
    """Create ImageManager instance for testing"""
    manager = ImageManager(max_size_mb=100, max_images=10)
    yield manager
    # Cleanup
    manager.cleanup()


@pytest.fixture
def camera_manager():
    """Create CameraManager instance for testing"""
    manager = CameraManager()
    yield manager
    # Cleanup
    manager.cleanup()


@pytest.fixture
def template_manager(tmp_path):
    """Create TemplateManager instance with temporary directory"""
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    manager = TemplateManager(str(template_dir))
    yield manager
    # Cleanup happens automatically with tmp_path


@pytest.fixture
def history_buffer():
    """Create HistoryBuffer instance for testing"""
    return HistoryBuffer(max_size=100)


@pytest.fixture
def camera_service(camera_manager, image_manager):
    """Create CameraService instance for testing"""
    return CameraService(
        camera_manager=camera_manager,
        image_manager=image_manager
    )


@pytest.fixture
def image_service(image_manager):
    """Create ImageService instance for testing"""
    return ImageService(image_manager=image_manager)


@pytest.fixture
def vision_service(image_manager, template_manager, history_buffer):
    """Create VisionService instance for testing"""
    return VisionService(
        image_manager=image_manager,
        template_manager=template_manager,
        history_buffer=history_buffer
    )


@pytest.fixture
def mock_camera_manager():
    """Create mock CameraManager for unit testing"""
    mock = MagicMock()
    test_image = np.zeros((480, 640, 3), dtype=np.uint8)
    mock.list_available_cameras.return_value = [
        {'id': 'test', 'name': 'Test Camera', 'type': 'test'}
    ]
    mock.connect_camera.return_value = True
    mock.disconnect_camera.return_value = True
    mock.capture.return_value = test_image
    mock.get_preview.return_value = test_image
    mock.create_test_image.return_value = test_image
    return mock


@pytest.fixture
def mock_image_manager():
    """Create mock ImageManager for unit testing"""
    mock = MagicMock()
    test_image = np.zeros((480, 640, 3), dtype=np.uint8)
    mock.get.return_value = test_image
    mock.store.return_value = 'test-image-id'
    mock.create_thumbnail.return_value = (test_image, 'base64-thumbnail')
    mock.delete.return_value = True
    mock.has_image.return_value = True
    mock.list_images.return_value = []
    mock.get_metadata.return_value = {}
    return mock


@pytest.fixture
def mock_template_manager():
    """Create mock TemplateManager for unit testing"""
    mock = MagicMock()
    test_template = np.zeros((50, 50, 3), dtype=np.uint8)
    mock.get_template.return_value = test_template
    mock.list_templates.return_value = []
    mock.learn_template.return_value = 'new-template-id'
    mock.create_template_thumbnail.return_value = 'base64-template-thumb'
    return mock


@pytest.fixture
def mock_history_buffer():
    """Create mock HistoryBuffer for unit testing"""
    mock = MagicMock()
    mock.add_inspection.return_value = None
    mock.get_recent.return_value = []
    return mock
