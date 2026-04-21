import React, { useEffect, useRef } from 'react';
import './MoveHistory.css';
import { MovePair } from '../../types';

interface MoveHistoryProps {
  moveHistory: MovePair[];
  currentMoveIndex: number;
  onMoveClick?: (moveIndex: number) => void;
}

const MoveHistory: React.FC<MoveHistoryProps> = ({
  moveHistory,
  currentMoveIndex,
  onMoveClick,
}) => {
  const movesContainerRef = useRef<HTMLDivElement>(null);

  const handleMoveClick = (moveIndex: number) => {
    if (onMoveClick) {
      onMoveClick(moveIndex);
    }
  };

  useEffect(() => {
    // Scroll apenas dentro do contentor, sem mover a página
    if (movesContainerRef.current) {
      movesContainerRef.current.scrollTop = movesContainerRef.current.scrollHeight;
    }
  }, [moveHistory]);

  return (
    <div className="move-history">
      <h3>Histórico de Jogadas</h3>
      <div className="moves-container" ref={movesContainerRef}>
        {moveHistory.map((movePair, index) => (
          <div key={index} className="move-pair">
            <span className="move-number">{index + 1}.</span>
            <button
              className={`move white ${currentMoveIndex === index * 2 ? 'current-move' : ''}`}
              onClick={() => handleMoveClick(index * 2)}
            >
              {movePair.white}
            </button>
            {movePair.black && (
              <button
                className={`move black ${currentMoveIndex === index * 2 + 1 ? 'current-move' : ''}`}
                onClick={() => handleMoveClick(index * 2 + 1)}
              >
                {movePair.black}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default MoveHistory;
