"""
XADRAS Vision Service - FEN Generator
Convert detected piece positions to FEN string
"""

from typing import Dict, Optional, List, Any


def generate_fen(pieces: Dict[str, str], active_color: str = 'w') -> str:
    """
    Generate FEN string from piece positions.
    
    Args:
        pieces: Dictionary mapping square names to piece symbols
                e.g., {'e1': 'K', 'e8': 'k', 'd1': 'Q', ...}
        active_color: 'w' for white to move, 'b' for black
        
    Returns:
        FEN string (only the piece placement part, plus basic game state)
        e.g., "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    """
    # Build board representation
    board: List[List[Optional[str]]] = [[None for _ in range(8)] for _ in range(8)]
    
    for square, piece in pieces.items():
        if len(square) != 2:
            continue
        
        file_letter = square[0].lower()
        rank_char = square[1]
        
        if file_letter not in 'abcdefgh' or rank_char not in '12345678':
            continue
        
        file_idx = ord(file_letter) - ord('a')  # 0-7
        rank_idx = int(rank_char) - 1  # 0-7
        
        board[rank_idx][file_idx] = piece
    
    # Generate FEN piece placement (from rank 8 to rank 1)
    fen_rows = []
    
    for rank_idx in range(7, -1, -1):  # 8 down to 1
        row = board[rank_idx]
        fen_row = ''
        empty_count = 0
        
        for file_idx in range(8):
            piece = row[file_idx]
            
            if piece is None:
                empty_count += 1
            else:
                if empty_count > 0:
                    fen_row += str(empty_count)
                    empty_count = 0
                fen_row += piece
        
        if empty_count > 0:
            fen_row += str(empty_count)
        
        fen_rows.append(fen_row)
    
    # Combine rows with /
    piece_placement = '/'.join(fen_rows)
    
    # Add basic game state (we can't determine castling/en passant from vision alone)
    # Format: piece_placement active_color castling en_passant halfmove fullmove
    # We use defaults since vision can't determine these
    fen = f"{piece_placement} {active_color} KQkq - 0 1"
    
    return fen


def fen_to_pieces(fen: str) -> Dict[str, str]:
    """
    Convert FEN string back to piece positions dictionary.
    
    Args:
        fen: FEN string
        
    Returns:
        Dictionary mapping square names to piece symbols
    """
    pieces = {}
    
    # Get piece placement (first part of FEN)
    piece_placement = fen.split()[0]
    
    ranks = piece_placement.split('/')
    
    for rank_idx, rank_str in enumerate(ranks):
        file_idx = 0
        actual_rank = 8 - rank_idx  # Convert to 1-8 (FEN starts from rank 8)
        
        for char in rank_str:
            if char.isdigit():
                file_idx += int(char)
            else:
                file_letter = chr(ord('a') + file_idx)
                square = f"{file_letter}{actual_rank}"
                pieces[square] = char
                file_idx += 1
    
    return pieces


def compare_positions(old_pieces: Dict[str, str], new_pieces: Dict[str, str]) -> Dict[str, Any]:
    """
    Compare two positions to find changes.
    
    Returns:
        Dictionary with:
        - 'changed': bool - whether position changed
        - 'removed': list of (square, piece) - pieces removed from squares
        - 'added': list of (square, piece) - pieces added to squares
        - 'possible_move': Optional move in UCI format if a simple move detected
    """
    removed = []
    added = []
    
    all_squares = set(old_pieces.keys()) | set(new_pieces.keys())
    
    for square in all_squares:
        old_piece = old_pieces.get(square)
        new_piece = new_pieces.get(square)
        
        if old_piece != new_piece:
            if old_piece is not None:
                removed.append((square, old_piece))
            if new_piece is not None:
                added.append((square, new_piece))
    
    changed = len(removed) > 0 or len(added) > 0
    
    # Try to detect a simple move (one piece removed, same piece added elsewhere)
    possible_move = None
    if len(removed) == 1 and len(added) == 1:
        from_sq, from_piece = removed[0]
        to_sq, to_piece = added[0]
        
        # Same piece moved (ignoring promotion for now)
        if from_piece.lower() == to_piece.lower():
            possible_move = f"{from_sq}{to_sq}"
    
    # Handle capture (one piece removed from one square, replaced on another)
    elif len(removed) == 2 and len(added) == 1:
        to_sq, to_piece = added[0]
        for from_sq, from_piece in removed:
            if from_sq != to_sq and from_piece == to_piece:
                possible_move = f"{from_sq}{to_sq}"
                break
    
    return {
        'changed': changed,
        'removed': removed,
        'added': added,
        'possible_move': possible_move
    }


# Standard starting position for reference
STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
EMPTY_FEN = "8/8/8/8/8/8/8/8 w - - 0 1"
