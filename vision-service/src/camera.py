"""
XADRAS Vision Service - Camera Interface
Abstraction for Raspberry Pi AI Camera and USB cameras
"""

import cv2
import numpy as np
import time
from typing import Optional, Tuple
from dataclasses import dataclass

from .config import config


@dataclass
class Frame:
    """Captured frame with metadata"""
    image: np.ndarray
    timestamp: float
    width: int
    height: int


class Camera:
    """
    Camera interface supporting both Raspberry Pi AI Camera and USB cameras.
    
    For Raspberry Pi:
        - Uses picamera2 library
        - Optimized for RPi AI Camera
        
    For USB/Other:
        - Uses OpenCV VideoCapture
        - Works on any platform
    """
    
    def __init__(self):
        self.capture = None
        self.picam = None
        self.use_picamera = config.use_picamera
        self.width = config.camera_width
        self.height = config.camera_height
        self.camera_index = config.camera_index
        self.is_open = False
    
    def open(self) -> bool:
        """Open the camera"""
        if self.use_picamera:
            return self._open_picamera()
        else:
            return self._open_opencv()
    
    def _open_picamera(self) -> bool:
        """Open Raspberry Pi camera using picamera2"""
        try:
            from picamera2 import Picamera2
            
            self.picam = Picamera2()
            
            # Configure camera
            camera_config = self.picam.create_preview_configuration(
                main={"size": (self.width, self.height), "format": "RGB888"}
            )
            self.picam.configure(camera_config)
            self.picam.start()
            
            # Wait for camera to warm up
            time.sleep(0.5)
            
            self.is_open = True
            print(f"[Camera] Raspberry Pi camera opened: {self.width}x{self.height}")
            return True
            
        except ImportError:
            print("[Camera] picamera2 not installed, falling back to OpenCV")
            self.use_picamera = False
            return self._open_opencv()
        except Exception as e:
            print(f"[Camera] Failed to open Pi camera: {e}")
            print("[Camera] Falling back to OpenCV")
            self.use_picamera = False
            return self._open_opencv()
    
    def _open_opencv(self) -> bool:
        """Open camera using OpenCV"""
        try:
            self.capture = cv2.VideoCapture(self.camera_index)
            
            if not self.capture.isOpened():
                print(f"[Camera] Failed to open camera at index {self.camera_index}")
                return False
            
            # Set resolution
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640) #self.width)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 640) #self.height)
            
            # Get actual resolution (may differ from requested)
            actual_width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            self.is_open = True
            print(f"[Camera] OpenCV camera opened: {actual_width}x{actual_height}")
            return True
            
        except Exception as e:
            print(f"[Camera] Failed to open camera: {e}")
            return False
    
    def read(self) -> Optional[Frame]:
        """Capture a frame from the camera"""
        if not self.is_open:
            return None
        
        try:
            if self.use_picamera and self.picam is not None:
                return self._read_picamera()
            elif self.capture is not None:
                return self._read_opencv()
            return None
        except Exception as e:
            print(f"[Camera] Read error: {e}")
            return None
    
    def _read_picamera(self) -> Optional[Frame]:
        """Read frame from Pi camera"""
        image = self.picam.capture_array()
        
        # picamera2 returns RGB, convert to BGR for OpenCV compatibility
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        return Frame(
            image=image,
            timestamp=time.time(),
            width=image.shape[1],
            height=image.shape[0]
        )
    
    def _read_opencv(self) -> Optional[Frame]:
        """Read frame from OpenCV camera"""
        ret, image = self.capture.read()
        
        if not ret or image is None:
            return None
        
        return Frame(
            image=image,
            timestamp=time.time(),
            width=image.shape[1],
            height=image.shape[0]
        )
    
    def close(self):
        """Close the camera"""
        if self.picam is not None:
            try:
                self.picam.stop()
                self.picam.close()
            except:
                pass
            self.picam = None
        
        if self.capture is not None:
            try:
                self.capture.release()
            except:
                pass
            self.capture = None
        
        self.is_open = False
        print("[Camera] Camera closed")
    
    def __enter__(self):
        """Context manager entry"""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


def test_camera():
    """Test camera functionality"""
    print("Testing camera...")
    
    camera = Camera()
    if not camera.open():
        print("Failed to open camera")
        return False
    
    print("Camera opened, capturing test frame...")
    frame = camera.read()
    
    if frame is None:
        print("Failed to capture frame")
        camera.close()
        return False
    
    print(f"Captured frame: {frame.width}x{frame.height}")
    
    # Save test frame
    cv2.imwrite("test_frame.jpg", frame.image)
    print("Test frame saved to test_frame.jpg")
    
    camera.close()
    return True


if __name__ == "__main__":
    test_camera()
