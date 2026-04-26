import React from 'react';
import { useNavigate } from 'react-router-dom';

export interface TournamentPairingsTabProps {
    pairings: any[];
    isOrganizer: boolean;
    status: string;
    currentUserId?: number | null;
}

const RESULT_LABELS: Record<string, string> = {
    WHITE_WIN: 'Vitória das Brancas',
    BLACK_WIN: 'Vitória das Pretas',
    DRAW: 'Empate',
    BYE: 'Folga (BYE)',
    FORFEIT_WHITE: 'Desistência das Brancas',
    FORFEIT_BLACK: 'Desistência das Pretas',
};

const TournamentPairingsTab: React.FC<TournamentPairingsTabProps> = ({
    pairings,
    isOrganizer,
    status,
    currentUserId,
}) => {
    const navigate = useNavigate();

    return (
        <div className="pairings-tab glass-card">
            {pairings.length > 0 ? (
                <div className="pairings-list">
                    <h3>Jogos da Ronda</h3>
                    {pairings.map((pairing) => {
                        const isPlayer =
                            currentUserId != null &&
                            !pairing.result &&
                            (pairing.white_player?.id === currentUserId ||
                                pairing.black_player?.id === currentUserId);
                                
                        const showButton = 
                            !pairing.bye_player &&
                            (isPlayer ? (!pairing.result && pairing.game_status !== 'FINISHED') : pairing.game_status === 'IN_PROGRESS');

                        const getGameStatusBadge = () => {
                            if (pairing.result || pairing.game_status === 'FINISHED') return <span className="status-badge status-completed">Terminado</span>;
                            if (pairing.game_status === 'IN_PROGRESS') return <span className="status-badge status-in-progress">Em Curso</span>;
                            if (pairing.game_status === 'PENDING') return <span className="status-badge status-pending">Pendente</span>;
                            return null;
                        };

                        return (
                            <div key={pairing.id} className="pairing-card">
                                <div className="pairing-header">
                                    <span className="round-badge">Ronda {pairing.round_number}</span>
                                    {getGameStatusBadge()}
                                    <div className="pairing-header-right">
                                        {pairing.physical_board_id && (
                                            <span className="board-badge">📹 Mesa {pairing.physical_board_id}</span>
                                        )}
                                        {/* Botão Entrar / Assistir */}
                                        {showButton && (
                                            <button
                                                className={`btn-pairing-enter ${
                                                    isPlayer ? 'btn-pairing-player' : 'btn-pairing-watch'
                                                }`}
                                                onClick={() => navigate(`/game/${pairing.game}`)}
                                                title={isPlayer ? 'Entrar na partida' : 'Assistir à partida'}
                                            >
                                                {isPlayer ? '♟ Entrar na Partida' : '👁 Assistir'}
                                            </button>
                                        )}
                                    </div>
                                </div>
                                <div className="pairing-players">
                                    <div className="player white-player">
                                        <span className="player-indicator white"></span>
                                        <span className="player-name">
                                            {pairing.white_player?.username ?? '—'}
                                        </span>
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
                                        {RESULT_LABELS[pairing.result] ?? pairing.result}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            ) : (
                <div className="empty-state">
                    <div className="empty-icon">🎯</div>
                    <p>Ainda não existem rondas criadas.</p>
                    {isOrganizer && status === 'REGISTRATION' && (
                        <p className="help-text">Utiliza o botão "Iniciar Torneio" acima para começar!</p>
                    )}
                </div>
            )}
        </div>
    );
};

export default TournamentPairingsTab;