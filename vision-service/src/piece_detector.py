"""
XADRAS Vision Service - Piece Detector
YOLO-based chess piece detection

PLACEHOLDER: This module is ready for the user's trained YOLO model.
Place your model file at: models/chess_pieces.pt
"""

import numpy as np
from typing import Dict, Optional, List, Tuple
from pathlib import Path

from .config import config


# Class mapping from YOLO class index to FEN symbol
CLASS_TO_FEN = {
    0: None,   # vazio (empty)
    1: 'b',    # black-bishop
    2: 'k',    # black-king
    3: 'n',    # black-knight
    4: 'p',    # black-pawn
    5: 'q',    # black-queen
    6: 'r',    # black-rook
    7: 'B',    # white-bishop
    8: 'K',    # white-king
    9: 'N',    # white-knight
    10: 'P',   # white-pawn
    11: 'Q',   # white-queen
    12: 'R',   # white-rook
}

# Reverse mapping for display
FEN_TO_CLASS_NAME = {
    'b': 'black-bishop',
    'k': 'black-king',
    'n': 'black-knight',
    'p': 'black-pawn',
    'q': 'black-queen',
    'r': 'black-rook',
    'B': 'white-bishop',
    'K': 'white-king',
    'N': 'white-knight',
    'P': 'white-pawn',
    'Q': 'white-queen',
    'R': 'white-rook',
}


class PieceDetector:
    """
    YOLO-based chess piece detector.
    
    Usage:
        detector = PieceDetector()
        if detector.is_loaded():
            pieces = detector.detect(warped_board_image)
            # pieces = {'e2': 'P', 'e7': 'p', 'e1': 'K', ...}
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or config.model_path
        self.model = None
        self.confidence_threshold = config.confidence_threshold
        
        # Board dimensions (matches warped board size)
        self.board_size = config.board_size
        self.square_size = self.board_size // 8
        
        # Try to load the model
        self._load_model()
    
    def _load_model(self):
        """Attempt to load the YOLO model"""
        model_file = Path(self.model_path)
        
        if not model_file.exists():
            print(f"[PieceDetector] Model not found at: {self.model_path}")
            print("[PieceDetector] Running in PLACEHOLDER mode - no detection will occur")
            print("[PieceDetector] Place your trained model at the path above to enable detection")
            return
        
        try:
            from ultralytics import YOLO
            self.model = YOLO(str(model_file))
            print(f"[PieceDetector] Model loaded successfully: {self.model_path}")
        except ImportError:
            print("[PieceDetector] ultralytics not installed. Install with: pip install ultralytics")
        except Exception as e:
            print(f"[PieceDetector] Failed to load model: {e}")
    
    def is_loaded(self) -> bool:
        """Check if the model is loaded and ready"""
        return self.model is not None
    
    def detect(self, warped_board: np.ndarray) -> Dict[str, str]:
        """
        Detect pieces on the warped board image.
        
        Args:
            warped_board: 800x800 warped top-down view of the board
            
        Returns:
            Dictionary mapping square names to piece symbols (FEN notation)
            e.g., {'e1': 'K', 'e8': 'k', 'd1': 'Q', ...}
            Empty squares are not included.
        """
        if not self.is_loaded():
            return {}
        
        try:
            # Run YOLO inference
            results = self.model(warped_board, verbose=False)
            
            if len(results) == 0:
                return {}
            
            # Process detections
            pieces = {}
            
            for result in results:
                boxes = result.boxes
                
                if boxes is None:
                    continue
                
                for i in range(len(boxes)):
                    # Get bounding box center
                    box = boxes.xyxy[i].cpu().numpy()  # [x1, y1, x2, y2]
                    center_x = (box[0] + box[2]) / 2
                    center_y = (box[1] + box[3]) / 2
                    
                    # Get class and confidence
                    class_id = int(boxes.cls[i].cpu().numpy())
                    confidence = float(boxes.conf[i].cpu().numpy())
                    
                    # Filter by confidence
                    if confidence < self.confidence_threshold:
                        continue
                    
                    # Skip empty class
                    if class_id == 0:  # vazio
                        continue
                    
                    # Map to FEN symbol
                    fen_symbol = CLASS_TO_FEN.get(class_id)
                    if fen_symbol is None:
                        continue
                    
                    # Convert pixel position to square name
                    square = self._pixel_to_square(center_x, center_y)
                    
                    # Store detection (if multiple detections per square, keep highest confidence)
                    if square not in pieces:
                        pieces[square] = fen_symbol
            
            return pieces
            
        except Exception as e:
            print(f"[PieceDetector] Detection error: {e}")
            return {}
    
    def _pixel_to_square(self, x: float, y: float) -> str:
        """Convert pixel coordinates to square name"""
        file_idx = min(7, max(0, int(x // self.square_size)))
        rank_idx = min(7, max(0, 7 - int(y // self.square_size)))
        
        files = 'abcdefgh'
        return f"{files[file_idx]}{rank_idx + 1}"
    
    def detect_with_visualization(self, warped_board: np.ndarray) -> Tuple[Dict[str, str], np.ndarray]:
        """
        Detect pieces and return visualization.
        
        Returns:
            Tuple of (pieces_dict, annotated_image)
        """
        pieces = self.detect(warped_board)
        
        # Create visualization
        vis = warped_board.copy()
        
        import cv2
        
        for square, piece in pieces.items():
            # Calculate square center
            file_idx = ord(square[0]) - ord('a')
            rank_idx = int(square[1]) - 1
            
            x = file_idx * self.square_size + self.square_size // 2
            y = (7 - rank_idx) * self.square_size + self.square_size // 2
            
            # Draw piece label
            color = (0, 0, 255) if piece.islower() else (255, 0, 0)  # Red for black, Blue for white
            cv2.putText(vis, piece, (x - 10, y + 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
        
        return pieces, vis


# Placeholder function for testing without model
def create_test_position() -> Dict[str, str]:
    """Create standard starting position for testing"""
    return {
        # White pieces
        'a1': 'R', 'b1': 'N', 'c1': 'B', 'd1': 'Q',
        'e1': 'K', 'f1': 'B', 'g1': 'N', 'h1': 'R',
        'a2': 'P', 'b2': 'P', 'c2': 'P', 'd2': 'P',
        'e2': 'P', 'f2': 'P', 'g2': 'P', 'h2': 'P',
        # Black pieces
        'a7': 'p', 'b7': 'p', 'c7': 'p', 'd7': 'p',
        'e7': 'p', 'f7': 'p', 'g7': 'p', 'h7': 'p',
        'a8': 'r', 'b8': 'n', 'c8': 'b', 'd8': 'q',
        'e8': 'k', 'f8': 'b', 'g8': 'n', 'h8': 'r',
    }
