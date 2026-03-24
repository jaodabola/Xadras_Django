import React, { useEffect, useState, useCallback } from 'react';
import { Chess, Square, Piece, Move } from 'chess.js';
import './ChessBoard.css';

type BoardOrientation = 'white' | 'black';

interface ChessBoardProps {
  position: string;
  orientation?: BoardOrientation;
  onMove: (move: { from: string; to: string; promotion?: string }) => void;
  lastMove: string | null;
  interactive: boolean;
  width?: number;
}

const files = ["a", "b", "c", "d", "e", "f", "g", "h"] as const;
const ranks = [8, 7, 6, 5, 4, 3, 2, 1] as const;

const ChessBoard: React.FC<ChessBoardProps> = ({
  position = 'start',
  orientation = 'white',
  onMove,
  lastMove,
  interactive = true,
  width = 500,
}) => {
  const [game, setGame] = useState<Chess>(() => new Chess());
  const [selectedSquare, setSelectedSquare] = useState<string | null>(null);
  const [validMoves, setValidMoves] = useState<string[]>([]);
  const [highlightedSquares, setHighlightedSquares] = useState<string[]>([]);
  const [kingInCheck, setKingInCheck] = useState<string | null>(null);

  // Update game state when position prop changes
  useEffect(() => {
    try {
      const newGame = new Chess();
      if (position !== 'start') {
        try {
          newGame.load(position);
        } catch (e) {
          console.error('Failed to load FEN position:', e);
          return;
        }
      }
      setGame(newGame);

      const inCheck = newGame.isCheck();
      if (inCheck) {
        const board = newGame.board();
        const kingPos = board.flat().find((sq): sq is { square: Square } & Piece =>
          sq !== null && sq.type === 'k' && sq.color === newGame.turn()
        );
        setKingInCheck(kingPos?.square || null);
      } else {
        setKingInCheck(null);
      }
    } catch (err) {
      console.error('Error initializing chess game:', err);
    }
  }, [position]);

  // Highlight last move
  useEffect(() => {
    if (lastMove) {
      setHighlightedSquares([lastMove.substring(0, 2), lastMove.substring(2, 4)]);
    } else {
      setHighlightedSquares([]);
    }
  }, [lastMove]);

  const handleSquareClick = (square: string) => {
    if (!interactive) return;

    if (!selectedSquare) {
      const piece = game.get(square as Square);
      if (piece && piece.color === game.turn()) {
        setSelectedSquare(square);
        const moves = game.moves({
          square: square as Square,
          verbose: true
        }) as Move[];
        setValidMoves(moves.map(move => move.to));
        return;
      }
      return;
    }

    if (selectedSquare === square) {
      setSelectedSquare(null);
      setValidMoves([]);
      return;
    }

    try {
      const move = {
        from: selectedSquare,
        to: square,
        promotion: 'q',
      };

      const moveObj = game.move({
        from: move.from as Square,
        to: move.to as Square,
        promotion: 'q',
      });

      if (moveObj) {
        onMove({
          from: moveObj.from,
          to: moveObj.to,
          promotion: moveObj.promotion
        });
      }
    } catch (e) {
      console.log('Invalid move');
    }

    setSelectedSquare(null);
    setValidMoves([]);
  };

  // Retorna o caminho para o SVG da peça
  const getPieceSrc = (piece: Piece): string => {
    const color = piece.color; // 'w' ou 'b'
    const type = piece.type.toUpperCase(); // 'P','N','B','R','Q','K'
    return `/pieces/${color}${type}.svg`;
  };

  const renderBoard = useCallback(() => {
    // FIXED: White should be at the bottom when orientation is 'white'
    // Ranks should go from 8 to 1 (top to bottom) for white orientation
    const displayRanks = orientation === 'white' ? [...ranks] : [...ranks].reverse();
    const displayFiles = orientation === 'white' ? [...files] : [...files].reverse();

    return displayRanks.flatMap((rank) =>
      displayFiles.map((file) => {
        const squareId = `${file}${rank}` as Square;
        const square = game.get(squareId);
        const fileIndex = files.indexOf(file as typeof files[0]);
        const isWhite = (fileIndex + rank) % 2 === 0;
        const isSelected = selectedSquare === squareId;
        const isValidMove = validMoves.includes(squareId);
        const isHighlighted = highlightedSquares.includes(squareId);
        const isKingInCheck = kingInCheck === squareId;
        const hasPiece = square !== null;

        const squareClass = [
          'square',
          isWhite ? 'white' : 'black',
          isSelected ? 'selected' : '',
          isValidMove ? 'valid-move' : '',
          hasPiece && isValidMove ? 'has-piece' : '',
          isHighlighted ? 'highlight' : '',
          isKingInCheck ? 'king-in-check' : ''
        ].filter(Boolean).join(' ');

        const pieceClass = [
          'piece',
          square ? (square.color === 'w' ? 'white' : 'black') : ''
        ].filter(Boolean).join(' ');

        return (
          <div
            key={squareId}
            id={squareId}
            className={squareClass}
            onClick={() => handleSquareClick(squareId)}
            style={{
              cursor: interactive ? 'pointer' : 'default'
            }}
          >
            {square && (
              <div
                className={pieceClass}
                data-color={square.color}
                data-piece={square.type}
              >
                <img
                  src={getPieceSrc(square)}
                  alt={`${square.color === 'w' ? 'white' : 'black'} ${square.type}`}
                  draggable={false}
                  style={{ width: '85%', height: '85%', objectFit: 'contain', display: 'block' }}
                />
              </div>
            )}
            {isValidMove && !hasPiece && <div className="move-indicator" />}
            {isValidMove && hasPiece && <div className="capture-indicator" />}
          </div>
        );
      })
    );
  }, [game, orientation, selectedSquare, validMoves, highlightedSquares, kingInCheck, interactive]);

  return (
    <div className="chess-board">
      {renderBoard()}
    </div>
  );
};

export default ChessBoard;