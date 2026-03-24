#!/usr/bin/env python3
"""
XADRAS Vision Service - Main Entry Point
Chess board detection and piece recognition for physical boards

Usage:
    python main.py                  # Run with default settings
    python main.py --debug          # Run with debug visualization
    python main.py --test           # Run with test position (no camera)
"""

import asyncio
import argparse
import signal
import sys
import time
from typing import Optional

# Add src to path
sys.path.insert(0, '.')

from src.config import config
from src.camera import Camera
from src.aruco_detector import ArucoDetector
from src.board_warper import BoardWarper
from src.piece_detector import PieceDetector
from src.fen_generator import generate_fen, compare_positions
from src.websocket_client import WebSocketClient, MockWebSocketClient, BoardUpdate


class VisionService:
    """
    Main Vision Service orchestrating all components.
    
    Flow:
        Camera → ArUco Detection → Board Warp → Piece Detection → FEN → WebSocket
    """
    
    def __init__(self, debug: bool = False, use_mock_ws: bool = False):
        self.debug = debug or config.debug
        self.running = False
        
        # Initialize components
        self.camera = Camera()
        self.aruco_detector = ArucoDetector()
        self.board_warper = BoardWarper()
        self.piece_detector = PieceDetector()
        
        # WebSocket client
        if use_mock_ws:
            self.ws_client = MockWebSocketClient()
        else:
            self.ws_client = WebSocketClient()
        
        # State tracking
        self.last_pieces: dict = {}
        self.last_fen: str = ""
        self.frames_processed: int = 0
        self.detections_sent: int = 0
        
        print("[VisionService] Initialized")
        print(f"  - Debug mode: {self.debug}")
        print(f"  - Model path: {config.model_path}")
        print(f"  - Model loaded: {self.piece_detector.is_loaded()}")
    
    async def start(self):
        """Start the vision service"""
        print("[VisionService] Starting...")
        
        # Open camera
        if not self.camera.open():
            print("[VisionService] ERROR: Failed to open camera")
            return False
        
        # Connect to WebSocket
        asyncio.create_task(self.ws_client.run_with_reconnect())
        
        # Wait a bit for connection
        await asyncio.sleep(1)
        
        self.running = True
        print("[VisionService] Running - Press Ctrl+C to stop")
        
        # Main processing loop
        await self._process_loop()
        
        return True
    
    async def stop(self):
        """Stop the vision service"""
        print("[VisionService] Stopping...")
        self.running = False
        
        self.camera.close()
        await self.ws_client.disconnect()
        
        print(f"[VisionService] Stopped")
        print(f"  - Frames processed: {self.frames_processed}")
        print(f"  - Detections sent: {self.detections_sent}")
    
    async def _process_loop(self):
        """Main processing loop"""
        import cv2
        
        while self.running:
            try:
                # Capture frame
                frame = self.camera.read()
                if frame is None:
                    await asyncio.sleep(0.1)
                    continue
                
                self.frames_processed += 1
                
                # Detect ArUco markers
                aruco_result = self.aruco_detector.detect(frame.image)
                
                if not aruco_result.success:
                    if self.debug:
                        debug_frame = self.aruco_detector.draw_markers(frame.image, aruco_result)
                        cv2.imshow("Vision Service", debug_frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            self.running = False
                    await asyncio.sleep(config.process_interval)
                    continue
                
                # Warp board
                warped = self.board_warper.warp(frame.image, aruco_result.all_corners)
                
                if warped is None:
                    await asyncio.sleep(config.process_interval)
                    continue
                
                # Detect pieces
                pieces = self.piece_detector.detect(warped)
                
                # Generate FEN
                fen = generate_fen(pieces)
                
                # Compare with previous position
                comparison = compare_positions(self.last_pieces, pieces)
                
                # Send update if position changed
                if comparison['changed']:
                    update = BoardUpdate(
                        fen=fen,
                        confidence=0.9 if self.piece_detector.is_loaded() else 0.5,
                        markers_visible=aruco_result.markers_visible,
                        timestamp=frame.timestamp,
                        possible_move=comparison['possible_move']
                    )
                    
                    await self.ws_client.send_board_update(update)
                    self.detections_sent += 1
                    self.last_pieces = pieces.copy()
                    self.last_fen = fen
                    
                    if comparison['possible_move']:
                        print(f"[VisionService] Move detected: {comparison['possible_move']}")
                
                # Debug visualization
                if self.debug:
                    debug_frame = self._create_debug_view(frame.image, aruco_result, warped, pieces)
                    cv2.imshow("Vision Service", debug_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self.running = False
                
                # Rate limiting
                await asyncio.sleep(config.process_interval)
                
            except Exception as e:
                print(f"[VisionService] Processing error: {e}")
                await asyncio.sleep(1)
        
        if self.debug:
            cv2.destroyAllWindows()
    
    def _create_debug_view(self, frame, aruco_result, warped, pieces) -> 'np.ndarray':
        """Create debug visualization"""
        import cv2
        import numpy as np
        
        # Draw ArUco markers on original frame
        annotated_frame = self.aruco_detector.draw_markers(frame, aruco_result)
        
        # Resize for display
        display_height = 480
        scale = display_height / annotated_frame.shape[0]
        frame_display = cv2.resize(annotated_frame, None, fx=scale, fy=scale)
        
        # Resize warped board
        warped_display = cv2.resize(warped, (display_height, display_height))
        
        # Draw grid and pieces on warped
        warped_display = self.board_warper.draw_grid(warped_display)
        
        # Add piece labels
        square_size = display_height // 8
        for square, piece in pieces.items():
            file_idx = ord(square[0]) - ord('a')
            rank_idx = int(square[1]) - 1
            x = file_idx * square_size + square_size // 2 - 10
            y = (7 - rank_idx) * square_size + square_size // 2 + 10
            color = (0, 0, 255) if piece.islower() else (255, 0, 0)
            cv2.putText(warped_display, piece, (x, y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        # Combine views
        combined = np.hstack([frame_display, warped_display])
        
        # Add FEN display
        fen = generate_fen(pieces)
        cv2.putText(combined, f"FEN: {fen[:50]}...", (10, combined.shape[0] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return combined


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="XADRAS Vision Service")
    parser.add_argument("--debug", action="store_true", help="Enable debug visualization")
    parser.add_argument("--test", action="store_true", help="Run with mock WebSocket (no backend)")
    args = parser.parse_args()
    
    # Create service
    service = VisionService(debug=args.debug, use_mock_ws=args.test)
    
    # Handle shutdown
    def signal_handler(sig, frame):
        print("\n[Main] Received shutdown signal")
        service.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start service
    try:
        await service.start()
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
