import { useState, useRef, useEffect, useCallback } from 'react';
import { Chess } from 'chess.js';
import ChessBoard from '../ChessBoard/ChessBoard';
import GameControls from '../GameControls/GameControls';
import MoveHistory from '../MoveHistory/MoveHistory';
import CapturedPieces from '../CapturedPieces/CapturedPieces';
import CameraMode from '../CameraMode/CameraMode';
import type { MovePair } from '../../types';
import './Game.css';

import { useParams } from 'react-router-dom';
import api from '../../services/api';

const Game: React.FC = () => {
  console.log('[Game] Rendered');
  const { gameId } = useParams<{ gameId: string }>();
  console.log('[Game] gameId:', gameId);

  // All state declarations at the top
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [turnError, setTurnError] = useState<string | null>(null);
  const [moveHistory, setMoveHistory] = useState<MovePair[]>([]);
  const [currentMoveIndex, setCurrentMoveIndex] = useState(-1);
  const [capturedPieces, setCapturedPieces] = useState({
    white: [] as string[],
    black: [] as string[]
  });
  const [autoFlipBoard, setAutoFlipBoard] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [cameraMode, setCameraMode] = useState(false); // Modo câmara para jogos locais
  const [gameData, setGameData] = useState<any>(null);
  const [currentUser, setCurrentUser] = useState<any>(null);

  // Refs after state
  const wsRef = useRef<WebSocket | null>(null);
  const gameRef = useRef(new Chess());
  const containerRef = useRef<HTMLDivElement>(null);

  // Fetch initial game state from backend
  useEffect(() => {
    console.log('[Game] useEffect (load game) fired, gameId:', gameId);

    // For local games (no gameId), initialize a new chess game
    if (!gameId) {
      console.log('[Game] Local game - initializing new chess game');
      gameRef.current = new Chess();
      setMoveHistory([]);
      setCurrentMoveIndex(-1);
      setCapturedPieces({ white: [], black: [] });
      setLoading(false);
      console.log('[Game] Local game initialized successfully');
      return;
    }

    // For online games, fetch from backend
    setLoading(true);
    setError(null);

    // Fetch both game data and current user data for turn validation
    Promise.all([
      api.get(`/game/${gameId}/`),
      api.get('/users/me/')
    ]).then(([gameResponse, userResponse]) => {
      const data = gameResponse.data;
      const userData = userResponse.data;
      console.log('[Game] API response for /game/' + gameId, data);
      try {
        console.log('[Game] Before FEN load:', data.fen_string);
        if (data.fen_string) {
          gameRef.current.load(data.fen_string);
          console.log('[Game] After FEN load:', gameRef.current.fen());
        }
        console.log('[Game] Before setMoveHistory:', data.moves);
        // Fully defensive move history construction
        const moves = Array.isArray(data.moves) ? data.moves : [];
        const movePairs: MovePair[] = [];
        for (let i = 0; i < moves.length; i += 2) {
          movePairs.push({
            white: moves[i]?.move_san || '',
            black: moves[i + 1]?.move_san || '',
          });
        }
        setMoveHistory(movePairs);
        setCurrentMoveIndex(moves.length > 0 ? moves.length - 1 : -1);
        console.log('[Game] After setCurrentMoveIndex');

        // Store game data and current user for turn validation
        setGameData(data);
        setCurrentUser(userData);
        console.log('[Game] Game data and user data stored for turn validation');

        setLoading(false);
        console.log('[Game] setLoading(false) called (success)');
      } catch (err) {
        console.error('[Game] ERROR in .then() block:', err);
        setError('Erro ao buscar estado da partida');
        setLoading(false);
      }
    }).catch((err) => {
      setError('Erro ao buscar estado da partida');
      console.error('[Game] API error for /game/' + gameId, err);
      setLoading(false);
      console.log('[Game] setLoading(false) called (error)');
    });
  }, [gameId]);

  // WebSocket integration for real-time moves between players
  useEffect(() => {
    // Only enable WebSocket for online games (with gameId)
    if (!gameId) return;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${wsProtocol}://${window.location.hostname}:8000/ws/game/${gameId}/`;
    console.log('[Game] Setting up WebSocket for game:', gameId, wsUrl);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[Game] WebSocket connected for game:', gameId);
    };

    ws.onerror = (error) => {
      console.error('[Game] WebSocket error:', error);
    };

    ws.onclose = (event) => {
      console.log('[Game] WebSocket closed:', event.code, event.reason);
      if (wsRef.current === ws) {
        wsRef.current = null;
      }
    };

    const handleWebSocketMessage = (event: MessageEvent) => {
      console.log('[Game] WebSocket message received:', event.data);
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'move' && data.move && data.move.san) {
          const san: string = data.move.san;
          const fen: string | undefined = data.move.fen;

          const currentFen = gameRef.current.fen();
          // If the current FEN already matches the server FEN, this client has
          // already applied this move locally (echo of own move) – skip.
          if (fen && currentFen === fen) {
            return;
          }

          const moveResult = gameRef.current.move(san);
          if (!moveResult) {
            console.warn('[Game] Failed to apply move from WebSocket:', san);
            return;
          }

          // Update local move history (mirror of handleMove logic)
          setMoveHistory((prevHistory) => {
            const currentIndex = prevHistory.length - 1;
            const newMoveHistory = prevHistory.slice(0, currentIndex + 1);
            const lastMove =
              newMoveHistory[newMoveHistory.length - 1] || { white: '', black: '' };

            if (gameRef.current.turn() === 'b') {
              // White has just moved
              lastMove.white = moveResult.san || san;
            } else {
              // Black has just moved
              lastMove.black = moveResult.san || san;
              newMoveHistory.push({ ...lastMove });
            }

            return newMoveHistory;
          });

          setCurrentMoveIndex((prev) => prev + 1);

          // Update captured pieces for remote moves
          if (moveResult.captured) {
            const color = gameRef.current.turn() === 'w' ? 'black' : 'white';
            setCapturedPieces((prev) => ({
              ...prev,
              [color]: [...prev[color], moveResult.captured as string],
            }));
          }
        } else if (data.type === 'board_update') {
          // Vision AI board updates are handled in a dedicated interface.
          // For the classic digital-vs-digital game view we only log them.
          console.log('[Game] board_update message (ignored in Game view):', data);
        } else if (data.type === 'chat') {
          console.log('[Game] Received chat message:', data.message, 'from:', data.user);
        }
      } catch (e) {
        console.error('[Game] Error processing WebSocket message:', e);
      }
    };

    ws.onmessage = handleWebSocketMessage;

    return () => {
      console.log('[Game] Cleaning up WebSocket for game:', gameId);
      ws.close();
      if (wsRef.current === ws) {
        wsRef.current = null;
      }
    };
  }, [gameId]);

  /**
   * Atualizar a posição do tabuleiro com o FEN recebido da deteção por câmara.
   * (Hook deve ficar antes dos early returns para respeitar as regras dos hooks do React)
   */
  const handleFenUpdate = useCallback((fen: string) => {
    try {
      gameRef.current.load(fen);
      // Limpar histórico — a posição vem da câmara, não de jogadas
      setMoveHistory([]);
      setCurrentMoveIndex(-1);
      setCapturedPieces({ white: [], black: [] });
      console.log('[Game] FEN atualizado pela câmara:', fen);
    } catch (e) {
      console.error('[Game] FEN inválido recebido da câmara:', fen, e);
    }
  }, []);

  /**
   * Alternar modo câmara (apenas para jogos locais).
   */
  const toggleCameraMode = useCallback(() => {
    setCameraMode(prev => !prev);
  }, []);

  // ... (all other hooks and logic) ...

  if (loading) {
    return <div className="game-loading">A carregar partida...</div>;
  }
  if (error) {
    return <div className="game-error">{error}</div>;
  }

  // Handle move from ChessBoard component
  const handleMove = (from: string, to: string, promotion?: string) => {
    // Turn validation for online games - MUST be checked FIRST before any game state changes
    if (gameId && gameData && currentUser) {
      const isWhiteTurn = gameRef.current.turn() === 'w';

      console.log('[Game] Turn validation - Is white turn:', isWhiteTurn);
      console.log(
        '[Game] Current user:',
        currentUser.username,
        'White player:',
        gameData.white_player?.username,
        'Black player:',
        gameData.black_player?.username
      );

      if (isWhiteTurn && gameData.white_player?.id !== currentUser.id) {
        console.log('[Game] Move blocked - Not white\'s turn');
        setTurnError('São as brancas a jogar, mas está a jogar com as pretas');
        setTimeout(() => setTurnError(null), 5000);
        return false; // Block move completely - no chess.js execution
      } else if (!isWhiteTurn && gameData.black_player?.id !== currentUser.id) {
        console.log('[Game] Move blocked - Not black\'s turn');
        setTurnError('São as pretas a jogar, mas está a jogar com as brancas');
        setTimeout(() => setTurnError(null), 5000);
        return false; // Block move completely - no chess.js execution
      }
    }

    // Local chess.js validation - only executed if turn validation passes
    let move;
    try {
      move = gameRef.current.move({ from, to, promotion: promotion?.[1]?.toLowerCase() as 'q' | 'r' | 'b' | 'n' | undefined });
    } catch (e) {
      setError('Jogada inválida');
      return false;
    }
    if (!move) return false;
    // Enviar movimento para o backend (REST e WebSocket)
    if (gameId) {
      api.post(`/game/${gameId}/move/`, {
        move_san: move.san,
        fen_after: gameRef.current.fen(),
      }).catch(() => setError('Erro ao enviar jogada para o servidor'));
      // WebSocket
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'move',
          move_san: move.san,
          fen_after: gameRef.current.fen(),
        }));
      }
    }
    // Atualizar histórico local
    setMoveHistory(prevHistory => {
      const currentIndex = prevHistory.length - 1;
      const newMoveHistory = prevHistory.slice(0, currentIndex + 1);
      const lastMove = newMoveHistory[newMoveHistory.length - 1] || { white: '', black: '' };
      if (gameRef.current.turn() === 'b') {
        lastMove.white = move.san || '';
      } else {
        lastMove.black = move.san || '';
        newMoveHistory.push({ ...lastMove });
      }
      return newMoveHistory;
    });
    setCurrentMoveIndex(prev => prev + 1);
    if (move.captured) {
      const color = gameRef.current.turn() === 'w' ? 'black' : 'white';
      setCapturedPieces(prev => ({ ...prev, [color]: [...prev[color], move.captured as string] }));
    }

    // Update gameData to reflect the new move count for correct turn logic
    if (gameId && gameData) {
      setGameData((prevGameData: any) => ({
        ...prevGameData,
        moves: [...(prevGameData.moves || []), {
          move_san: move.san,
          fen_after: gameRef.current.fen(),
          move_number: (prevGameData.moves?.length || 0) + 1
        }]
      }));
      console.log('[Game] Updated gameData with new move, new move count:', (gameData.moves?.length || 0) + 1);
    }

    return true;
  };

  // Handle undo last move
  const handleUndo = () => {
    setCurrentMoveIndex(prevIndex => {
      if (prevIndex >= 0) {
        return prevIndex - 1;
      }
      return prevIndex;
    });

    setMoveHistory(prevHistory => {
      if (prevHistory.length > 0) {
        const newMoveHistory = [...prevHistory];
        newMoveHistory.splice(-1, 1); // Remove last move

        // Reset game and replay all moves except the last one
        gameRef.current = new Chess();

        for (let i = 0; i < newMoveHistory.length; i++) {
          const movePair = newMoveHistory[i];
          if (movePair.white) gameRef.current.move(movePair.white as any);
          if (movePair.black) gameRef.current.move(movePair.black as any);
        }

        return newMoveHistory;
      }
      return prevHistory;
    });
  };

  // Start a new game
  const handleNewGame = () => {
    gameRef.current = new Chess();
    setMoveHistory([]);
    setCurrentMoveIndex(-1);
    setCapturedPieces({ white: [], black: [] });
    setCameraMode(false); // Desativar câmara ao iniciar novo jogo
  };

  // Toggle auto-flip
  const toggleAutoFlip = () => {
    setAutoFlipBoard(prev => !prev);
  };

  // Toggle fullscreen
  const toggleFullscreen = () => {
    const element = containerRef.current;
    if (!element) return;

    if (!document.fullscreenElement) {
      if (element.requestFullscreen) {
        element.requestFullscreen().then(() => setIsFullscreen(true)).catch(console.error);
      }
    } else if (document.exitFullscreen) {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(console.error);
    }
  };

  // Auto-flip logic moved inline to prevent useEffect infinite loops


  // Get the last move for highlighting
  const getLastMove = (): string | null => {
    if (currentMoveIndex < 0) return null;
    const lastMovePair = moveHistory[currentMoveIndex];
    if (!lastMovePair) return null;

    const lastMove = gameRef.current.turn() === 'w' ? lastMovePair.black : lastMovePair.white;
    return lastMove || null;
  };

  // Get piece symbol for display
  const getPieceSymbol = (piece: { type: string; color: string }) => {
    const symbols: Record<string, string> = {
      p: '♟', n: '♞', b: '♝', r: '♜', q: '♛', k: '♚',
      P: '♙', N: '♘', B: '♗', R: '♖', Q: '♕', K: '♔',
    };
    const pieceKey = piece.color === 'b' ? piece.type.toLowerCase() : piece.type.toUpperCase();
    return symbols[pieceKey] || '';
  };

  // Calculate material value of captured pieces
  const calculateMaterial = (pieces: string[]) => {
    const pieceValues: Record<string, number> = {
      p: 1, n: 3, b: 3, r: 5, q: 9,
      P: 1, N: 3, B: 3, R: 5, Q: 9,
    };
    return pieces.reduce((sum, piece) => sum + (pieceValues[piece] || 0), 0);
  };

  // Values will be calculated inline in JSX to prevent re-render issues

  // Handle move click
  const handleMoveClick = (index: number) => {
    // Reset game and replay moves up to the clicked index
    gameRef.current = new Chess();
    const newMoveHistory = moveHistory.slice(0, index + 1);

    for (let i = 0; i < newMoveHistory.length; i++) {
      const movePair = newMoveHistory[i];
      if (movePair.white) gameRef.current.move(movePair.white as any);
      if (movePair.black) gameRef.current.move(movePair.black as any);
    }

    setCurrentMoveIndex(index);
  };

  // Determinar se o utilizador pode interagir com o tabuleiro
  const canUserInteract = () => {
    // No modo câmara, desativar interação manual
    if (cameraMode) return false;

    // Para jogos locais, permitir sempre interação
    if (!gameId || !gameData || !currentUser) {
      return true;
    }

    const isWhiteTurn = gameRef.current.turn() === 'w';

    // Verificar se é a vez do utilizador atual com base no estado do tabuleiro
    if (isWhiteTurn && gameData.white_player?.id === currentUser.id) {
      return true;
    } else if (!isWhiteTurn && gameData.black_player?.id === currentUser.id) {
      return true;
    }

    return false;
  };



  // Wrapper for ChessBoard onMove prop
  const handleChessBoardMove = (move: { from: string; to: string; promotion?: string }) => {
    const moveResult = handleMove(move.from, move.to, move.promotion);
    if (!moveResult) {
      // Move was blocked (turn validation failed or invalid move)
      console.log('[Game] Move blocked by handleMove, preventing ChessBoard update');
      return false;
    }
    return true;
  };

  return (
    <div ref={containerRef} className={`game-container ${isFullscreen ? 'fullscreen' : ''}`}>
      {/* Turn validation error overlay */}
      {turnError && (
        <div className="turn-error-overlay" style={{
          position: 'fixed',
          top: '20px',
          left: '50%',
          transform: 'translateX(-50%)',
          backgroundColor: '#f44336',
          color: 'white',
          padding: '12px 24px',
          borderRadius: '8px',
          zIndex: 1000,
          boxShadow: '0 4px 8px rgba(0,0,0,0.2)'
        }}>
          {turnError}
        </div>
      )}
      <div className="game-board">
        <div className="board-container">
          <GameControls
            autoFlipBoard={gameId ? false : autoFlipBoard}
            currentMoveIndex={currentMoveIndex}
            onToggleAutoFlip={gameId ? undefined : toggleAutoFlip}
            onUndo={gameId ? undefined : handleUndo}
            onNewGame={gameId ? undefined : handleNewGame}
            onToggleFullscreen={toggleFullscreen}
            isFullscreen={isFullscreen}
          />

          {/* Botão do modo câmara — apenas para jogos locais */}
          {!gameId && (
            <button
              className={`camera-toggle-btn ${cameraMode ? 'camera-toggle-btn--active' : ''}`}
              onClick={toggleCameraMode}
              title={cameraMode ? 'Desativar câmara' : 'Ativar câmara para deteção do tabuleiro'}
            >
              {cameraMode ? '📷 Câmara Ativa' : '📷 Câmara'}
            </button>
          )}

          <ChessBoard
            position={gameRef.current.fen()}
            orientation={
              gameId
                ? (gameData?.black_player?.id === currentUser?.id ? 'black' : 'white')
                : (autoFlipBoard && gameRef.current.turn() === 'b' ? 'black' : 'white')
            }
            onMove={handleChessBoardMove}
            lastMove={getLastMove()}
            interactive={canUserInteract()}
          />
        </div>

        <div className="game-info">
          <div className="material-count">
            <div>Brancas: {calculateMaterial(capturedPieces.black)}</div>
            <div>Pretas: {calculateMaterial(capturedPieces.white)}</div>
          </div>

          <MoveHistory
            moveHistory={moveHistory}
            currentMoveIndex={currentMoveIndex}
            onMoveClick={handleMoveClick}
          />

          <CapturedPieces
            capturedPieces={capturedPieces}
            getPieceSymbol={getPieceSymbol}
            calculateMaterial={calculateMaterial}
          />

          {/* Painel da câmara — apenas para jogos locais */}
          {!gameId && (
            <CameraMode
              active={cameraMode}
              onFenDetected={handleFenUpdate}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default Game;
