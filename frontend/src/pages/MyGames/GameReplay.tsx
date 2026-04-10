import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import ChessBoard from '../../components/ChessBoard/ChessBoard';
import { games } from '../../services/api';
import './GameReplay.css';

interface ReplayData {
  game_id: number;
  game_type: string;
  status: string;
  result: string | null;
  created_at: string;
  white_player: string;
  black_player: string | null;
  fens: string[];
  total_moves: number;
}

const GameReplay: React.FC = () => {
  const { gameId } = useParams<{ gameId: string }>();
  const [data, setData] = useState<ReplayData | null>(null);
  const [currentMove, setCurrentMove] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    if (!gameId) return;
    const load = async () => {
      setLoading(true);
      try {
        const replay = await games.getGameReplay(parseInt(gameId));
        setData(replay);
        setCurrentMove(0);
      } catch (err) {
        setError('Não foi possível carregar a partida.');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [gameId]);

  // Auto-play
  useEffect(() => {
    if (!isPlaying || !data) return;
    if (currentMove >= data.fens.length - 1) {
      setIsPlaying(false);
      return;
    }
    const timer = setTimeout(() => {
      setCurrentMove((m) => m + 1);
    }, 1000);
    return () => clearTimeout(timer);
  }, [isPlaying, currentMove, data]);

  // Keyboard navigation
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (!data) return;
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        setCurrentMove((m) => Math.max(0, m - 1));
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        setCurrentMove((m) => Math.min(data.fens.length - 1, m + 1));
      } else if (e.key === 'Home') {
        e.preventDefault();
        setCurrentMove(0);
      } else if (e.key === 'End') {
        e.preventDefault();
        setCurrentMove(data.fens.length - 1);
      } else if (e.key === ' ') {
        e.preventDefault();
        setIsPlaying((p) => !p);
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [data]);

  const getResultLabel = () => {
    if (!data) return '';
    if (data.status === 'IN_PROGRESS') return 'Em Curso';
    const map: Record<string, string> = {
      WHITE_WIN: '1-0', BLACK_WIN: '0-1', DRAW: '½-½',
    };
    return data.result ? map[data.result] || data.result : '';
  };

  if (loading) {
    return (
      <div className="replay-page">
        <div className="replay-loading">
          <div className="spinner" />
          <span>A carregar partida...</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="replay-page">
        <div className="replay-error">
          <span>❌</span>
          <p>{error || 'Partida não encontrada.'}</p>
          <Link to="/my-games" className="btn btn-secondary">
            ← Voltar
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="replay-page">
      {/* Header */}
      <div className="replay-header">
        <Link to="/my-games" className="replay-back">← Minhas Partidas</Link>
        <div className="replay-title-row">
          <h1>
            {data.game_type === 'LIVE_CAPTURE' ? '📷' : '🌐'}{' '}
            Partida #{data.game_id}
          </h1>
          {getResultLabel() && (
            <span className="replay-result">{getResultLabel()}</span>
          )}
        </div>
        <div className="replay-meta">
          <span>⬜ {data.white_player}</span>
          <span className="replay-vs">vs</span>
          <span>⬛ {data.black_player || '—'}</span>
          <span className="replay-separator">·</span>
          <span>{data.total_moves} jogadas</span>
          <span className="replay-separator">·</span>
          <span>
            {new Date(data.created_at).toLocaleDateString('pt-PT', {
              day: '2-digit', month: 'short', year: 'numeric',
            })}
          </span>
        </div>
      </div>

      {/* Main content */}
      <div className="replay-content">
        {/* Board */}
        <div className="replay-board-wrapper">
          <ChessBoard
            position={data.fens[currentMove]}
            orientation="white"
            onMove={() => {}}
            lastMove={null}
            interactive={false}
          />
        </div>

        {/* Controls + Move list */}
        <div className="replay-sidebar">
          {/* Navigation controls */}
          <div className="replay-controls">
            <button
              className="control-btn"
              onClick={() => setCurrentMove(0)}
              disabled={currentMove === 0}
              title="Primeira jogada (Home)"
            >
              ⏮
            </button>
            <button
              className="control-btn"
              onClick={() => setCurrentMove((m) => Math.max(0, m - 1))}
              disabled={currentMove === 0}
              title="Jogada anterior (←)"
            >
              ◀
            </button>
            <button
              className={`control-btn play-btn ${isPlaying ? 'playing' : ''}`}
              onClick={() => setIsPlaying((p) => !p)}
              title="Reproduzir (Espaço)"
            >
              {isPlaying ? '⏸' : '▶'}
            </button>
            <button
              className="control-btn"
              onClick={() => setCurrentMove((m) => Math.min(data.fens.length - 1, m + 1))}
              disabled={currentMove === data.fens.length - 1}
              title="Próxima jogada (→)"
            >
              ▶
            </button>
            <button
              className="control-btn"
              onClick={() => setCurrentMove(data.fens.length - 1)}
              disabled={currentMove === data.fens.length - 1}
              title="Última jogada (End)"
            >
              ⏭
            </button>
          </div>

          {/* Move counter */}
          <div className="replay-move-counter">
            Jogada {currentMove} / {data.fens.length - 1}
          </div>

          {/* Move list */}
          <div className="replay-move-list">
            <div
              className={`move-item ${currentMove === 0 ? 'active' : ''}`}
              onClick={() => setCurrentMove(0)}
            >
              <span className="move-number">0.</span>
              <span className="move-text">Posição Inicial</span>
            </div>
            {data.fens.slice(1).map((_, i) => {
              const moveIdx = i + 1;
              const isWhite = i % 2 === 0;
              const displayNumber = Math.floor(i / 2) + 1;
              return (
                <div
                  key={moveIdx}
                  className={`move-item ${currentMove === moveIdx ? 'active' : ''}`}
                  onClick={() => setCurrentMove(moveIdx)}
                >
                  {isWhite && <span className="move-number">{displayNumber}.</span>}
                  {!isWhite && <span className="move-number" style={{ visibility: 'hidden' }}>{displayNumber}.</span>}
                  <span className="move-color">{isWhite ? '⬜' : '⬛'}</span>
                  <span className="move-text">Jogada {moveIdx}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default GameReplay;
