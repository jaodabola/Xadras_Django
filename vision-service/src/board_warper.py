"""
XADRAS Vision Service - Board Warper
Perspective transformation to get top-down view of the chessboard
"""

import cv2
import numpy as np
from typing import Tuple, Optional

from .config import config


class BoardWarper:
    """
    Transforms the detected chessboard region to a perfect square top-down view.
    
    Input: 4 corner points from ArUco detection
    Output: 800x800 (configurable) warped image with a1 at bottom-left
    """
    
    def __init__(self, output_size: int = None):
        self.output_size = output_size or config.board_size
        
        # Define destination points (perfect square)
        # Order: top-left, top-right, bottom-right, bottom-left
        # Which corresponds to: a8, h8, h1, a1
        self.dst_points = np.array([
            [0, 0],                              # a8 - top-left
            [self.output_size, 0],               # h8 - top-right
            [self.output_size, self.output_size], # h1 - bottom-right
            [0, self.output_size]                # a1 - bottom-left
        ], dtype=np.float32)
        
        # Square size in pixels
        self.square_size = self.output_size // 8
    
    def warp(self, frame: np.ndarray, corners: np.ndarray) -> Optional[np.ndarray]:
        """
        Warp the perspective to get a top-down view of the board.
        
        Args:
            frame: Original camera frame (BGR)
            corners: 4 corner points in order [a8, h8, h1, a1]
            
        Returns:
            Warped image of the board (output_size x output_size) or None if failed
        """
        if corners is None or len(corners) != 4:
            return None
        
        try:
            # Ensure corners are float32
            src_points = corners.astype(np.float32)
            
            # Calculate perspective transform matrix
            transform_matrix = cv2.getPerspectiveTransform(src_points, self.dst_points)
            
            # Apply the transformation
            warped = cv2.warpPerspective(
                frame, 
                transform_matrix, 
                (self.output_size, self.output_size)
            )
            
            return warped
            
        except Exception as e:
            print(f"Warp error: {e}")
            return None
    
    def get_square_region(self, warped: np.ndarray, file: int, rank: int) -> np.ndarray:
        """
        Extract a single square from the warped board image.
        
        Args:
            warped: Warped board image
            file: File index 0-7 (a=0, h=7)
            rank: Rank index 0-7 (1=0, 8=7)
            
        Returns:
            Image of the single square
        """
        # Calculate pixel coordinates
        # Note: In warped image, rank 8 is at top (y=0), rank 1 at bottom
        x1 = file * self.square_size
        x2 = (file + 1) * self.square_size
        y1 = (7 - rank) * self.square_size  # Flip because rank 8 is at top
        y2 = (8 - rank) * self.square_size
        
        return warped[y1:y2, x1:x2]
    
    def get_all_squares(self, warped: np.ndarray) -> dict:
        """
        Extract all 64 squares from the warped board.
        
        Returns:
            Dictionary mapping square name (e.g., 'e4') to square image
        """
        squares = {}
        files = 'abcdefgh'
        
        for file_idx, file_letter in enumerate(files):
            for rank in range(8):
                square_name = f"{file_letter}{rank + 1}"
                squares[square_name] = self.get_square_region(warped, file_idx, rank)
        
        return squares
    
    def pixel_to_square(self, x: int, y: int) -> str:
        """
        Convert pixel coordinates in warped image to square name.
        
        Args:
            x: X coordinate in warped image
            y: Y coordinate in warped image
            
        Returns:
            Square name (e.g., 'e4')
        """
        file_idx = min(7, max(0, x // self.square_size))
        rank_idx = min(7, max(0, 7 - (y // self.square_size)))
        
        files = 'abcdefgh'
        return f"{files[file_idx]}{rank_idx + 1}"
    
    def draw_grid(self, warped: np.ndarray) -> np.ndarray:
        """Draw chess grid overlay on warped image for debugging"""
        output = warped.copy()
        
        # Draw grid lines
        for i in range(9):
            pos = i * self.square_size
            cv2.line(output, (pos, 0), (pos, self.output_size), (0, 255, 0), 1)
            cv2.line(output, (0, pos), (self.output_size, pos), (0, 255, 0), 1)
        
        # Label squares
        files = 'abcdefgh'
        for file_idx, file_letter in enumerate(files):
            for rank in range(8):
                x = file_idx * self.square_size + 5
                y = (7 - rank) * self.square_size + 20
                cv2.putText(output, f"{file_letter}{rank+1}", (x, y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
        
        return output
