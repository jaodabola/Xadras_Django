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
    updateTournament,
    getParticipants,
    joinTournament,
    leaveTournament,
    deleteTournament,
    startTournament,
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
  const [participants, setParticipants] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<'info' | 'pairings' | 'standings'>('info');
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  // Edit Mode state
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({
    name: '',
    description: '',
    max_participants: 2,
    tournament_type: 'SWISS',
    time_control: '',
    increment: 0,
    is_public: true,
    vision_enabled: false,
    registration_deadline: '',
    start_date: '',
  });

  useEffect(() => {
    if (id) {
      loadTournamentData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (selectedTournament) {
      const t = selectedTournament as any;
      setEditForm({
        name: t.name || '',
        description: t.description || '',
        max_participants: t.max_participants || 2,
        tournament_type: t.tournament_type || 'SWISS',
        time_control: t.time_control || '',
        increment: t.increment ?? 0,
        is_public: t.is_public ?? true,
        vision_enabled: t.vision_enabled ?? false,
        registration_deadline: t.registration_deadline ? t.registration_deadline.slice(0, 16) : '',
        start_date: t.start_date ? t.start_date.slice(0, 16) : '',
      });
    }
  }, [selectedTournament]);

  const loadTournamentData = async () => {
    if (!id) return;
    try {
      const tournament = await getTournament(id);

      const participantsData = await getParticipants(id);
      setParticipants(participantsData);

      if (tournament.status !== 'REGISTRATION') {
        if ((tournament as any).pairings) {
          setPairings((tournament as any).pairings);
        }
        const standingsData = await getStandings(id);
        setStandings(standingsData);
      }
    } catch (err) {
      console.error('Error loading tournament data:', err);
    }
  };

  const handleJoinLeave = async () => {
    if (!id) return;
    try {
      setActionLoading('join_leave');
      if (isParticipant) {
        await leaveTournament(id);
      } else {
        await joinTournament(id);
      }
      await loadTournamentData();
    } catch (err) {
      console.error('Error joining/leaving:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleSaveEdit = async () => {
    if (!id) return;
    try {
      setActionLoading('saving');

      // Prepare data for update: convert empty strings to null for date fields
      // This prevents 400 Bad Request errors from DRF DateTimeField
      const dataToUpdate = {
        ...editForm,
        registration_deadline: editForm.registration_deadline || null,
        start_date: editForm.start_date || null,
        // Also handle time_control if empty
        time_control: editForm.time_control || null
      };

      await updateTournament(id, dataToUpdate);
      setIsEditing(false);
    } catch (err) {
      console.error('Error updating tournament:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleGeneratePairings = async () => {
    if (!id) return;
    try {
      setActionLoading('generate_pairings');
      // Step 1: Start the tournament (REGISTRATION -> IN_PROGRESS, assigns seeds)
      await startTournament(id);
      // Step 2: Generate pairings for the first round
      await generatePairings(id);
      await loadTournamentData();
      setActiveTab('pairings');
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
      await startRound(id);
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
      const assignments = pairings.map((pairing, index) => ({
        pairing_id: pairing.id,
        physical_board_id: `board_${String(index + 1).padStart(3, '0')}`,
        camera_id: index + 1
      }));
      await assignBoards(id, { assignments });
      await loadTournamentData();
    } catch (err) {
      console.error('Error assigning boards:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDeleteTournament = async () => {
    if (!id) return;
    try {
      setActionLoading('deleting');
      await deleteTournament(id);
      navigate('/tournaments');
    } catch (err) {
      console.error('Error deleting tournament:', err);
    } finally {
      setActionLoading(null);
      setShowDeleteModal(false);
    }
  };

  const isOrganizer = user && selectedTournament && selectedTournament.created_by === user.id;
  const isParticipant = user && participants.some((p: any) => p.user === user.id);
  const canJoin = user && !user.isGuest && selectedTournament && !isParticipant && selectedTournament.status === 'REGISTRATION' && selectedTournament.participant_count < selectedTournament.max_participants;

  if (loading && !selectedTournament) {
    return (
      <div className="tournament-detail">
        <div className="loading-container glass-card">
          <LoadingSpinner />
          <p>A carregar torneio...</p>
        </div>
      </div>
    );
  }

  if (!selectedTournament) {
    return (
      <div className="tournament-detail">
        <div className="error-container glass-card">
          <h2>Torneio Não Encontrado</h2>
          <button className="btn btn-primary" onClick={() => navigate('/tournaments')}>
            Voltar aos Torneios
          </button>
        </div>
      </div>
    );
  }

  const getStatusBadge = (status: string) => {
    const statusClasses: Record<string, string> = {
      'REGISTRATION': 'status-pending',
      'IN_PROGRESS': 'status-in-progress',
      'FINISHED': 'status-completed',
      'CANCELLED': 'status-completed'
    };
    const statusLabels: Record<string, string> = {
      'REGISTRATION': 'Inscrições Abertas',
      'IN_PROGRESS': 'A Decorrer',
      'FINISHED': 'Terminado',
      'CANCELLED': 'Cancelado'
    };
    return (
      <span className={`status-badge ${statusClasses[status] || ''}`}>
        {statusLabels[status] || status}
      </span>
    );
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('pt-PT', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="tournament-detail">
      {/* Background decoration */}
      <div className="bg-glow bg-glow-primary"></div>
      <div className="bg-glow bg-glow-secondary"></div>

      <div className="detail-content-wrapper">
        <button className="back-button" onClick={() => navigate('/tournaments')}>
          <span className="icon">←</span> Voltar aos Torneios
        </button>

        {/* Error Display */}
        {error && (
          <div className="error-banner animate-fade-in">
            <span className="error-message">{error}</span>
            <button className="error-close" onClick={clearError}>×</button>
          </div>
        )}

        {/* Hero Header Section */}
        <div className="detail-header glass-card animate-slide-up">
          {isEditing ? (
            <div className="edit-form">
              <h3 className="edit-form-title">✏️ Editar Torneio</h3>

              {/* Row 1: Name */}
              <div className="form-group">
                <label>Nome do Torneio</label>
                <input
                  type="text"
                  value={editForm.name}
                  onChange={e => setEditForm({ ...editForm, name: e.target.value })}
                  className="game-input"
                />
              </div>

              {/* Row 2: Format + Max Participants */}
              <div className="form-row">
                <div className="form-group">
                  <label>Formato</label>
                  <select
                    value={editForm.tournament_type}
                    onChange={e => setEditForm({ ...editForm, tournament_type: e.target.value })}
                    className="game-select"
                    disabled={selectedTournament.status !== 'REGISTRATION'}
                  >
                    <option value="SWISS">Sistema Suíço</option>
                    <option value="ROUND_ROBIN">Todos Contra Todos</option>
                    <option value="ELIMINATION">Eliminação Direta</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Máx. Participantes</label>
                  <input
                    type="number"
                    min="2" max="256"
                    value={editForm.max_participants}
                    onChange={e => setEditForm({ ...editForm, max_participants: parseInt(e.target.value) })}
                    className="game-input"
                    disabled={selectedTournament.status !== 'REGISTRATION'}
                  />
                </div>
              </div>

              {/* Row 3: Time Control + Increment */}
              <div className="form-row">
                <div className="form-group">
                  <label>Controlo de Tempo</label>
                  <select
                    value={editForm.time_control}
                    onChange={e => setEditForm({ ...editForm, time_control: e.target.value })}
                    className="game-select"
                  >
                    <option value="">Selecionar...</option>
                    <option value="1+0">1 min (Bullet)</option>
                    <option value="2+1">2+1 min (Bullet)</option>
                    <option value="3+0">3 min (Blitz)</option>
                    <option value="3+2">3+2 min (Blitz)</option>
                    <option value="5+0">5 min (Blitz)</option>
                    <option value="5+3">5+3 min (Blitz)</option>
                    <option value="10+0">10 min (Rápido)</option>
                    <option value="10+5">10+5 min (Rápido)</option>
                    <option value="15+10">15+10 min (Rápido)</option>
                    <option value="30+0">30 min (Clássico)</option>
                    <option value="60+0">60 min (Clássico)</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Incremento (seg)</label>
                  <input
                    type="number"
                    min="0" max="60"
                    value={editForm.increment}
                    onChange={e => setEditForm({ ...editForm, increment: parseInt(e.target.value) || 0 })}
                    className="game-input"
                  />
                </div>
              </div>

              {/* Row 4: Registration Deadline + Start Date */}
              <div className="form-row">
                <div className="form-group">
                  <label>Prazo de Inscrição</label>
                  <input
                    type="datetime-local"
                    value={editForm.registration_deadline}
                    onChange={e => setEditForm({ ...editForm, registration_deadline: e.target.value })}
                    className="game-input"
                  />
                </div>
                <div className="form-group">
                  <label>Data de Início</label>
                  <input
                    type="datetime-local"
                    value={editForm.start_date}
                    onChange={e => setEditForm({ ...editForm, start_date: e.target.value })}
                    className="game-input"
                  />
                </div>
              </div>

              {/* Row 5: Toggles */}
              <div className="form-row">
                <div className="form-group toggle-group">
                  <label className="toggle-label">
                    <input
                      type="checkbox"
                      checked={editForm.is_public}
                      onChange={e => setEditForm({ ...editForm, is_public: e.target.checked })}
                      className="toggle-checkbox"
                    />
                    <span className="toggle-text">🌐 Torneio Público</span>
                  </label>
                  <span className="toggle-hint">Visível para todos os utilizadores</span>
                </div>
                <div className="form-group toggle-group">
                  <label className="toggle-label">
                    <input
                      type="checkbox"
                      checked={editForm.vision_enabled}
                      onChange={e => setEditForm({ ...editForm, vision_enabled: e.target.checked })}
                      className="toggle-checkbox"
                    />
                    <span className="toggle-text">📹 Vision AI Ativado</span>
                  </label>
                  <span className="toggle-hint">Reconhecimento automático de posições</span>
                </div>
              </div>

              {/* Row 6: Description */}
              <div className="form-group">
                <label>Descrição</label>
                <textarea
                  value={editForm.description}
                  onChange={e => setEditForm({ ...editForm, description: e.target.value })}
                  className="game-input textarea"
                  rows={3}
                  placeholder="Descreve o torneio, regras especiais, prémios..."
                />
              </div>

              {selectedTournament.status !== 'REGISTRATION' && (
                <div className="edit-warning">
                  ⚠️ Formato e capacidade não podem ser alterados após o torneio ter começado.
                </div>
              )}

              <div className="edit-actions">
                <button className="btn btn-secondary" onClick={() => setIsEditing(false)}>Cancelar</button>
                <button className="btn btn-primary" onClick={handleSaveEdit} disabled={actionLoading === 'saving'}>
                  {actionLoading === 'saving' ? <LoadingSpinner size="small" /> : '💾 Guardar Alterações'}
                </button>
              </div>
            </div>
          ) : (
            <>
              <div className="header-top-row">
                <div className="title-section">
                  <h1>{selectedTournament.name}</h1>
                  {getStatusBadge(selectedTournament.status)}
                </div>

                {/* Global Actions */}
                <div className="header-global-actions">
                  {(canJoin || isParticipant) && (
                    <button
                      className={`btn ${isParticipant ? 'btn-danger' : 'btn-primary'} join-btn`}
                      onClick={handleJoinLeave}
                      disabled={actionLoading === 'join_leave'}
                    >
                      {actionLoading === 'join_leave' ? <LoadingSpinner size="small" /> : (
                        isParticipant ? 'Sair do Torneio' : 'Participar no Torneio'
                      )}
                    </button>
                  )}
                  {isOrganizer && (
                    <button
                      className="btn btn-outline btn-icon"
                      onClick={() => setIsEditing(true)}
                      title="Editar Torneio"
                    >
                      ✏️
                    </button>
                  )}
                  {isOrganizer && (
                    <button
                      className="btn btn-danger-outline btn-icon"
                      onClick={() => setShowDeleteModal(true)}
                      disabled={actionLoading !== null}
                      title="Apagar Torneio"
                    >
                      🗑
                    </button>
                  )}
                </div>
              </div>

              <p className="description">{selectedTournament.description || "Nenhuma descrição fornecida."}</p>

              <div className="tournament-meta-pills">
                <div className="meta-pill">
                  <span className="meta-icon">👑</span>
                  <div className="meta-text">
                    <span className="meta-label">Organizador</span>
                    <span className="meta-value">{selectedTournament.created_by_username}</span>
                  </div>
                </div>
                <div className="meta-pill">
                  <span className="meta-icon">👥</span>
                  <div className="meta-text">
                    <span className="meta-label">Participantes</span>
                    <span className="meta-value">
                      {selectedTournament.participant_count}/{selectedTournament.max_participants}
                    </span>
                  </div>
                </div>
                <div className="meta-pill">
                  <span className="meta-icon">📅</span>
                  <div className="meta-text">
                    <span className="meta-label">Criado a</span>
                    <span className="meta-value">{formatDate(selectedTournament.created_at)}</span>
                  </div>
                </div>
                <div className="meta-pill">
                  <span className="meta-icon">⏱️</span>
                  <div className="meta-text">
                    <span className="meta-label">Controlo de Tempo</span>
                    <span className="meta-value">{selectedTournament.time_control || 'N/A'} {selectedTournament.increment ? `+ ${selectedTournament.increment}s` : ''}</span>
                  </div>
                </div>
              </div>

              {/* Organizer Controls */}
              {isOrganizer && (
                <div className="organizer-controls-inline">
                  <div className="controls-header">
                    <h3>🛠️ Painel de Gestão Direta</h3>
                  </div>
                  <div className="control-buttons">
                    {selectedTournament.status === 'REGISTRATION' && (
                      <div className="control-action-group">
                        <button
                          className="btn btn-primary glow-btn"
                          onClick={handleGeneratePairings}
                          disabled={actionLoading !== null || selectedTournament.participant_count < 2}
                        >
                          {actionLoading === 'generate_pairings' ? <LoadingSpinner size="small" /> : '▶ Iniciar Torneio e Gerar 1ª Ronda'}
                        </button>
                        {selectedTournament.participant_count < 2 && (
                          <span className="help-text-inline">São necessários pelo menos 2 participantes para iniciar.</span>
                        )}
                      </div>
                    )}

                    {selectedTournament.status === 'IN_PROGRESS' && pairings.length > 0 && (
                      <div className="control-action-group">
                        <button
                          className="btn btn-secondary"
                          onClick={handleAssignBoards}
                          disabled={actionLoading !== null}
                        >
                          {actionLoading === 'assign_boards' ? <LoadingSpinner size="small" /> : '📹 Atribuir Tabuleiros Vision'}
                        </button>
                        <button
                          className="btn btn-primary"
                          onClick={handleStartRound}
                          disabled={actionLoading !== null}
                        >
                          {actionLoading === 'start_round' ? <LoadingSpinner size="small" /> : '▶️ Iniciar Ronda'}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Tab Navigation */}
        <div className="tabs-container animate-fade-in">
          <div className="tabs-list">
            <button
              className={`tab-button ${activeTab === 'info' ? 'active' : ''}`}
              onClick={() => setActiveTab('info')}
            >
              ℹ️ Participantes
            </button>
            <button
              className={`tab-button ${activeTab === 'pairings' ? 'active' : ''}`}
              onClick={() => setActiveTab('pairings')}
            >
              🎯 Emparelhamentos
            </button>
            <button
              className={`tab-button ${activeTab === 'standings' ? 'active' : ''}`}
              onClick={() => setActiveTab('standings')}
            >
              🏆 Classificação
            </button>
          </div>
        </div>

        {/* Tab Content */}
        <div className="tab-content animate-slide-up">
          {activeTab === 'info' && (
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
          )}

          {activeTab === 'pairings' && (
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
                  {isOrganizer && selectedTournament.status === 'REGISTRATION' && (
                    <p className="help-text">Utiliza o botão "Gerar Emparelhamentos" acima para iniciar!</p>
                  )}
                </div>
              )}
            </div>
          )}

          {activeTab === 'standings' && (
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
                  <div className="empty-icon">🏆</div>
                  <p>A classificação final ou parcial ainda não está disponível.</p>
                  <p className="help-text">Aguardando a conclusão da primeira ronda.</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      {/* Modal de confirmação para apagar */}
      {showDeleteModal && (
        <div className="modal-overlay" onClick={() => setShowDeleteModal(false)}>
          <div className="modal-box" onClick={e => e.stopPropagation()}>
            <div className="modal-icon">🗑️</div>
            <h3>Apagar Torneio</h3>
            <p>
              Tem a certeza que pretende apagar o torneio{' '}
              <strong>{selectedTournament?.name}</strong>?
            </p>
            <div className="modal-warning-text">
              ⚠️ Esta ação é irreversível. Todos os dados, participantes e histórico de jogos associados serão permanentemente eliminados.
            </div>
            <div className="modal-actions">
              <button
                className="btn-delete-cancel"
                onClick={() => setShowDeleteModal(false)}
                disabled={actionLoading === 'deleting'}
              >
                Cancelar
              </button>
              <button
                className="btn-delete-confirm"
                onClick={handleDeleteTournament}
                disabled={actionLoading === 'deleting'}
              >
                {actionLoading === 'deleting' ? <LoadingSpinner size="small" /> : '🗑 Apagar Definitivamente'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TournamentDetail;
