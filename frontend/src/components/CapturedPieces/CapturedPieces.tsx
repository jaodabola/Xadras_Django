import React, { ReactNode } from 'react';
import './CapturedPieces.css';
import { CapturedPieces as CapturedPiecesType } from '../../types';

interface CapturedPiecesProps {
  capturedPieces: CapturedPiecesType;
  getPieceSymbol: (piece: { type: string; color: string }) => ReactNode;
  calculateMaterial: (pieces: string[]) => number;
  isSidebar?: boolean;
  className?: string;
}

const CapturedPieces: React.FC<CapturedPiecesProps> = ({
  capturedPieces,
  getPieceSymbol,
  calculateMaterial,
  isSidebar = false,
  className = '',
}) => {
  const renderCapturedPieces = (color: 'white' | 'black') => {
    const pieces = capturedPieces[color];
    if (!pieces || pieces.length === 0) return null;

    // Grouping count
    const countMap: Record<string, number> = {};
    pieces.forEach(p => {
      countMap[p] = (countMap[p] || 0) + 1;
    });

    return (
      <div className={`captured-pieces ${color}`}>
        <div className="captured-pieces-header">
          <h4>{color === 'white' ? 'Brancas' : 'Pretas'}</h4>
          <span className="material-count">+{calculateMaterial(pieces)}</span>
        </div>
        <div className="captured-pieces-list">
          {Object.entries(countMap).map(([piece, count]) => (
            <div key={`${color}-${piece}`} className="captured-piece-wrapper">
              <span className={`captured-piece ${color}`}>
                {getPieceSymbol({ type: piece, color: color === 'white' ? 'b' : 'w' })}
              </span>
              {count > 1 && <span className="piece-multiplier">x{count}</span>}
            </div>
          ))}
        </div>
      </div>
    );
  };

  if (isSidebar) {
    return (
      <div className={`captured-pieces-sidebar ${className}`}>
        <h3>Peças Capturadas</h3>
        {renderCapturedPieces('black')}
        {renderCapturedPieces('white')}
      </div>
    );
  }

  return (
    <div className={`captured-pieces-container ${className}`}>
      <div className="captured-pieces-row">
        {renderCapturedPieces('black')}
      </div>
      <div className="captured-pieces-row">
        {renderCapturedPieces('white')}
      </div>
    </div>
  );
};

export default CapturedPieces;
