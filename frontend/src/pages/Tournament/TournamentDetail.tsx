import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTournament } from '../../contexts/TournamentContext';
import { useAuth } from '../../contexts/AuthContext';
import LoadingSpinner from '../../components/LoadingSpinner/LoadingSpinner';
import './TournamentDetail.css';

interface Pairing {
  id: number;
  round_number: number;
  white_player: {
    id: number;
    username: string;
  };
  black_player: {
    id: number;
    username: string;
  } | null;
  bye_player: {
    id: number;
    username: string;
  } | null;
  result: string | null;
  physical_board_id: string | null;
  camera_id: number | null;
}

const TournamentDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const {
    selectedTournament,
    getTournament,
    generatePairings,
    assignBoards,
    startRound,
    getStandings,
    loading,
    error,
    clearError
  } = useTournament();

  const [pairings, setPairings] = useState<Pairing[]>([]);
  const [standings, setStandings] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<'info' | 'pairings' | 'standings'>('info');
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      loadTournamentData();
    }
  }, [id]);

  const loadTournamentData = async () => {
    if (!id) return;
    
    try {
      const tournament = await getTournament(parseInt(id));
      
      // Load pairings if tournament has started
      if (tournament.status !== 'PENDING') {
        // Pairings would be part of tournament data or separate API call
        // For now, we'll assume they're in the tournament object
        if ((tournament as any).pairings) {
          setPairings((tournament as any).pairings);
        }
      }

      // Load standings
      if (tournament.status !== 'PENDING') {
        const standingsData = await getStandings(parseInt(id));
        setStandings(standingsData);
      }
    } catch (err) {
      console.error('Error loading tournament data:', err);
    }
  };

  const handleGeneratePairings = async () => {
    if (!id) return;
    
    try {
      setActionLoading('generate_pairings');
      await generatePairings(parseInt(id));
      await loadTournamentData();
    } catch (err) {
      console.error('Error generating pairings:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleStartRound = async () => {
    if (!id) return;
    
    try {
      setActionLoading('start_round');
      await startRound(parseInt(id));
      await loadTournamentData();
    } catch (err) {
      console.error('Error starting round:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleAssignBoards = async () => {
    if (!id || !pairings.length) return;
    
    try {
      setActionLoading('assign_boards');
      
      // Create board assignments from pairings
      const assignments = pairings.map((pairing, index) => ({
        pairing_id: pairing.id,
        physical_board_id: `board_${String(index + 1).padStart(3, '0')}`,
        camera_id: index + 1
      }));

      await assignBoards(parseInt(id), { assignments });
      await loadTournamentData();
    } catch (err) {
      console.error('Error assigning boards:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const isOrganizer = user && selectedTournament && selectedTournament.created_by.id === user.id;

  if (loading && !selectedTournament) {
    return (
      <div className="tournament-detail">
        <div className="loading-container">
          <LoadingSpinner />
          <p>Loading tournament...</p>
        </div>
      </div>
    );
  }

  if (!selectedTournament) {
    return (
      <div className="tournament-detail">
        <div className="error-container">
          <h2>Tournament Not Found</h2>
          <button className="btn btn-primary" onClick={() => navigate('/tournaments')}>
            Back to Tournaments
          </button>
        </div>
      </div>
    );
  }

  const getStatusBadge = (status: string) => {
    const statusClasses = {
      'PENDING': 'status-pending',
      'IN_PROGRESS': 'status-in-progress',
      'COMPLETED': 'status-completed'
    };

    const statusLabels = {
      'PENDING': 'Pending',
      'IN_PROGRESS': 'In Progress',
      'COMPLETED': 'Completed'
    };

    return (
      <span className={`status-badge ${statusClasses[status as keyof typeof statusClasses]}`}>
        {statusLabels[status as keyof typeof statusLabels]}
      </span>
    );
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="tournament-detail">
      {/* Header Section */}
      <div className="detail-header">
        <button className="back-button" onClick={() => navigate('/tournaments')}>
          ← Back to Tournaments
        </button>
        
        <div className="header-content">
          <div className="title-section">
            <h1>{selectedTournament.name}</h1>
            {getStatusBadge(selectedTournament.status)}
          </div>
          <p className="description">{selectedTournament.description}</p>
          
          <div className="tournament-meta">
            <div className="meta-item">
              <span className="meta-label">Organizer:</span>
              <span className="meta-value">{selectedTournament.created_by.username}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Participants:</span>
              <span className="meta-value">
                {selectedTournament.current_participants}/{selectedTournament.max_participants}
              </span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Created:</span>
              <span className="meta-value">{formatDate(selectedTournament.created_at)}</span>
            </div>
          </div>
        </div>

        {/* Organizer Controls */}
        {isOrganizer && (
          <div className="organizer-controls">
            <h3>Tournament Management</h3>
            <div className="control-buttons">
              {selectedTournament.status === 'PENDING' && (
                <>
                  <button
                    className="btn btn-primary"
                    onClick={handleGeneratePairings}
                    disabled={actionLoading !== null || selectedTournament.current_participants < 2}
                    title={selectedTournament.current_participants < 2 ? 'Need at least 2 participants' : ''}
                  >
                    {actionLoading === 'generate_pairings' ? (
                      <LoadingSpinner />
                    ) : (
                      '🎲 Generate Pairings'
                    )}
                  </button>
                  {selectedTournament.current_participants < 2 && (
                    <small className="help-text">Need at least 2 participants to start</small>
                  )}
                </>
              )}
              
              {selectedTournament.status === 'IN_PROGRESS' && pairings.length > 0 && (
                <>
                  <button
                    className="btn btn-secondary"
                    onClick={handleAssignBoards}
                    disabled={actionLoading !== null}
                  >
                    {actionLoading === 'assign_boards' ? (
                      <LoadingSpinner />
                    ) : (
                      '📹 Assign Vision Boards'
                    )}
                  </button>
                  <button
                    className="btn btn-primary"
                    onClick={handleStartRound}
                    disabled={actionLoading !== null}
                  >
                    {actionLoading === 'start_round' ? (
                      <LoadingSpinner />
                    ) : (
                      '▶️ Start Round'
                    )}
                  </button>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="error-banner">
          <span className="error-message">{error}</span>
          <button className="error-close" onClick={clearError}>×</button>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="tab-navigation">
        <button
          className={`tab ${activeTab === 'info' ? 'active' : ''}`}
          onClick={() => setActiveTab('info')}
        >
          ℹ️ Information
        </button>
        <button
          className={`tab ${activeTab === 'pairings' ? 'active' : ''}`}
          onClick={() => setActiveTab('pairings')}
        >
          🎯 Pairings
        </button>
        <button
          className={`tab ${activeTab === 'standings' ? 'active' : ''}`}
          onClick={() => setActiveTab('standings')}
        >
          🏆 Standings
        </button>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'info' && (
          <div className="info-tab">
            <div className="info-section">
              <h3>Participants ({selectedTournament.participants.length})</h3>
              {selectedTournament.participants.length > 0 ? (
                <div className="participants-grid">
                  {selectedTournament.participants.map((participant: any, index: number) => (
                    <div key={participant.id || index} className="participant-card">
                      <div className="participant-number">#{index + 1}</div>
                      <div className="participant-name">{participant.username || participant.name}</div>
                      {participant.elo_rating && (
                        <div className="participant-rating">ELO: {participant.elo_rating}</div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state-small">
                  <p>No participants yet</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'pairings' && (
          <div className="pairings-tab">
            {pairings.length > 0 ? (
              <div className="pairings-list">
                <h3>Round Pairings</h3>
                {pairings.map((pairing) => (
                  <div key={pairing.id} className="pairing-card">
                    <div className="pairing-header">
                      <span className="round-badge">Round {pairing.round_number}</span>
                      {pairing.physical_board_id && (
                        <span className="board-badge">📹 {pairing.physical_board_id}</span>
                      )}
                    </div>
                    <div className="pairing-players">
                      <div className="player white-player">
                        <span className="player-label">White:</span>
                        <span className="player-name">{pairing.white_player.username}</span>
                      </div>
                      <div className="vs-divider">vs</div>
                      {pairing.black_player ? (
                        <div className="player black-player">
                          <span className="player-label">Black:</span>
                          <span className="player-name">{pairing.black_player.username}</span>
                        </div>
                      ) : pairing.bye_player ? (
                        <div className="player bye-player">
                          <span className="bye-badge">BYE</span>
                        </div>
                      ) : null}
                    </div>
                    {pairing.result && (
                      <div className="pairing-result">
                        Result: <strong>{pairing.result}</strong>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state-small">
                <p>No pairings generated yet</p>
                {isOrganizer && selectedTournament.status === 'PENDING' && (
                  <p className="help-text">Click "Generate Pairings" to create the first round</p>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'standings' && (
          <div className="standings-tab">
            {standings.length > 0 ? (
              <div className="standings-table">
                <table>
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Player</th>
                      <th>Score</th>
                      <th>Games</th>
                      <th>Wins</th>
                      <th>Draws</th>
                      <th>Losses</th>
                    </tr>
                  </thead>
                  <tbody>
                    {standings.map((standing, index) => (
                      <tr key={standing.player_id || index}>
                        <td className="rank-cell">#{index + 1}</td>
                        <td className="player-cell">{standing.player_name}</td>
                        <td className="score-cell"><strong>{standing.score}</strong></td>
                        <td>{standing.games_played}</td>
                        <td>{standing.wins}</td>
                        <td>{standing.draws}</td>
                        <td>{standing.losses}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-state-small">
                <p>No standings available yet</p>
                <p className="help-text">Standings will appear once the tournament starts</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default TournamentDetail;
