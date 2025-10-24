"""
Constants and configuration values for Machine Vision Flow system.
Centralizes all magic numbers and configuration constants.
"""

from enum import Enum


# Image Management Constants
class ImageConstants:
    """Constants related to image storage and processing."""

    # Storage limits
    DEFAULT_MAX_IMAGES = 100
    DEFAULT_MAX_MEMORY_MB = 1000
    MIN_IMAGES = 1
    MAX_IMAGES = 1000

    # Image dimensions
    DEFAULT_IMAGE_WIDTH = 1920
    DEFAULT_IMAGE_HEIGHT = 1080
    MAX_IMAGE_DIMENSION = 4096
    MIN_IMAGE_DIMENSION = 10

    # Thumbnail settings
    DEFAULT_THUMBNAIL_WIDTH = 320
    MIN_THUMBNAIL_WIDTH = 50
    MAX_THUMBNAIL_WIDTH = 800
    THUMBNAIL_JPEG_QUALITY = 70

    # Memory management
    MEMORY_CLEANUP_THRESHOLD = 0.9  # Start cleanup at 90% memory usage
    LRU_EVICTION_BATCH_SIZE = 5  # Number of images to evict at once


# Camera Constants
class CameraConstants:
    """Constants related to camera operations."""

    # Camera types
    TEST_CAMERA_ID = "test"
    DEFAULT_CAMERA_ID = "test"

    # Capture settings
    DEFAULT_CAPTURE_TIMEOUT_MS = 5000
    MAX_CAPTURE_TIMEOUT_MS = 30000
    MIN_CAPTURE_TIMEOUT_MS = 100

    # USB camera enumeration
    MAX_USB_CAMERAS_TO_CHECK = 5
    USB_CAMERA_CHECK_TIMEOUT_MS = 1000

    # Stream settings
    MJPEG_FPS = 30
    MJPEG_QUALITY = 85
    STREAM_BUFFER_SIZE = 10
    MAX_CONCURRENT_STREAMS = 3

    # Test image generation
    TEST_IMAGE_WIDTH = 1920
    TEST_IMAGE_HEIGHT = 1080
    TEST_PATTERN_TYPES = ["checkerboard", "gradient", "noise", "solid"]


# Template Constants
class TemplateConstants:
    """Constants related to template matching."""

    # Storage
    DEFAULT_STORAGE_PATH = "templates"
    MAX_TEMPLATE_SIZE_MB = 10
    ALLOWED_FORMATS = [".png", ".jpg", ".jpeg"]

    # Matching parameters
    DEFAULT_THRESHOLD = 0.8
    MIN_THRESHOLD = 0.0
    MAX_THRESHOLD = 1.0

    DEFAULT_SCALE_MIN = 0.8
    DEFAULT_SCALE_MAX = 1.2
    SCALE_STEP = 0.05

    # Template limits
    MAX_TEMPLATES = 1000
    MIN_TEMPLATE_SIZE = 10  # pixels
    MAX_TEMPLATE_SIZE = 500  # pixels


# Vision Processing Constants
class VisionConstants:
    """Constants for computer vision operations."""

    # Edge detection
    class EdgeMethod(str, Enum):
        CANNY = "canny"
        SOBEL = "sobel"
        LAPLACIAN = "laplacian"
        SCHARR = "scharr"
        PREWITT = "prewitt"
        ROBERTS = "roberts"

    # Canny edge detection
    CANNY_LOW_THRESHOLD_DEFAULT = 50
    CANNY_HIGH_THRESHOLD_DEFAULT = 150
    CANNY_LOW_THRESHOLD_MIN = 0
    CANNY_LOW_THRESHOLD_MAX = 500
    CANNY_HIGH_THRESHOLD_MIN = 0
    CANNY_HIGH_THRESHOLD_MAX = 500

    # Morphological operations
    MORPH_KERNEL_SIZE_DEFAULT = 3
    MORPH_KERNEL_SIZE_MIN = 1
    MORPH_KERNEL_SIZE_MAX = 21

    # Contour detection
    MAX_CONTOURS_DEFAULT = 100
    MAX_CONTOURS_LIMIT = 1000
    MIN_CONTOUR_AREA_DEFAULT = 100
    MAX_CONTOUR_AREA_DEFAULT = 100000

    # Preprocessing
    GAUSSIAN_BLUR_SIZE_DEFAULT = 5
    GAUSSIAN_BLUR_SIZE_MIN = 1
    GAUSSIAN_BLUR_SIZE_MAX = 31
    BILATERAL_FILTER_D_DEFAULT = 9
    MEDIAN_BLUR_SIZE_DEFAULT = 5


# ROI Constants
class ROIConstants:
    """Constants for Region of Interest operations."""

    MIN_ROI_SIZE = 1
    MAX_ROI_SIZE = 4096
    DEFAULT_ROI_EXPAND_PIXELS = 10
    ROI_OVERLAP_THRESHOLD = 0.5


# History Buffer Constants
class HistoryConstants:
    """Constants for history buffer."""

    DEFAULT_BUFFER_SIZE = 1000
    MIN_BUFFER_SIZE = 10
    MAX_BUFFER_SIZE = 10000

    # Time series
    DEFAULT_TIME_INTERVAL_MINUTES = 5
    MIN_TIME_INTERVAL_MINUTES = 1
    MAX_TIME_INTERVAL_MINUTES = 60

    DEFAULT_DURATION_HOURS = 24
    MAX_DURATION_HOURS = 168  # 1 week

    # Status filters
    class Status(str, Enum):
        PASS = "pass"
        FAIL = "fail"
        ERROR = "error"
        ALL = "all"


# API Constants
class APIConstants:
    """Constants for API endpoints."""

    # Pagination
    DEFAULT_OFFSET = 0
    DEFAULT_LIMIT = 100
    MAX_LIMIT = 1000
    MIN_LIMIT = 1

    # Rate limiting
    REQUESTS_PER_MINUTE = 100
    REQUESTS_PER_HOUR = 1000

    # Timeouts
    REQUEST_TIMEOUT_SECONDS = 30
    LONG_POLL_TIMEOUT_SECONDS = 60

    # File uploads
    MAX_UPLOAD_SIZE_MB = 50
    ALLOWED_UPLOAD_EXTENSIONS = [".png", ".jpg", ".jpeg", ".bmp", ".tiff"]

    # API versions
    API_VERSION = "v1"
    MIN_CLIENT_VERSION = "1.0.0"


# System Constants
class SystemConstants:
    """Constants for system operations."""

    # Logging
    LOG_LEVEL_DEFAULT = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_FILE_BACKUP_COUNT = 5

    # Threading
    MAX_WORKER_THREADS = 10
    THREAD_POOL_SIZE = 4

    # File system
    TEMP_DIR = "/tmp/machinevision"
    DATA_DIR = "./data"
    CLEANUP_INTERVAL_SECONDS = 3600  # 1 hour

    # Health checks
    HEALTH_CHECK_INTERVAL_SECONDS = 30
    MEMORY_WARNING_THRESHOLD = 0.8  # 80% memory usage
    DISK_WARNING_THRESHOLD = 0.9  # 90% disk usage


# Color Constants (BGR format for OpenCV)
class Colors:
    """Standard colors for drawing operations (BGR format)."""

    GREEN = (0, 255, 0)
    RED = (0, 0, 255)
    BLUE = (255, 0, 0)
    YELLOW = (0, 255, 255)
    CYAN = (255, 255, 0)
    MAGENTA = (255, 0, 255)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    ORANGE = (0, 165, 255)
    PURPLE = (128, 0, 128)

    # Semantic colors
    SUCCESS = GREEN
    ERROR = RED
    WARNING = YELLOW
    INFO = BLUE
    PRIMARY = BLUE
    SECONDARY = CYAN


# Drawing Constants
class DrawingConstants:
    """Constants for drawing operations."""

    # Line thickness
    DEFAULT_LINE_THICKNESS = 2
    THIN_LINE = 1
    THICK_LINE = 3
    BOLD_LINE = 5

    # Font settings
    DEFAULT_FONT = 0  # cv2.FONT_HERSHEY_SIMPLEX
    DEFAULT_FONT_SCALE = 1.0
    SMALL_FONT_SCALE = 0.5
    LARGE_FONT_SCALE = 1.5

    # Marker sizes
    DEFAULT_MARKER_SIZE = 5
    SMALL_MARKER_SIZE = 3
    LARGE_MARKER_SIZE = 10


# Error Messages
class ErrorMessages:
    """Standard error messages."""

    # Image errors
    IMAGE_NOT_FOUND = "Image with ID {image_id} not found"
    IMAGE_STORAGE_FULL = "Image storage is full, cannot store new image"
    INVALID_IMAGE_FORMAT = "Invalid image format: {format}"

    # Camera errors
    CAMERA_NOT_FOUND = "Camera {camera_id} not found"
    CAMERA_CONNECTION_FAILED = "Failed to connect to camera {camera_id}: {error}"
    CAMERA_CAPTURE_FAILED = "Failed to capture from camera {camera_id}: {error}"
    CAMERA_ALREADY_EXISTS = "Camera {camera_id} already exists"

    # Template errors
    TEMPLATE_NOT_FOUND = "Template {template_id} not found"
    TEMPLATE_UPLOAD_FAILED = "Failed to upload template: {error}"
    TEMPLATE_INVALID_SIZE = "Template size {size} is invalid (min: {min}, max: {max})"

    # ROI errors
    ROI_OUT_OF_BOUNDS = "ROI {roi} is out of image bounds {bounds}"
    ROI_INVALID_SIZE = "ROI size is invalid: {width}x{height}"
    ROI_MISSING_PARAMS = "ROI requires all parameters: x, y, width, height"

    # Processing errors
    PROCESSING_FAILED = "Image processing failed: {error}"
    INVALID_PARAMETER = "Invalid parameter {param}: {value}"
    OPERATION_TIMEOUT = "Operation timed out after {timeout} seconds"

    # System errors
    INITIALIZATION_FAILED = "Failed to initialize {component}: {error}"
    CONFIGURATION_ERROR = "Configuration error: {error}"
    RESOURCE_EXHAUSTED = "Resource exhausted: {resource}"


# Success Messages
class SuccessMessages:
    """Standard success messages."""

    CAMERA_CONNECTED = "Successfully connected to camera {camera_id}"
    CAMERA_DISCONNECTED = "Successfully disconnected camera {camera_id}"
    IMAGE_CAPTURED = "Successfully captured image {image_id}"
    TEMPLATE_UPLOADED = "Successfully uploaded template {template_id}"
    TEMPLATE_DELETED = "Successfully deleted template {template_id}"
    PROCESSING_COMPLETE = "Processing completed successfully"
