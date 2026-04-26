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
import { IconArrowRight, IconCrown, IconUsers, IconCalendar, IconClock, IconEdit, IconTrash, IconPlay, IconCamera, IconTrophy } from '../../components/Icons/Icons';
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
      // startTournament já gera automaticamente a 1ª ronda no backend
      await startTournament(id);
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
        <button className="back-button flex-center-gap" onClick={() => navigate('/tournaments')}>
          <IconArrowRight size={18} style={{ transform: 'rotate(180deg)' }} /> Voltar aos Torneios
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
                </div>

                {/* Global Actions */}
                <div className="header-global-actions">
                  {(canJoin || (isParticipant && !isOrganizer)) && (
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
                      className="btn btn-outline btn-icon flex-center-gap"
                      onClick={() => setIsEditing(true)}
                      title="Editar Torneio"
                    >
                      <IconEdit size={16} />
                    </button>
                  )}
                  {isOrganizer && (
                    <button
                      className="btn btn-danger-outline btn-icon flex-center-gap"
                      onClick={() => setShowDeleteModal(true)}
                      disabled={actionLoading !== null}
                      title="Apagar Torneio"
                    >
                      <IconTrash size={16} />
                    </button>
                  )}
                </div>
              </div>

              <p className="description">{selectedTournament.description || "Nenhuma descrição fornecida."}</p>

              <div className="tournament-meta-pills">
                <div className="meta-pill">
                  <span className="meta-icon"><IconCrown size={18} /></span>
                  <div className="meta-text">
                    <span className="meta-label">Organizador</span>
                    <span className="meta-value">{selectedTournament.created_by_username}</span>
                  </div>
                </div>
                <div className="meta-pill">
                  <span className="meta-icon"><IconUsers size={18} /></span>
                  <div className="meta-text">
                    <span className="meta-label">Participantes</span>
                    <span className="meta-value">
                      {selectedTournament.participant_count}/{selectedTournament.max_participants}
                    </span>
                  </div>
                </div>
                <div className="meta-pill">
                  <span className="meta-icon"><IconCalendar size={18} /></span>
                  <div className="meta-text">
                    <span className="meta-label">Criado a</span>
                    <span className="meta-value">{formatDate(selectedTournament.created_at)}</span>
                  </div>
                </div>
                <div className="meta-pill">
                  <span className="meta-icon"><IconClock size={18} /></span>
                  <div className="meta-text">
                    <span className="meta-label">Controlo de Tempo</span>
                    <span className="meta-value">{selectedTournament.time_control || 'N/A'} {selectedTournament.increment ? `+ ${selectedTournament.increment}s` : ''}</span>
                  </div>
                </div>
              </div>

              {/* Organizer Controls */}
              {isOrganizer && (
                <div className="organizer-controls-inline">

                  <div className="control-buttons">
                    {selectedTournament.status === 'REGISTRATION' && (
                      <div className="control-action-group">
                        <button
                          className="btn btn-primary glow-btn flex-center-gap"
                          onClick={handleGeneratePairings}
                          disabled={actionLoading !== null || selectedTournament.participant_count < 2}
                        >
                          {actionLoading === 'generate_pairings' ? <LoadingSpinner size="small" /> : <><IconPlay size={16} /> Iniciar Torneio e Gerar 1ª Ronda</>}
                        </button>
                        {selectedTournament.participant_count < 2 && (
                          <span className="help-text-inline">São necessários pelo menos 2 participantes para iniciar.</span>
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
              className={`tab-button flex-center-gap ${activeTab === 'info' ? 'active' : ''}`}
              onClick={() => setActiveTab('info')}
            >
              <IconUsers size={16} /> Participantes
            </button>
            <button
              className={`tab-button flex-center-gap ${activeTab === 'pairings' ? 'active' : ''}`}
              onClick={() => setActiveTab('pairings')}
            >
              <IconCalendar size={16} /> Emparelhamentos
            </button>
            <button
              className={`tab-button flex-center-gap ${activeTab === 'standings' ? 'active' : ''}`}
              onClick={() => setActiveTab('standings')}
            >
              <IconTrophy size={16} /> Classificação
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
              currentUserId={user?.id ?? null}
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
    </div>
  );
};

export default TournamentDetail;