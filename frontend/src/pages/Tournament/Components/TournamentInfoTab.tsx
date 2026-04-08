import React from 'react';

export interface TournamentInfoTabProps {
    participants: any[];
}

const TournamentInfoTab: React.FC<TournamentInfoTabProps> = ({ participants }) => {
    return (
        <div className="info-tab">
            <div className="info-section glass-card">
                <h3>Lista Oficial de Participantes ({participants.length})</h3>
                {participants.length > 0 ? (
                    <div className="participants-grid">
                        {participants.map((participant: any, index: number) => (
                            <div key={participant.id || index} className="participant-card">
                                <div className="participant-avatar">
                                    {participant.username ? participant.username.charAt(0).toUpperCase() : '?'}
                                </div>
                                <div className="participant-info">
                                    <div className="participant-name">{participant.username || participant.name}</div>
                                    <div className="participant-elo">ELO: {participant.elo_rating || participant.initial_rating || 1200}</div>
                                </div>
                                <div className="participant-seed">
                                    #{index + 1}
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="empty-state">
                        <div className="empty-icon">👥</div>
                        <p>Ainda não há participantes inscritos neste torneio.</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default TournamentInfoTab;