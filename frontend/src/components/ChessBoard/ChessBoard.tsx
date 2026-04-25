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
  bestMove?: string | null;
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
  bestMove = null,
}) => {
  const [game, setGame] = useState<Chess>(() => new Chess());
  const [selectedSquare, setSelectedSquare] = useState<string | null>(null);
  const [validMoves, setValidMoves] = useState<string[]>([]);
  const [highlightedSquares, setHighlightedSquares] = useState<string[]>([]);
  const [kingInCheck, setKingInCheck] = useState<string | null>(null);
  const [promotionMove, setPromotionMove] = useState<{ from: string, to: string } | null>(null);

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

  const confirmMove = (from: string, to: string, promotion?: string) => {
    try {
      const moveObj = game.move({
        from: from as Square,
        to: to as Square,
        promotion: promotion || 'q',
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
    setPromotionMove(null);
    setSelectedSquare(null);
    setValidMoves([]);
  };

  const attemptMove = (from: string, to: string) => {
    const piece = game.get(from as Square);
    if (piece && piece.type === 'p' && (to[1] === '8' || to[1] === '1')) {
      const moves = game.moves({ square: from as Square, verbose: true }) as Move[];
      const isValidPromotion = moves.some(m => m.to === to && m.promotion);
      if (isValidPromotion) {
        setPromotionMove({ from, to });
        return;
      }
    }
    confirmMove(from, to);
  };

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

    if (validMoves.includes(square)) {
      attemptMove(selectedSquare, square);
    } else {
      const piece = game.get(square as Square);
      if (piece && piece.color === game.turn()) {
        setSelectedSquare(square);
        const moves = game.moves({
          square: square as Square,
          verbose: true
        }) as Move[];
        setValidMoves(moves.map(move => move.to));
      } else {
        setSelectedSquare(null);
        setValidMoves([]);
      }
    }
  };

  const handleDragStart = (e: React.DragEvent<HTMLDivElement>, squareId: string) => {
    if (!interactive) {
      e.preventDefault();
      return;
    }
    const piece = game.get(squareId as Square);
    if (!piece || piece.color !== game.turn()) {
      e.preventDefault();
      return;
    }

    e.dataTransfer.setData('text/plain', squareId);
    e.dataTransfer.effectAllowed = 'move';

    const target = e.currentTarget;
    const img = target.querySelector('img');
    if (img) {
      e.dataTransfer.setDragImage(img, img.clientWidth / 2, img.clientHeight / 2);
    }

    // Apenas calculamos os movimentos válidos para mostrar os indicadores (bolinhas)
    // Sem selecionar a casa (evita o fundo amarelo)
    const moves = game.moves({
      square: squareId as Square,
      verbose: true
    }) as Move[];
    setValidMoves(moves.map(move => move.to));
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e: React.DragEvent, targetSquare: string) => {
    e.preventDefault();
    if (!interactive) return;

    const sourceSquare = e.dataTransfer.getData('text/plain');
    if (!sourceSquare || sourceSquare === targetSquare) {
      return;
    }

    attemptMove(sourceSquare, targetSquare);
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
        let square: Piece | undefined | null = game.get(squareId);

        if (promotionMove) {
          if (squareId === promotionMove.from) {
            square = undefined;
          } else if (squareId === promotionMove.to) {
            square = game.get(promotionMove.from as Square);
          }
        }

        const fileIndex = files.indexOf(file as typeof files[0]);
        const isWhite = (fileIndex + rank) % 2 === 0;
        const isSelected = selectedSquare === squareId;
        const isValidMove = validMoves.includes(squareId);
        const isHighlighted = highlightedSquares.includes(squareId);
        const isKingInCheck = kingInCheck === squareId;
        const hasPiece = !!square;

        const isBestMoveFrom = bestMove && bestMove.substring(0, 2) === squareId;
        const isBestMoveTo = bestMove && bestMove.substring(2, 4) === squareId;

        const isLeftEdge = file === displayFiles[0];
        const isBottomEdge = rank === displayRanks[displayRanks.length - 1];

        const squareClass = [
          'square',
          isWhite ? 'white' : 'black',
          isSelected ? 'selected' : '',
          isValidMove ? 'valid-move' : '',
          hasPiece && isValidMove ? 'has-piece' : '',
          isHighlighted ? 'highlight' : '',
          isKingInCheck ? 'king-in-check' : '',
          (isBestMoveFrom || isBestMoveTo) ? 'best-move-hint' : ''
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
            onDragOver={handleDragOver}
            onDrop={(e) => handleDrop(e, squareId)}
            draggable={interactive && hasPiece}
            onDragStart={(e) => handleDragStart(e, squareId)}
            style={{
              cursor: interactive ? 'pointer' : 'default',
              position: 'relative'
            }}
          >
            {isLeftEdge && <div className="coordinate rank">{rank}</div>}
            {isBottomEdge && <div className="coordinate file">{file}</div>}

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
  }, [game, orientation, selectedSquare, validMoves, highlightedSquares, kingInCheck, interactive, bestMove, promotionMove]);

  return (
    <div className="chess-board" style={{ position: 'relative' }}>
      {renderBoard()}

      {promotionMove && (
        <div className="promotion-modal-overlay">
          <div className="promotion-modal" onClick={e => e.stopPropagation()}>
            <h3 style={{ margin: '0 0 1.5rem', textAlign: 'center', color: 'var(--fg)', fontSize: '1.25rem' }}>Promover Peão</h3>
            <div className="promotion-options">
              {['q', 'r', 'b', 'n'].map((p) => (
                <div
                  key={p}
                  className="promotion-option"
                  onClick={() => confirmMove(promotionMove.from, promotionMove.to, p)}
                >
                  <img src={`/pieces/${game.turn()}${p.toUpperCase()}.svg`} alt={p} draggable={false} />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChessBoard;