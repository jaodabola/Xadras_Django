import React from 'react';
import { FaArrowsRotate, FaRotateLeft, FaPlus, FaExpand, FaCompress, FaFlag, FaArrowLeft } from 'react-icons/fa6';
import './GameControls.css';

interface GameControlsProps {
  autoFlipBoard: boolean;
  currentMoveIndex: number;
  onToggleAutoFlip?: () => void;
  onUndo?: () => void;
  onNewGame?: () => void;
  onToggleFullscreen: () => void;
  isFullscreen: boolean;
  onResign?: () => void;
  onBackToTournament?: () => void;
}

const GameControls: React.FC<GameControlsProps> = ({
  autoFlipBoard,
  currentMoveIndex,
  onToggleAutoFlip,
  onUndo,
  onNewGame,
  onToggleFullscreen,
  isFullscreen,
  onResign,
  onBackToTournament,
}) => {
  return (
    <div className="game-controls">
      {/* Auto-flip button - only show in local games */}
      {onToggleAutoFlip && (
        <button 
          className={`control-button ${autoFlipBoard ? 'active' : ''}`}
          onClick={onToggleAutoFlip}
          title="Alternar rotação automática do tabuleiro"
        >
          <FaArrowsRotate />
        </button>
      )}
      
      {/* Undo button - only show in local games */}
      {onUndo && (
        <button 
          className="control-button" 
          onClick={onUndo}
          disabled={currentMoveIndex < 0}
          title="Desfazer última jogada"
        >
          <FaRotateLeft />
        </button>
      )}
      
      {/* New game button - only show in local games */}
      {onNewGame && (
        <button 
          className="control-button" 
          onClick={onNewGame}
          title="Nova partida"
        >
          <FaPlus />
        </button>
      )}
      {/* Botão voltar ao torneio — mesmo sítio e estilo que o Desistir */}
      {onBackToTournament && (
        <button
          className="control-button"
          onClick={onBackToTournament}
          title="Voltar ao Torneio"
        >
          <FaArrowLeft />
        </button>
      )}
      {/* Resign button - only show when provided (online games) */}
      {onResign && (
        <button 
          className="control-button" 
          onClick={onResign}
          title="Desistir da partida"
          style={{ color: '#ef4444' }}
        >
          <FaFlag />
        </button>
      )}
      
      {/* Fullscreen button - always show */}
      <button 
        className="control-button" 
        onClick={onToggleFullscreen}
        title={isFullscreen ? "Sair do ecrã inteiro" : "Ecrã inteiro"}
      >
        {isFullscreen ? <FaCompress /> : <FaExpand />}
      </button>
    </div>
  );
};

export default GameControls;
