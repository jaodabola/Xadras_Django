import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTournament } from '../../contexts/TournamentContext';
import { useAuth } from '../../contexts/AuthContext';
import LoadingSpinner from '../../components/LoadingSpinner/LoadingSpinner';
import TournamentEditForm from './components/TournamentEditForm';
import TournamentInfoTab from './components/TournamentInfoTab';
import TournamentPairingsTab from './components/TournamentPairingsTab';
import TournamentStandingsTab from './components/TournamentStandingsTab';
import TournamentDeleteModal from './components/TournamentDeleteModal';
import './TournamentDetail.css';

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
    getAllPairings,
    loading,
    error,
    clearError
  } = useTournament();

  const [pairings, setPairings] = useState<any[]>([]);
  const [standings, setStandings] = useState<any[]>([]);
  const [participants, setParticipants] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<'info' | 'pairings' | 'standings'>('info');
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  // Modal de códigos de câmara por mesa
  const [showBoardCodesModal, setShowBoardCodesModal] = useState(false);
  const [boardCodes, setBoardCodes] = useState<{ boardNumber: number; sessionCode: string; white: string; black: string }[]>([]);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

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
        const allPairings = await getAllPairings(id);
        setPairings(allPairings);

        try {
          const standingsData = await getStandings(id);
          setStandings(standingsData);
        } catch {
          // Classificação pode não estar disponível ainda
        }
      } else {
        setPairings([]);
        setStandings([]);
      }
    } catch (err) {
      console.error('Error loading tournament data:', err);
    }
  };

  // Recarregar classificação ao mudar para esse tab
  const handleTabChange = async (tab: 'info' | 'pairings' | 'standings') => {
    setActiveTab(tab);
    if (tab === 'standings' && id && selectedTournament?.status !== 'REGISTRATION') {
      try {
        const standingsData = await getStandings(id);
        setStandings(standingsData);
      } catch { /* ignorar */ }
    }
    if (tab === 'pairings' && id && selectedTournament?.status !== 'REGISTRATION') {
      try {
        const allPairings = await getAllPairings(id);
        setPairings(allPairings);
      } catch { /* ignorar */ }
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
      const dataToUpdate = {
        ...editForm,
        registration_deadline: editForm.registration_deadline || null,
        start_date: editForm.start_date || null,
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

  // Iniciar torneio e gerar emparelhamentos da 1ª ronda
  const handleStartTournament = async () => {
    if (!id) return;
    try {
      setActionLoading('start_tournament');
      await startTournament(id);
      await generatePairings(id);
      await loadTournamentData();
      setActiveTab('pairings');
    } catch (err) {
      console.error('Error starting tournament:', err);
    } finally {
      setActionLoading(null);
    }
  };

  // Gerar próxima ronda (torneio já em progresso)
  const handleGenerateNextRound = async () => {
    if (!id) return;
    try {
      setActionLoading('generate_pairings');
      await generatePairings(id);
      await loadTournamentData();
      setActiveTab('pairings');
    } catch (err) {
      console.error('Error generating next round:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleStartRound = async () => {
    if (!id || !selectedTournament) return;
    const currentRound = (selectedTournament as any).current_round || 1;
    try {
      setActionLoading('start_round');
      await startRound(id, currentRound);
      await loadTournamentData();
    } catch (err) {
      console.error('Error starting round:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleAssignBoards = async () => {
    if (!id || !pairings.length || !selectedTournament) return;
    try {
      setActionLoading('assign_boards');
      const currentRound = (selectedTournament as any).current_round || 1;
      // Só atribuir os pairings da ronda atual
      const roundPairings = pairings.filter((p: any) => !p.is_bye && p.round_number === currentRound);

      // Gerar um código de sessão único por mesa (mesmo formato do CameraMode)
      const generateSessionCode = () => {
        const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
        let result = '';
        for (let i = 0; i < 6; i++) {
          result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
      };

      const assignments: Record<string, any> = {};
      const generatedCodes: { boardNumber: number; sessionCode: string; white: string; black: string }[] = [];

      roundPairings.forEach((pairing: any, index: number) => {
        const sessionCode = generateSessionCode();
        const boardNumber = index + 1;
        assignments[pairing.id] = {
          physical_board_id: sessionCode,   // código de sessão como ID do tabuleiro
          camera_id: boardNumber,
          board_number: boardNumber,
        };
        generatedCodes.push({
          boardNumber,
          sessionCode,
          white: pairing.white_player?.username || '?',
          black: pairing.black_player?.username || '?',
        });
      });

      await assignBoards(id, { round_number: currentRound, board_assignments: assignments });
      await loadTournamentData();

      // Mostrar modal com os códigos
      setBoardCodes(generatedCodes);
      setShowBoardCodesModal(true);
    } catch (err) {
      console.error('Error assigning boards:', err);
    } finally {
      setActionLoading(null);
    }
  };

  const copyBoardCode = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedCode(code);
      setTimeout(() => setCopiedCode(null), 2000);
    } catch {
      const el = document.createElement('textarea');
      el.value = code;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      setCopiedCode(code);
      setTimeout(() => setCopiedCode(null), 2000);
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
  const canJoin = user && selectedTournament && !isParticipant && selectedTournament.status === 'REGISTRATION' && selectedTournament.participant_count < selectedTournament.max_participants;

  // Verificar se a ronda atual tem todos os jogos terminados (para habilitar "próxima ronda")
  const currentRound = (selectedTournament as any)?.current_round || 0;
  const totalRounds = (selectedTournament as any)?.total_rounds || 0;
  const currentRoundPairings = pairings.filter((p: any) => p.round_number === currentRound);
  const allCurrentRoundFinished = currentRoundPairings.length > 0 &&
    currentRoundPairings.every((p: any) => p.result !== null || p.is_bye);
  const canGenerateNextRound = selectedTournament?.status === 'IN_PROGRESS' &&
    allCurrentRoundFinished &&
    (totalRounds === 0 || currentRound < totalRounds);

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
            <TournamentEditForm 
              editForm={editForm}
              setEditForm={setEditForm}
              selectedTournament={selectedTournament}
              actionLoading={actionLoading}
              onSave={handleSaveEdit}
              onCancel={() => setIsEditing(false)}
            />
          ) : (
            <>
              <div className="header-top-row">
                <div className="title-section">
                  <h1>{selectedTournament.name}</h1>
                  {getStatusBadge(selectedTournament.status)}
                  {selectedTournament.status === 'IN_PROGRESS' && (
                    <span className="round-info-badge">
                      Ronda {currentRound}{totalRounds > 0 ? ` / ${totalRounds}` : ''}
                    </span>
                  )}
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
                    <h3>🛠️ Painel de Gestão</h3>
                  </div>
                  <div className="control-buttons">
                    {/* Iniciar torneio (estado REGISTRATION) */}
                    {selectedTournament.status === 'REGISTRATION' && (
                      <div className="control-action-group">
                        <button
                          className="btn btn-primary glow-btn"
                          onClick={handleStartTournament}
                          disabled={actionLoading !== null || selectedTournament.participant_count < 2}
                        >
                          {actionLoading === 'start_tournament' ? <LoadingSpinner size="small" /> : '▶ Iniciar Torneio e Gerar 1ª Ronda'}
                        </button>
                        {selectedTournament.participant_count < 2 && (
                          <span className="help-text-inline">São necessários pelo menos 2 participantes para iniciar.</span>
                        )}
                      </div>
                    )}

                    {/* Controlos durante torneio */}
                    {selectedTournament.status === 'IN_PROGRESS' && (
                      <div className="control-action-group">
                        {/* Gerar próxima ronda — só quando a ronda atual está completa e há mais rondas */}
                        {canGenerateNextRound && (
                          <button
                            className="btn btn-primary glow-btn"
                            onClick={handleGenerateNextRound}
                            disabled={actionLoading !== null}
                          >
                            {actionLoading === 'generate_pairings' ? <LoadingSpinner size="small" /> : `▶ Gerar Ronda ${currentRound + 1}`}
                          </button>
                        )}

                        {/* Atribuir tabuleiros Vision */}
                        {pairings.filter(p => p.round_number === currentRound).length > 0 && (
                          <button
                            className="btn btn-secondary"
                            onClick={handleAssignBoards}
                            disabled={actionLoading !== null}
                          >
                            {actionLoading === 'assign_boards' ? <LoadingSpinner size="small" /> : '📹 Atribuir Tabuleiros Vision'}
                          </button>
                        )}
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
              onClick={() => handleTabChange('info')}
            >
              ℹ️ Participantes
            </button>
            <button
              className={`tab-button ${activeTab === 'pairings' ? 'active' : ''}`}
              onClick={() => handleTabChange('pairings')}
            >
              🎯 Emparelhamentos
            </button>
            <button
              className={`tab-button ${activeTab === 'standings' ? 'active' : ''}`}
              onClick={() => handleTabChange('standings')}
            >
              🏆 Classificação
            </button>
          </div>
        </div>

        {/* Tab Content */}
        <div className="tab-content animate-slide-up">
          {activeTab === 'info' && <TournamentInfoTab participants={participants} />}
          {activeTab === 'pairings' && (
            <TournamentPairingsTab
              pairings={pairings}
              isOrganizer={!!isOrganizer}
              status={selectedTournament.status}
              currentUserId={user?.id}
              organizerId={(selectedTournament as any).created_by}
              tournamentId={id}
            />
          )}
          {activeTab === 'standings' && <TournamentStandingsTab standings={standings} />}
        </div>
      </div>
      
      {/* Modal de confirmação para apagar */}
      <TournamentDeleteModal 
        isOpen={showDeleteModal}
        tournamentName={selectedTournament?.name}
        actionLoading={actionLoading}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleDeleteTournament}
      />

      {/* Modal de Códigos de Câmara por Mesa */}
      {showBoardCodesModal && (
        <div className="modal-overlay" onClick={() => setShowBoardCodesModal(false)}>
          <div className="modal-box board-codes-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-icon">📷</div>
            <h3>Códigos de Câmara — Ronda {(selectedTournament as any)?.current_round}</h3>
            <p>Introduz cada código na app do tabuleiro físico correspondente.</p>

            <div className="board-codes-list">
              {boardCodes.map(board => (
                <div key={board.boardNumber} className="board-code-row">
                  <div className="board-code-info">
                    <span className="board-code-number">Mesa {board.boardNumber}</span>
                    <span className="board-code-players">
                      <span className="bc-white">♙ {board.white}</span>
                      <span className="bc-vs">vs</span>
                      <span className="bc-black">♟ {board.black}</span>
                    </span>
                  </div>
                  <div
                    className="board-session-code"
                    onClick={() => copyBoardCode(board.sessionCode)}
                    title="Clique para copiar"
                  >
                    {board.sessionCode}
                    <span className="copy-hint">
                      {copiedCode === board.sessionCode ? '✅' : '📋'}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <div className="modal-actions" style={{ justifyContent: 'center', marginTop: '1.5rem' }}>
              <button
                className="btn btn-primary"
                onClick={() => setShowBoardCodesModal(false)}
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TournamentDetail;
