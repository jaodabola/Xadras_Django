import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import ChessBoard from '../../components/ChessBoard/ChessBoard';
import { games } from '../../services/api';
import { IconAlert, IconCamera, IconGlobe, IconPlay, IconPause, IconSkipBack, IconSkipForward, IconStepBack } from '../../components/Icons/Icons';
import './GameReplay.css';
import EvaluationBar from '../../components/EvaluationBar/EvaluationBar';
import { useStockfish } from '../../hooks/useStockfish';

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

  // Stockfish Engine
  const [engineEnabled, setEngineEnabled] = useState(false);
  const { evaluation, isEngineReady, analyzeFen, stopAnalysis } = useStockfish();

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

  // Handle Engine triggering
  useEffect(() => {
    if (engineEnabled && data && data.fens[currentMove]) {
      analyzeFen(data.fens[currentMove]); // Análise infinita (até parar)
    } else {
      stopAnalysis();
    }
  }, [engineEnabled, data, currentMove, analyzeFen, stopAnalysis]);

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
          <IconAlert size={48} />
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
          <h1 className="flex-center-gap">
            {data.game_type === 'LIVE_CAPTURE' ? <IconCamera size={24} /> : <IconGlobe size={24} />}
            Partida #{data.game_id}
          </h1>
          {getResultLabel() && (
            <span className="replay-result">{getResultLabel()}</span>
          )}
        </div>
        <div className="replay-meta">
          <span className="flex-center-gap"><span className="color-dot white-dot"></span> {data.white_player}</span>
          <span className="replay-vs">vs</span>
          <span className="flex-center-gap"><span className="color-dot black-dot"></span> {data.black_player || '—'}</span>
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
        {/* Board and Evaluation */}
        <div style={{ display: 'flex', gap: '8px', alignItems: 'stretch' }}>
          {engineEnabled && <EvaluationBar evaluation={evaluation} />}
          <div className="replay-board-wrapper" style={{ flexGrow: 1, minWidth: 0, margin: 0 }}>
            <ChessBoard
              position={data.fens[currentMove]}
              orientation="white"
              onMove={() => {}}
              lastMove={null}
              interactive={false}
              bestMove={engineEnabled ? evaluation?.bestMove : null}
            />
          </div>
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
              <IconSkipBack size={16} />
            </button>
            <button
              className="control-btn"
              onClick={() => setCurrentMove((m) => Math.max(0, m - 1))}
              disabled={currentMove === 0}
              title="Jogada anterior (←)"
            >
              <IconStepBack size={16} />
            </button>
            <button
              className={`control-btn play-btn ${isPlaying ? 'playing' : ''}`}
              onClick={() => setIsPlaying((p) => !p)}
              title="Reproduzir (Espaço)"
            >
              {isPlaying ? <IconPause size={16} /> : <IconPlay size={16} />}
            </button>
            <button
              className="control-btn"
              onClick={() => setCurrentMove((m) => Math.min(data.fens.length - 1, m + 1))}
              disabled={currentMove === data.fens.length - 1}
              title="Próxima jogada (→)"
            >
              <IconPlay size={16} />
            </button>
            <button
              className="control-btn"
              onClick={() => setCurrentMove(data.fens.length - 1)}
              disabled={currentMove === data.fens.length - 1}
              title="Última jogada (End)"
            >
              <IconSkipForward size={16} />
            </button>

            <div style={{ width: '1px', alignSelf: 'stretch', backgroundColor: 'var(--border-color, #ccc)', margin: '0 4px' }}></div>
            
            <button
               className={`control-btn ${engineEnabled ? 'playing' : ''}`}
               onClick={() => setEngineEnabled(prev => !prev)}
               disabled={!isEngineReady}
               title="Ligar Análise do Motor"
               style={{ width: 'auto', padding: '0 12px', fontSize: '0.85rem', fontWeight: 'bold' }}
            >
               {engineEnabled ? `🧠 ON (D${evaluation?.depth || 0})` : '💤 MOTOR'}
            </button>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '0.5rem 0' }}>
            {/* Move counter */}
            <div className="replay-move-counter" style={{ margin: 0 }}>
              Jogada {currentMove} / {data.fens.length - 1}
            </div>
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
                  <span className={`color-dot ${isWhite ? 'white-dot' : 'black-dot'}`} style={{ marginRight: '8px' }}></span>
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
