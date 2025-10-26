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
    MAX_THUMBNAIL_WIDTH = 2000  # Allow full resolution thumbnails in debug mode
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


# Edge Detection Default Parameters
class EdgeDetectionDefaults:
    """Default parameters for edge detection algorithms."""

    # Canny edge detection
    CANNY_LOW_THRESHOLD = 50
    CANNY_HIGH_THRESHOLD = 150
    CANNY_APERTURE_SIZE = 3
    CANNY_L2_GRADIENT = False

    # Sobel edge detection
    SOBEL_KERNEL_SIZE = 3
    SOBEL_SCALE = 1.0
    SOBEL_DELTA = 0.0
    SOBEL_THRESHOLD = 50.0

    # Laplacian edge detection
    LAPLACIAN_KERNEL_SIZE = 3
    LAPLACIAN_SCALE = 1.0
    LAPLACIAN_DELTA = 0.0
    LAPLACIAN_THRESHOLD = 30.0

    # Prewitt edge detection
    PREWITT_THRESHOLD = 50.0

    # Scharr edge detection
    SCHARR_SCALE = 1.0
    SCHARR_DELTA = 0.0
    SCHARR_THRESHOLD = 50.0

    # Morphological gradient
    MORPH_KERNEL_SIZE = 3
    MORPH_THRESHOLD = 30.0

    # Preprocessing defaults
    BLUR_KERNEL_SIZE = 5
    BILATERAL_D = 9
    BILATERAL_SIGMA_COLOR = 75.0
    BILATERAL_SIGMA_SPACE = 75.0
    MORPHOLOGY_KERNEL_SIZE = 3

    # Contour filtering
    MIN_CONTOUR_AREA = 10.0
    MIN_CONTOUR_PERIMETER = 0.0
    MAX_CONTOURS = 100
    CONTOUR_APPROX_EPSILON = 0.02

    # Visualization
    SHOW_CENTERS = True
    LINE_THICKNESS = 2


# Color Detection Default Parameters
class ColorDetectionDefaults:
    """Default parameters for color detection algorithms."""

    # Detection methods
    DEFAULT_METHOD = "histogram"
    KMEANS_CLUSTERS = 3
    KMEANS_RANDOM_STATE = 42
    KMEANS_N_INIT = 10

    # Color matching
    MIN_PERCENTAGE = 50.0

    # Contour masking
    USE_CONTOUR_MASK = True


# ArUco Detection Default Parameters
class ArucoDetectionDefaults:
    """Default parameters for ArUco marker detection."""

    # Default dictionary
    DEFAULT_DICTIONARY = "DICT_4X4_50"

    # Visualization
    LINE_THICKNESS = 2
    CENTER_RADIUS = 3
    ROTATION_LINE_COLOR = (0, 255, 255)  # Yellow (BGR)
    CENTER_COLOR = (0, 0, 255)  # Red (BGR)
    TEXT_COLOR = (0, 255, 0)  # Green (BGR)


# Template Matching Default Parameters
class TemplateMatchDefaults:
    """Default parameters for template matching."""

    # Matching method and threshold
    DEFAULT_METHOD = "TM_CCOEFF_NORMED"
    DEFAULT_THRESHOLD = 0.8

    # Multi-scale matching
    MULTI_SCALE_ENABLED = False
    SCALE_RANGE_MIN = 0.8
    SCALE_RANGE_MAX = 1.2
    SCALE_STEPS = 5

    # Visualization
    LINE_THICKNESS = 2
    MATCH_COLOR = (0, 255, 0)  # Green (BGR)
    TEXT_COLOR = (0, 255, 0)  # Green (BGR)


# Rotation Detection Default Parameters
class RotationDetectionDefaults:
    """Default parameters for rotation detection algorithms."""

    # Default settings
    DEFAULT_METHOD = "min_area_rect"
    DEFAULT_ANGLE_RANGE = "0_360"

    # Method confidence defaults
    MIN_AREA_RECT_CONFIDENCE = 1.0
    ELLIPSE_FIT_CONFIDENCE = 0.9
    PCA_CONFIDENCE_SCALE = 10.0  # Divisor for eigenvalue ratio normalization

    # Ellipse fitting minimum points
    MIN_POINTS_FOR_ELLIPSE = 5
    MIN_POINTS_FOR_ROTATION = 3

    # Visualization
    ROTATION_LINE_LENGTH = 50
    LINE_THICKNESS = 3
    CENTER_RADIUS = 5
    ARROW_TIP_LENGTH = 0.3
    CONTOUR_COLOR = (0, 255, 255)  # Cyan (BGR)
    CENTER_COLOR = (0, 0, 255)  # Red (BGR)
    ARROW_COLOR = (0, 255, 0)  # Green (BGR)
    TEXT_COLOR = (0, 255, 0)  # Green (BGR)
