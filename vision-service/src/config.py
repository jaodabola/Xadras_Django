"""
XADRAS Vision Service - Configuration
Environment-based configuration for Raspberry Pi deployment
"""

import os
from dataclasses import dataclass
from typing import List


@dataclass
class Config:
    """Vision service configuration loaded from environment variables"""
    
    # Backend connection
    backend_ws_url: str = os.getenv(
        "BACKEND_WS_URL", 
        "ws://localhost:8000/ws/vision/"
    )
    backend_http_url: str = os.getenv(
        "BACKEND_HTTP_URL",
        "http://localhost:8000"
    )
    
    # Camera authentication
    camera_token: str = os.getenv("CAMERA_TOKEN", "")
    camera_id: str = os.getenv("CAMERA_ID", "")
    
    # Camera settings
    camera_index: int = int(os.getenv("CAMERA_INDEX", "0"))
    camera_width: int = int(os.getenv("CAMERA_WIDTH", "1920"))
    camera_height: int = int(os.getenv("CAMERA_HEIGHT", "1080"))
    use_picamera: bool = os.getenv("USE_PICAMERA", "true").lower() == "true"
    
    # ArUco marker settings
    aruco_dict_id: int = int(os.getenv("ARUCO_DICT_ID", "1"))  # DICT_4X4_50
    aruco_marker_ids: List[int] = None  # Set in __post_init__
    
    # Board settings
    board_size: int = int(os.getenv("BOARD_SIZE", "800"))  # Output size in pixels
    
    # YOLO model settings
    model_path: str = os.getenv("MODEL_PATH", "models/chess_pieces.pt")
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))
    
    # Processing settings
    process_interval: float = float(os.getenv("PROCESS_INTERVAL", "0.2"))  # 5 FPS
    min_markers_required: int = int(os.getenv("MIN_MARKERS_REQUIRED", "3"))
    
    # Debug settings
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    save_debug_images: bool = os.getenv("SAVE_DEBUG_IMAGES", "false").lower() == "true"
    
    def __post_init__(self):
        # Parse marker IDs from environment or use defaults
        marker_ids_str = os.getenv("ARUCO_MARKER_IDS", "0,1,2,3")
        self.aruco_marker_ids = [int(x) for x in marker_ids_str.split(",")]
    
    def validate(self) -> bool:
        """Validate configuration"""
        errors = []
        
        if not self.camera_token and not self.debug:
            errors.append("CAMERA_TOKEN is required for production")
        
        if self.min_markers_required < 2:
            errors.append("MIN_MARKERS_REQUIRED must be at least 2")
        
        if errors:
            for error in errors:
                print(f"Config Error: {error}")
            return False
        
        return True


# Global config instance
config = Config()
config.__post_init__()
