import { Chess, Square } from 'chess.js';

export interface MovePair {
  white: string;
  black?: string;
}

export interface CapturedPieces {
  white: string[];
  black: string[];
}

export interface GameState {
  fen: string;
  moveHistory: MovePair[];
  capturedPieces: CapturedPieces;
  inCheck: string | null;
  currentMoveIndex: number;
}

export type PieceSymbol = 'p' | 'n' | 'b' | 'r' | 'q' | 'k';
export type Color = 'w' | 'b';

export interface Piece {
  type: PieceSymbol;
  color: Color;
  square: Square;
}

export interface BoardSquare {
  square: Square;
  piece: Piece | null;
  isHighlighted: boolean;
  isSelected: boolean;
  isBlack: boolean;
}

export interface MoveHistoryProps {
  moveHistory: MovePair[];
  currentMoveIndex: number;
  onMoveClick?: (moveIndex: number) => void;
}

export interface ChessBoardProps {
  game: Chess;
  selectedSquare: string | null;
  highlighted: string[];
  kingInCheck: string | null;
  isBoardFlipped: boolean;
  onSquareClick: (square: string) => void;
  getPieceSymbol: (piece: { type: string; color: string }) => string;
}

export interface GameControlsProps {
  autoFlipBoard: boolean;
  currentMoveIndex: number;
  onToggleAutoFlip: () => void;
  onUndo: () => void;
  onNewGame: () => void;
  onToggleFullscreen: () => void;
  isFullscreen: boolean;
}

export interface CapturedPiecesProps {
  capturedPieces: CapturedPieces;
  getPieceSymbol: (piece: { type: string; color: string }) => string;
  calculateMaterial: (pieces: string[]) => number;
  isSidebar?: boolean;
}
