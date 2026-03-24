"""
XADRAS Vision Service - ArUco Marker Detector
Detects ArUco markers at chessboard corners with partial visibility support
"""

import cv2
import numpy as np
import time
from typing import Optional, Dict, Tuple, List
from dataclasses import dataclass

from .config import config


@dataclass
class DetectionResult:
    """Result of ArUco marker detection"""
    corners: Dict[int, np.ndarray]  # marker_id -> corner center point
    all_corners: Optional[np.ndarray]  # 4 corner points in order (if available)
    markers_visible: int
    success: bool
    message: str
    using_memory: bool = False  # True if using remembered corners


class ArucoDetector:
    """
    ArUco marker detector for chessboard corner detection.
    
    Marker Layout (looking at board from white's perspective):
        ID 0 (a8) ─────────── ID 1 (h8)
            │                     │
            │    Chess Board      │
            │                     │
        ID 3 (a1) ─────────── ID 2 (h1)
    
    Supports detection with 2-4 visible markers.
    Uses corner memory to handle temporary occlusions.
    """
    
    # Corner indices for marker IDs
    CORNER_ORDER = {
        0: 0,  # a8 - top-left
        1: 1,  # h8 - top-right
        2: 2,  # h1 - bottom-right
        3: 3,  # a1 - bottom-left
    }
    
    # How long to remember corners when markers are occluded (seconds)
    CORNER_MEMORY_DURATION = 3.0
    
    def __init__(self):
        # Initialize ArUco detector
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(config.aruco_dict_id)
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        
        # Expected marker IDs
        self.expected_ids = set(config.aruco_marker_ids)
        
        # Corner smoothing (for temporal stability)
        self.corner_history: Dict[int, List[np.ndarray]] = {i: [] for i in self.expected_ids}
        self.history_size = 5
        
        # Last known good corners with timestamps for memory persistence
        self.last_known_corners: Dict[int, np.ndarray] = {}
        self.corner_timestamps: Dict[int, float] = {}
    
    def detect(self, frame: np.ndarray) -> DetectionResult:
        """
        Detect ArUco markers in frame.
        Uses corner memory to handle temporary occlusions.
        
        Args:
            frame: BGR image from camera
            
        Returns:
            DetectionResult with detected corners
        """
        current_time = time.time()
        
        # Convert to grayscale for detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect markers
        corners, ids, rejected = self.detector.detectMarkers(gray)
        
        # Extract center points for each detected marker
        detected_corners = {}
        if ids is not None and len(ids) > 0:
            for i, marker_id in enumerate(ids.flatten()):
                if marker_id in self.expected_ids:
                    # Get center of the marker
                    marker_corners = corners[i][0]
                    center = np.mean(marker_corners, axis=0)
                    detected_corners[marker_id] = center
                    
                    # Update history for smoothing
                    self._update_history(marker_id, center)
                    
                    # Update memory with timestamp
                    self.last_known_corners[marker_id] = center.copy()
                    self.corner_timestamps[marker_id] = current_time
        
        markers_visible = len(detected_corners)
        using_memory = False
        
        # Merge with remembered corners if we have less than 4 visible
        if markers_visible < 4:
            effective_corners = detected_corners.copy()
            for marker_id in self.expected_ids:
                if marker_id not in effective_corners and marker_id in self.last_known_corners:
                    # Check if remembered corner is still valid (within memory duration)
                    age = current_time - self.corner_timestamps.get(marker_id, 0)
                    if age < self.CORNER_MEMORY_DURATION:
                        effective_corners[marker_id] = self.last_known_corners[marker_id]
                        using_memory = True
        else:
            effective_corners = detected_corners
        
        effective_count = len(effective_corners)
        
        # Check if we have enough markers (including remembered ones)
        if effective_count < config.min_markers_required:
            return DetectionResult(
                corners=detected_corners,
                all_corners=None,
                markers_visible=markers_visible,
                success=False,
                message=f"Only {effective_count} markers available, need {config.min_markers_required}",
                using_memory=using_memory
            )
        
        # Try to get all 4 corners (interpolate missing ones if possible)
        all_corners = self._get_all_corners(effective_corners)
        
        if all_corners is None:
            return DetectionResult(
                corners=detected_corners,
                all_corners=None,
                markers_visible=markers_visible,
                success=False,
                message="Could not interpolate missing corners",
                using_memory=using_memory
            )
        
        memory_msg = " (using memory)" if using_memory else ""
        return DetectionResult(
            corners=detected_corners,
            all_corners=all_corners,
            markers_visible=markers_visible,
            success=True,
            message=f"Detected {markers_visible} markers{memory_msg}",
            using_memory=using_memory
        )
    
    def _update_history(self, marker_id: int, point: np.ndarray):
        """Update corner history for smoothing"""
        history = self.corner_history[marker_id]
        history.append(point.copy())
        if len(history) > self.history_size:
            history.pop(0)
    
    def _get_smoothed_corner(self, marker_id: int) -> Optional[np.ndarray]:
        """Get smoothed corner position from history"""
        history = self.corner_history[marker_id]
        if len(history) == 0:
            return None
        return np.mean(history, axis=0)
    
    def _get_all_corners(self, detected: Dict[int, np.ndarray]) -> Optional[np.ndarray]:
        """
        Get all 4 corners, interpolating missing ones if needed.
        
        Returns corners in order: [top-left, top-right, bottom-right, bottom-left]
        which corresponds to: [a8, h8, h1, a1]
        """
        corners = [None, None, None, None]
        
        # Fill in detected corners
        for marker_id, point in detected.items():
            if marker_id in self.CORNER_ORDER:
                idx = self.CORNER_ORDER[marker_id]
                smoothed = self._get_smoothed_corner(marker_id)
                corners[idx] = smoothed if smoothed is not None else point
        
        # Count how many we have
        detected_count = sum(1 for c in corners if c is not None)
        
        if detected_count == 4:
            return np.array(corners, dtype=np.float32)
        
        if detected_count == 3:
            return self._interpolate_one_corner(corners)
        
        if detected_count == 2:
            return self._interpolate_two_corners(corners)
        
        return None
    
    def _interpolate_one_corner(self, corners: List[Optional[np.ndarray]]) -> Optional[np.ndarray]:
        """Interpolate one missing corner from 3 known corners"""
        # Find which corner is missing
        missing_idx = None
        for i, c in enumerate(corners):
            if c is None:
                missing_idx = i
                break
        
        if missing_idx is None:
            return np.array(corners, dtype=np.float32)
        
        # Get the three known corners
        known = [(i, corners[i]) for i in range(4) if corners[i] is not None]
        
        # In a parallelogram, opposite corners sum to the same value
        # For a rectangle: corner0 + corner2 = corner1 + corner3
        # So missing corner = other_diagonal_sum - opposite_corner
        
        opposite_idx = (missing_idx + 2) % 4
        adjacent1_idx = (missing_idx + 1) % 4
        adjacent2_idx = (missing_idx + 3) % 4
        
        if corners[opposite_idx] is None:
            return None  # Can't interpolate
        
        # Estimate: missing = adjacent1 + adjacent2 - opposite
        corners[missing_idx] = (
            corners[adjacent1_idx] + corners[adjacent2_idx] - corners[opposite_idx]
        )
        
        return np.array(corners, dtype=np.float32)
    
    def _interpolate_two_corners(self, corners: List[Optional[np.ndarray]]) -> Optional[np.ndarray]:
        """
        Interpolate two missing corners from 2 known corners.
        Only works if we have diagonal corners (0,2) or (1,3).
        """
        known_indices = [i for i, c in enumerate(corners) if c is not None]
        
        if len(known_indices) != 2:
            return None
        
        # Check if they're diagonal
        if set(known_indices) == {0, 2} or set(known_indices) == {1, 3}:
            # We have diagonal corners - can estimate a square
            c1, c2 = corners[known_indices[0]], corners[known_indices[1]]
            
            # Center point
            center = (c1 + c2) / 2
            
            # Half diagonal vector
            half_diag = (c2 - c1) / 2
            
            # Perpendicular vector (rotated 90 degrees for other diagonal)
            perp = np.array([-half_diag[1], half_diag[0]])
            
            # Estimate the other two corners
            if set(known_indices) == {0, 2}:
                # We have top-left and bottom-right
                corners[1] = center + perp  # top-right
                corners[3] = center - perp  # bottom-left
            else:
                # We have top-right and bottom-left
                corners[0] = center - perp  # top-left
                corners[2] = center + perp  # bottom-right
            
            return np.array(corners, dtype=np.float32)
        
        # Adjacent corners - can try to estimate using last known positions
        # This is less reliable
        for i in range(4):
            if corners[i] is None and i in self.last_known_corners:
                corners[i] = self.last_known_corners[i]
        
        all_filled = all(c is not None for c in corners)
        if all_filled:
            return np.array(corners, dtype=np.float32)
        
        return None
    
    def draw_markers(self, frame: np.ndarray, result: DetectionResult) -> np.ndarray:
        """Draw detected markers on frame for debugging"""
        output = frame.copy()
        
        # Draw detected corner centers (green = live, orange = from memory)
        for marker_id, point in result.corners.items():
            pt = tuple(point.astype(int))
            cv2.circle(output, pt, 10, (0, 255, 0), -1)  # Green for live detection
            cv2.putText(output, f"ID:{marker_id}", (pt[0] + 15, pt[1]), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Draw remembered corners (orange) that aren't currently detected
        if result.using_memory:
            current_time = time.time()
            for marker_id in self.expected_ids:
                if marker_id not in result.corners and marker_id in self.last_known_corners:
                    age = current_time - self.corner_timestamps.get(marker_id, 0)
                    if age < self.CORNER_MEMORY_DURATION:
                        pt = tuple(self.last_known_corners[marker_id].astype(int))
                        # Orange color with fading based on age
                        alpha = 1.0 - (age / self.CORNER_MEMORY_DURATION)
                        cv2.circle(output, pt, 10, (0, 165, 255), 2)  # Orange outline
                        cv2.putText(output, f"MEM:{marker_id}", (pt[0] + 15, pt[1]), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
        
        # Draw board outline if we have all corners
        if result.all_corners is not None:
            pts = result.all_corners.astype(int)
            # Yellow if live, orange if using memory
            color = (0, 165, 255) if result.using_memory else (0, 255, 255)
            for i in range(4):
                cv2.line(output, tuple(pts[i]), tuple(pts[(i + 1) % 4]), color, 2)
        
        # Add status text
        status = f"Markers: {result.markers_visible}/4 - {'OK' if result.success else result.message}"
        if result.using_memory:
            status += " [MEMORY]"
        cv2.putText(output, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        return output
