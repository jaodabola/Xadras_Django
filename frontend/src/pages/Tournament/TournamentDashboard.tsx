import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTournament } from '../../contexts/TournamentContext';
import { useAuth } from '../../contexts/AuthContext';
import LoadingSpinner from '../../components/LoadingSpinner/LoadingSpinner';
import './TournamentDashboard.css';

const TournamentDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { 
    tournaments, 
    loading, 
    error, 
    fetchTournaments,
    joinTournament,
    clearError 
  } = useTournament();

  const [filter, setFilter] = useState<'all' | 'pending' | 'in_progress' | 'completed'>('all');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (user) {
      fetchTournaments();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]); // Only re-fetch when user changes, not on every render

  // Filter tournaments based on status and search term
  const filteredTournaments = tournaments.filter(tournament => {
    const statusMap: Record<string, string> = {
      'all': '',
      'pending': 'REGISTRATION',
      'in_progress': 'IN_PROGRESS',
      'completed': 'FINISHED',
    };
    const matchesFilter = filter === 'all' || tournament.status === statusMap[filter];
    const matchesSearch = tournament.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         (tournament.description || '').toLowerCase().includes(searchTerm.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const handleJoinTournament = async (tournamentId: string) => {
    try {
      await joinTournament(tournamentId);
    } catch (err) {
      // Error is handled by context
    }
  };

  const getStatusBadge = (status: string) => {
    const statusClasses: Record<string, string> = {
      'REGISTRATION': 'status-pending',
      'IN_PROGRESS': 'status-in-progress', 
      'FINISHED': 'status-completed',
      'CANCELLED': 'status-completed',
    };
    
    const statusLabels: Record<string, string> = {
      'REGISTRATION': 'Inscrições Abertas',
      'IN_PROGRESS': 'A decorrer',
      'FINISHED': 'Terminado',
      'CANCELLED': 'Cancelado',
    };

    return (
      <span className={`status-badge ${statusClasses[status as keyof typeof statusClasses]}`}>
        {statusLabels[status as keyof typeof statusLabels]}
      </span>
    );
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('pt-PT', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (!user) {
    return (
      <div className="tournament-dashboard">
        <div className="auth-required">
          <h2>Autenticação necessária</h2>
          <p>Inicie sessão para ver e participar em torneios de xadrez.</p>
          <button
            className="btn btn-primary"
            onClick={() => navigate('/login')}
          >
            Iniciar Sessão
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="tournament-dashboard">
      {/* Header Section */}
      <div className="dashboard-header">
        <div className="header-content">
          <h1>Torneios</h1>
          <p>Organize e participe em torneios de xadrez</p>
        </div>
        <div className="header-actions">
          {user && (
            <button
              className="btn btn-primary"
              onClick={() => navigate('/tournaments/create')}
            >
              + Criar Torneio
            </button>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="error-banner">
          <div className="error-content">
            <span className="error-message">{error}</span>
            <button 
              className="error-close"
              onClick={clearError}
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Filters and Search */}
      <div className="dashboard-controls">
        <div className="search-container">
          <input
            type="text"
            placeholder="Pesquisar torneios…"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>
        
        <div className="filter-container">
          <label>Estado:</label>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as any)}
            className="filter-select"
          >
            <option value="all">Todos</option>
            <option value="pending">Próximos</option>
            <option value="in_progress">A decorrer</option>
            <option value="completed">Terminados</option>
          </select>
        </div>
      </div>

      {/* Tournament Grid */}
      <div className="tournaments-section">
        {loading ? (
          <div className="loading-container">
            <LoadingSpinner />
            <p>A carregar torneios…</p>
          </div>
        ) : filteredTournaments.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🏆</div>
            <h3>Nenhum torneio encontrado</h3>
            <p>
              {tournaments.length === 0
                ? 'Nenhum torneio disponível. Crie o primeiro!'
                : 'Nenhum torneio corresponde aos filtros actuais.'}
            </p>
            {tournaments.length === 0 && (
              <button
                className="btn btn-primary"
                onClick={() => navigate('/tournaments/create')}
              >
                Criar Primeiro Torneio
              </button>
            )}
          </div>
        ) : (
          <div className="tournament-grid">
            {filteredTournaments.map((tournament) => (
              <div key={tournament.id} className="tournament-card">
                <div className="card-header">
                  <h3 className="tournament-name">{tournament.name}</h3>
                  {getStatusBadge(tournament.status)}
                </div>
                
                <div className="card-content">
                  <p className="tournament-description">{tournament.description}</p>
                  
                  <div className="tournament-stats">
                    <div className="stat-item">
                      <span className="stat-label">Participantes</span>
                      <span className="stat-value">
                        {tournament.participant_count}/{tournament.max_participants}
                      </span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">Criado por</span>
                      <span className="stat-value">{tournament.created_by_username}</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">Data</span>
                      <span className="stat-value">{formatDate(tournament.created_at)}</span>
                    </div>
                  </div>
                </div>
                
                <div className="card-actions">
                  <button
                    className="btn btn-secondary"
                    onClick={() => navigate(`/tournaments/${tournament.id}`)}
                  >
                    Ver Detalhes
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Stats */}
      <div className="dashboard-stats">
        <div className="stat-card">
          <div className="stat-number">{tournaments.length}</div>
          <div className="stat-label">Total</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">
            {tournaments.filter(t => t.status === 'REGISTRATION').length}
          </div>
          <div className="stat-label">Próximos</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">
            {tournaments.filter(t => t.status === 'IN_PROGRESS').length}
          </div>
          <div className="stat-label">A decorrer</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">
            {tournaments.filter(t => t.status === 'FINISHED').length}
          </div>
          <div className="stat-label">Terminados</div>
        </div>
      </div>
    </div>
  );
};

export default TournamentDashboard;
