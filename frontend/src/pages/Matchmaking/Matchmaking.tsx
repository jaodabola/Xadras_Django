import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMatchmaking } from '../../contexts/MatchmakingContext';
import { useAuth } from '../../contexts/AuthContext';
import './Matchmaking.css';

/* ─── Time control options (design1 pattern) ─── */
const TIME_CONTROLS = [
  { id: 'bullet', label: 'Bullet', time: '1 min', icon: '⚡', description: 'Ritmo rápido, um minuto por jogador' },
  { id: 'blitz', label: 'Blitz', time: '5 min', icon: '⏱', description: 'Jogos rápidos, cinco minutos cada' },
  { id: 'rapid', label: 'Rápido', time: '10 min', icon: '🕐', description: 'Ritmo padrão, dez minutos por lado' },
  { id: 'classical', label: 'Clássico', time: '30 min', icon: '♟', description: 'Tempo tradicional para jogo profundo' },
] as const;

type TimeControlId = typeof TIME_CONTROLS[number]['id'];

/* ─── Searching timer ─── */
function SearchingTimer({ seconds }: { seconds: number }) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return <span>{String(m).padStart(2, '0')}:{String(s).padStart(2, '0')}</span>;
}

/* ─── Main component ─── */
const Matchmaking: React.FC = () => {
  const [selectedTimeControl, setSelectedTimeControl] = useState<TimeControlId | null>(null);
  const [preferredColor, setPreferredColor] = useState<'WHITE' | 'BLACK' | 'ANY'>('ANY');
  const [timeInQueue, setTimeInQueue] = useState(0);
  const [queuePosition, setQueuePosition] = useState<number | null>(null);
  const [estimatedWaitTime, setEstimatedWaitTime] = useState<number | null>(null);

  const { isInQueue, joinQueue, leaveQueue, matchFound, matchData, error } = useMatchmaking();
  const { user } = useAuth();
  const navigate = useNavigate();

  /* Navigate on match found */
  useEffect(() => {
    if (matchFound && matchData) navigate(`/game/${matchData.game_id}`);
  }, [matchFound, matchData, navigate]);

  /* Queue timer */
  useEffect(() => {
    if (!isInQueue) {
      setTimeInQueue(0);
      setQueuePosition(null);
      setEstimatedWaitTime(null);
      return;
    }
    setTimeInQueue(0);
    const interval = setInterval(() => {
      setTimeInQueue(t => t + 1);
      if (Math.random() > 0.7)
        setQueuePosition(p => p ? Math.max(1, p - 1) : Math.floor(Math.random() * 10) + 1);
      if (Math.random() > 0.8)
        setEstimatedWaitTime(p => p ? Math.max(5, p + (Math.random() > 0.5 ? 1 : -1)) : 10);
    }, 1000);
    return () => clearInterval(interval);
  }, [isInQueue]);

  const handleFindMatch = async () => {
    try { await joinQueue(preferredColor); } catch (e) { console.error(e); }
  };

  const handleCancelSearch = async () => {
    try { await leaveQueue(); } catch (e) { console.error(e); }
  };

  /* Not logged in state */
  if (!user) {
    return (
      <div className="matchmaking-container">
        <div className="matchmaking-card not-logged-in">
          <div className="lock-icon">🔒</div>
          <h2>Autenticação necessária</h2>
          <p>Inicie sessão para encontrar adversários e jogar xadrez online.</p>
          <button className="login-button" onClick={() => navigate('/login')}>
            Iniciar Sessão
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="matchmaking-container">
      <div className="matchmaking-card">

        {/* Header */}
        <div className="card-header">
          <h2>Encontrar Jogo</h2>
          <p className="subtitle">Selecione o ritmo de jogo e encontraremos um adversário.</p>
        </div>



        {error && (
          <div className="error-message">
            <span className="error-icon">⚠</span>
            {error}
          </div>
        )}

        {!isInQueue ? (
          <div className="search-form">
            {/* Time control selection */}
            <div className="form-group">
              <label>Ritmo de jogo</label>
              <div className="color-options" style={{ gridTemplateColumns: 'repeat(2,1fr)' }}>
                {TIME_CONTROLS.map(tc => (
                  <button
                    key={tc.id}
                    type="button"
                    className={`color-option${selectedTimeControl === tc.id ? ' active' : ''}`}
                    onClick={() => setSelectedTimeControl(tc.id)}
                    style={{ flexDirection: 'row', justifyContent: 'flex-start', gap: '1rem', textAlign: 'left' }}
                  >
                    <span
                      className="piece-icon random-piece"
                      style={{ fontSize: '1.25rem', width: '2.5rem', height: '2.5rem', flexShrink: 0 }}
                    >
                      {tc.icon}
                    </span>
                    <span>
                      <span style={{ display: 'flex', alignItems: 'baseline', gap: '0.375rem', marginBottom: '0.125rem' }}>
                        <strong style={{ fontSize: '0.9375rem', color: 'var(--fg, #0f0f0f)' }}>{tc.label}</strong>
                        <span style={{ fontSize: '0.8125rem', color: 'var(--muted-fg, #6b6b6b)' }}>{tc.time}</span>
                      </span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--muted-fg, #6b6b6b)' }}>{tc.description}</span>
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Color selection */}
            <div className="form-group">
              <label>Cor preferida</label>
              <div className="color-options">
                <button
                  type="button"
                  className={`color-option${preferredColor === 'WHITE' ? ' active' : ''}`}
                  onClick={() => setPreferredColor('WHITE')}
                >
                  <span className="piece-icon white-piece">♔</span>
                  <span className="color-label">Brancas</span>
                </button>
                <button
                  type="button"
                  className={`color-option${preferredColor === 'BLACK' ? ' active' : ''}`}
                  onClick={() => setPreferredColor('BLACK')}
                >
                  <span className="piece-icon black-piece">♚</span>
                  <span className="color-label">Pretas</span>
                </button>
                <button
                  type="button"
                  className={`color-option${preferredColor === 'ANY' ? ' active' : ''}`}
                  onClick={() => setPreferredColor('ANY')}
                >
                  <span className="piece-icon random-piece">⚡</span>
                  <span className="color-label">Aleatório</span>
                </button>
              </div>
            </div>

            <button
              className="start-search-button"
              onClick={handleFindMatch}
              disabled={!selectedTimeControl}
            >
              <span className="button-text">
                {selectedTimeControl ? 'Encontrar Jogo' : 'Selecione o Ritmo'}
              </span>
              <span className="button-icon">→</span>
            </button>

            {/* Player stats */}
            <div className="player-stats">
              <div className="stat-item">
                <span className="stat-icon">⭐</span>
                <span className="stat-label">Rating ELO</span>
                <span className="stat-value">{user.elo_rating || '—'}</span>
              </div>
              <div className="stat-item">
                <span className="stat-icon">🎮</span>
                <span className="stat-label">Jogos</span>
                <span className="stat-value">{user.games_played || 0}</span>
              </div>
              <div className="stat-item">
                <span className="stat-icon">🏆</span>
                <span className="stat-label">Vitórias</span>
                <span className="stat-value">
                  {user.games_played
                    ? `${Math.round(((user.games_won || 0) / user.games_played) * 100)}%`
                    : '—'}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="searching-container">
            <div className="searching-animation">
              <div className="chess-piece-animated">♞</div>
              <div className="searching-pulse" />
            </div>

            <h3>À procura de adversário…</h3>
            <p className="searching-subtitle">A encontrar um jogador com nível semelhante</p>

            <div className="queue-info">
              <div className="info-item">
                <span className="info-label">Tempo em fila</span>
                <span className="info-value time-display">
                  <SearchingTimer seconds={timeInQueue} />
                </span>
              </div>
              {queuePosition !== null && (
                <div className="info-item">
                  <span className="info-label">Posição</span>
                  <span className="info-value">#{queuePosition}</span>
                </div>
              )}
              {estimatedWaitTime !== null && (
                <div className="info-item">
                  <span className="info-label">Espera estimada</span>
                  <span className="info-value">~{estimatedWaitTime}s</span>
                </div>
              )}
            </div>

            <button className="cancel-search-button" onClick={handleCancelSearch}>
              Cancelar Procura
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Matchmaking;