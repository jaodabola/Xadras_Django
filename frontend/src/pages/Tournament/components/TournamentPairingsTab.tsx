import React from 'react';
import { useNavigate } from 'react-router-dom';

export interface TournamentPairingsTabProps {
  pairings: any[];
  isOrganizer: boolean;
  status: string;
  currentUserId?: number;
  organizerId?: number;
  tournamentId?: string;
}

const resultLabel: Record<string, string> = {
  WHITE_WIN: '♔ Brancas vencem',
  BLACK_WIN: '♚ Pretas vencem',
  DRAW: '½ Empate',
  BYE: '🔄 Folga',
  FORFEIT_WHITE: '⚑ Derrota Brancas (desistência)',
  FORFEIT_BLACK: '⚑ Derrota Pretas (desistência)',
};

const TournamentPairingsTab: React.FC<TournamentPairingsTabProps> = ({
  pairings,
  isOrganizer,
  status,
  organizerId,
  tournamentId,
}) => {
  const navigate = useNavigate();

  const goToGame = (gameId: string) => {
    const params = new URLSearchParams();
    if (organizerId) params.set('organizerId', String(organizerId));
    if (tournamentId) params.set('tournamentId', tournamentId);
    navigate(`/game/${gameId}?${params.toString()}`);
  };

  if (pairings.length === 0) {
    return (
      <div className="pairings-tab glass-card">
        <div className="empty-state">
          <div className="empty-icon">🎯</div>
          <p>Ainda não existem rondas criadas.</p>
          {isOrganizer && status === 'REGISTRATION' && (
            <p className="help-text">Utiliza o botão "Iniciar Torneio" acima para começar!</p>
          )}
        </div>
      </div>
    );
  }

  // Agrupar pairings por ronda
  const roundMap: Record<number, any[]> = {};
  for (const p of pairings) {
    const rn = p.round_number ?? 0;
    if (!roundMap[rn]) roundMap[rn] = [];
    roundMap[rn].push(p);
  }
  const sortedRounds = Object.keys(roundMap)
    .map(Number)
    .sort((a, b) => b - a); // Ronda mais recente primeiro

  return (
    <div className="pairings-tab glass-card">
      {sortedRounds.map(roundNumber => (
        <div key={roundNumber} className="round-section">
          <div className="round-header">
            <h3>Ronda {roundNumber}</h3>
          </div>
          <div className="pairings-list">
            {roundMap[roundNumber].map((pairing: any) => {
              const hasResult = pairing.result !== null && pairing.result !== undefined;
              const gameId = pairing.game_id;

              return (
                <div
                  key={pairing.id}
                  className={`pairing-card ${hasResult ? 'pairing-card--finished' : ''}`}
                >
                  {pairing.physical_board_id && (
                    <div className="pairing-board-badge">
                      📷 Código: <strong>{pairing.physical_board_id}</strong>
                    </div>
                  )}

                  <div className="pairing-players">
                    {pairing.is_bye ? (
                      <div className="bye-pairing">
                        <span className="player-name">{pairing.bye_player?.username || '—'}</span>
                        <span className="bye-badge">🔄 Folga (BYE)</span>
                      </div>
                    ) : (
                      <>
                        <div className={`player white-player ${hasResult && pairing.result === 'WHITE_WIN' ? 'player--winner' : ''}`}>
                          <span className="player-indicator white"></span>
                          <span className="player-name">{pairing.white_player?.username || '—'}</span>
                        </div>
                        <div className="vs-divider">VS</div>
                        <div className={`player black-player ${hasResult && pairing.result === 'BLACK_WIN' ? 'player--winner' : ''}`}>
                          <span className="player-indicator black"></span>
                          <span className="player-name">{pairing.black_player?.username || '—'}</span>
                        </div>
                      </>
                    )}
                  </div>

                  <div className="pairing-footer">
                    {hasResult ? (
                      <span className="pairing-result-badge">
                        {resultLabel[pairing.result] || pairing.result}
                      </span>
                    ) : (
                      <span className="pairing-status-badge">Em curso</span>
                    )}

                    {/* Botão único para assistir/jogar */}
                    {gameId && !pairing.is_bye && (
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => goToGame(gameId)}
                      >
                        👁 Assistir
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
};

export default TournamentPairingsTab;
