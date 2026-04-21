import React from 'react';

export interface TournamentStandingsTabProps {
    standings: any[];
}

const TournamentStandingsTab: React.FC<TournamentStandingsTabProps> = ({ standings }) => {
    return (
        <div className="standings-tab glass-card">
            {standings.length > 0 ? (
                <div className="standings-table-wrap">
                    <table className="standings-table">
                        <thead>
                            <tr>
                                <th>Posição</th>
                                <th>Jogador</th>
                                <th>Pontos</th>
                                <th>Jogos</th>
                                <th>V/E/D</th>
                            </tr>
                        </thead>
                        <tbody>
                            {standings.map((standing, index) => (
                                <tr key={standing.player_id || index}>
                                    <td className="rank-cell">
                                        <span className={`rank-badge ${index < 3 ? 'top-3' : ''}`}>
                                            {index + 1}
                                        </span>
                                    </td>
                                    <td className="player-cell">{standing.player_name || standing.username}</td>
                                    <td className="score-cell"><strong>{standing.score}</strong></td>
                                    <td>{standing.games_played}</td>
                                    <td>{standing.wins} / {standing.draws} / {standing.losses}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <div className="empty-state">
                    <img src="/logo/LOGO_TOURNAMENT.png" alt="Torneios" className="empty-icon-img" />
                    <p>A classificação final ou parcial ainda não está disponível.</p>
                    <p className="help-text">Aguardando a conclusão da primeira ronda.</p>
                </div>
            )}
        </div>
    );
};

export default TournamentStandingsTab;