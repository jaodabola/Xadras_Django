import React from 'react';

export interface TournamentPairingsTabProps {
  pairings: any[];
  isOrganizer: boolean;
  status: string;
}

const TournamentPairingsTab: React.FC<TournamentPairingsTabProps> = ({ pairings, isOrganizer, status }) => {
  return (
    <div className="pairings-tab glass-card">
      {pairings.length > 0 ? (
        <div className="pairings-list">
          <h3>Jogos da Ronda</h3>
          {pairings.map((pairing) => (
            <div key={pairing.id} className="pairing-card">
              <div className="pairing-header">
                <span className="round-badge">Ronda {pairing.round_number}</span>
                {pairing.physical_board_id && (
                  <span className="board-badge">Mesa: 📹 {pairing.physical_board_id}</span>
                )}
              </div>
              <div className="pairing-players">
                <div className="player white-player">
                  <span className="player-indicator white"></span>
                  <span className="player-name">{pairing.white_player.username}</span>
                </div>
                <div className="vs-divider">VS</div>
                {pairing.black_player ? (
                  <div className="player black-player">
                    <span className="player-indicator black"></span>
                    <span className="player-name">{pairing.black_player.username}</span>
                  </div>
                ) : pairing.bye_player ? (
                  <div className="player bye-player">
                    <span className="bye-badge">Folga (BYE)</span>
                  </div>
                ) : null}
              </div>
              {pairing.result && (
                <div className="pairing-result">
                  Resultado: <strong>{pairing.result}</strong>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <div className="empty-icon">🎯</div>
          <p>Ainda não existem rondas criadas.</p>
          {isOrganizer && status === 'REGISTRATION' && (
            <p className="help-text">Utiliza o botão "Gerar Emparelhamentos" acima para iniciar!</p>
          )}
        </div>
      )}
    </div>
  );
};

export default TournamentPairingsTab;
