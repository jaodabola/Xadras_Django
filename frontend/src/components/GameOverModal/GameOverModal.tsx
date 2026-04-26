import React from 'react';
import './GameOverModal.css';

interface GameOverModalProps {
  message: string;
  isSpectator: boolean;
  gameType: 'online' | 'local' | 'tournament';
  tournamentId?: string | null;
  onNewGame?: () => void;
  onGoHome?: () => void;
  onBackToTournament?: () => void;
}

const GameOverModal: React.FC<GameOverModalProps> = ({
  message,
  isSpectator,
  gameType,
  tournamentId,
  onNewGame,
  onGoHome,
  onBackToTournament
}) => {
  return (
    <div className="game-over-modal-overlay">
      <div className="game-over-modal">
        <h2>{message}</h2>
        {isSpectator && (
          <p className="game-over-spectator-note">A assistir como espectador</p>
        )}
        <div className="game-over-actions">
          {gameType === 'tournament' && (
            <button
              className="btn btn-primary"
              onClick={onBackToTournament}
            >
              ♟ Voltar ao Torneio
            </button>
          )}

          {gameType === 'online' && (
            <>
              <button className="btn btn-primary" onClick={onNewGame}>
                Novo Jogo
              </button>
              <button className="btn btn-secondary" onClick={onGoHome}>
                Página Inicial
              </button>
            </>
          )}

          {gameType === 'local' && (
            <>
              <button className="btn btn-primary" onClick={onNewGame}>
                Recomeçar Jogo
              </button>
              
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default GameOverModal;
