import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { games } from '../../services/api';
import './MyGames.css';

interface GameItem {
  id: number;
  white_player: { username: string };
  black_player: { username: string } | null;
  status: string;
  result: string | null;
  game_type: string;
  created_at: string;
  move_count?: number;
}

type FilterType = 'ALL' | 'ONLINE' | 'LIVE_CAPTURE';

const MyGames: React.FC = () => {
  const [gameList, setGameList] = useState<GameItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FilterType>('ALL');
  const [deleteTarget, setDeleteTarget] = useState<GameItem | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchGames();
  }, [filter]);

  const fetchGames = async () => {
    setLoading(true);
    try {
      const typeParam = filter === 'ALL' ? undefined : filter;
      const data = await games.getMyGames(typeParam);
      setGameList(data);
    } catch (err) {
      console.error('Erro ao carregar partidas:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await games.deleteGame(deleteTarget.id);
      setGameList((prev) => prev.filter((g) => g.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err) {
      console.error('Erro ao apagar partida:', err);
    } finally {
      setDeleting(false);
    }
  };

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleDateString('pt-PT', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };

  const getResultLabel = (game: GameItem) => {
    if (game.status === 'IN_PROGRESS') return 'Em Curso';
    if (!game.result) return 'Sem Resultado';
    const map: Record<string, string> = {
      WHITE_WIN: 'Brancas Vencem',
      BLACK_WIN: 'Pretas Vencem',
      DRAW: 'Empate',
    };
    return map[game.result] || game.result;
  };

  const getResultClass = (game: GameItem) => {
    if (game.status === 'IN_PROGRESS') return 'status-live';
    if (!game.result) return '';
    if (game.result === 'DRAW') return 'status-draw';
    return 'status-finished';
  };

  const getTypeIcon = (type: string) => {
    return type === 'LIVE_CAPTURE' ? '📷' : '🌐';
  };

  const getTypeLabel = (type: string) => {
    return type === 'LIVE_CAPTURE' ? 'Captada' : 'Online';
  };

  return (
    <div className="my-games-page">
      <div className="my-games-header">
        <h1>Minhas Partidas</h1>
        <p className="my-games-subtitle">
          Revê as tuas partidas anteriores e analisa as jogadas.
        </p>
      </div>

      {/* Filtros */}
      <div className="my-games-filters">
        {(['ALL', 'ONLINE', 'LIVE_CAPTURE'] as FilterType[]).map((f) => (
          <button
            key={f}
            className={`filter-btn ${filter === f ? 'active' : ''}`}
            onClick={() => setFilter(f)}
          >
            {f === 'ALL' ? '📋 Todas' : f === 'ONLINE' ? '🌐 Online' : '📷 Captadas'}
          </button>
        ))}
      </div>

      {/* Lista de partidas */}
      <div className="my-games-list">
        {loading ? (
          <div className="my-games-loading">
            <div className="spinner" />
            <span>A carregar partidas...</span>
          </div>
        ) : gameList.length === 0 ? (
          <div className="my-games-empty">
            <span className="empty-icon">♟️</span>
            <h3>Nenhuma partida encontrada</h3>
            <p>As tuas partidas aparecerão aqui quando jogares ou captares uma partida com o telemóvel.</p>
          </div>
        ) : (
          gameList.map((game) => (
            <div key={game.id} className="game-card-wrapper">
              <Link
                to={`/my-games/${game.id}`}
                className="game-card"
              >
                <div className="game-card-left">
                  <span className="game-type-badge" title={getTypeLabel(game.game_type)}>
                    {getTypeIcon(game.game_type)}
                  </span>
                  <div className="game-card-info">
                    <div className="game-card-players">
                      <span className="player-white">⬜ {game.white_player.username}</span>
                      <span className="vs">vs</span>
                      <span className="player-black">⬛ {game.black_player?.username || '—'}</span>
                    </div>
                    <div className="game-card-meta">
                      <span className="game-date">{formatDate(game.created_at)}</span>
                      {game.move_count !== undefined && (
                        <span className="game-moves">{game.move_count} jogadas</span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="game-card-right">
                  <span className={`game-result ${getResultClass(game)}`}>
                    {getResultLabel(game)}
                  </span>
                  <span className="game-arrow">→</span>
                </div>
              </Link>
              <button
                className="game-delete-btn"
                title="Apagar partida"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setDeleteTarget(game);
                }}
              >
                🗑️
              </button>
            </div>
          ))
        )}
      </div>

      {/* Modal de confirmação */}
      {deleteTarget && (
        <div className="delete-modal-overlay" onClick={() => !deleting && setDeleteTarget(null)}>
          <div className="delete-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Apagar Partida?</h3>
            <p>
              Tens a certeza que queres apagar a partida #{deleteTarget.id}?
              Esta ação é irreversível.
            </p>
            <div className="delete-modal-actions">
              <button
                className="btn btn-secondary"
                onClick={() => setDeleteTarget(null)}
                disabled={deleting}
              >
                Cancelar
              </button>
              <button
                className="btn btn-danger"
                onClick={handleDelete}
                disabled={deleting}
              >
                {deleting ? 'A apagar...' : 'Apagar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MyGames;
