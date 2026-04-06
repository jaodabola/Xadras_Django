/**
 * CameraMode – Componente React para deteção de tabuleiro via app externa.
 *
 * Gera um session_id único, liga-se ao WebSocket do backend,
 * e fica à escuta de FEN enviados pela app do telemóvel.
 *
 * Já não captura vídeo da webcam do browser.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import './CameraMode.css';

interface CameraModeProps {
  /** Chamado quando o backend devolve um FEN válido */
  onFenDetected: (fen: string) => void;
  /** Se true, o componente está ativo e visível */
  active: boolean;
}

type WSState = 'disconnected' | 'connecting' | 'connected';

/**
 * Gera um identificador de sessão curto e legível.
 */
const generateSessionId = (): string => {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; // Sem I, O, 0, 1 para evitar confusão
  let result = '';
  for (let i = 0; i < 6; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
};

const CameraMode: React.FC<CameraModeProps> = ({ onFenDetected, active }) => {
  // -- Estado --
  const [sessionId] = useState(() => generateSessionId());
  const [wsState, setWsState] = useState<WSState>('disconnected');
  const [lastFen, setLastFen] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // -- Referências --
  const wsRef = useRef<WebSocket | null>(null);
  const lastFenRef = useRef<string>('');

  /**
   * Ligar ao WebSocket do backend com o session_id.
   */
  const connectWebSocket = useCallback(() => {
    // Fechar ligação anterior se existir
    if (wsRef.current) {
      wsRef.current.close();
    }

    setWsState('connecting');
    setError(null);

    const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${wsProtocol}://${window.location.hostname}:8000/ws/live-board/?session=${sessionId}`;

    console.log('[CameraMode] A ligar ao WebSocket:', wsUrl);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[CameraMode] WebSocket ligado');
      setWsState('connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'detection_result') {
          // FEN recebido da app do telemóvel via backend
          if (data.board_detected && data.fen && data.fen !== lastFenRef.current) {
            lastFenRef.current = data.fen;
            setLastFen(data.fen);
            onFenDetected(data.fen);
          }
        } else if (data.type === 'connection_established') {
          console.log('[CameraMode] Ligação confirmada:', data.message);
        } else if (data.type === 'error') {
          console.error('[CameraMode] Erro do servidor:', data.message);
          setError(data.message);
        }
      } catch (e) {
        console.error('[CameraMode] Erro ao processar mensagem WS:', e);
      }
    };

    ws.onerror = () => {
      console.error('[CameraMode] Erro do WebSocket');
      setWsState('disconnected');
      setError('Falha na ligação ao servidor. Verifique se o backend está a correr.');
    };

    ws.onclose = () => {
      console.log('[CameraMode] WebSocket fechado');
      setWsState('disconnected');
    };
  }, [sessionId, onFenDetected]);

  /**
   * Ligar/desligar o WebSocket conforme o componente fica ativo/inativo.
   */
  useEffect(() => {
    if (active) {
      connectWebSocket();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [active, connectWebSocket]);

  /**
   * Copiar o session_id para a área de transferência.
   */
  const copySessionId = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(sessionId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback para browsers mais antigos
      const el = document.createElement('textarea');
      el.value = sessionId;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [sessionId]);

  /**
   * Obter etiqueta do estado do WebSocket.
   */
  const getWsStatusLabel = () => {
    switch (wsState) {
      case 'connected': return 'Ligado';
      case 'connecting': return 'A ligar...';
      default: return 'Desligado';
    }
  };

  // -- Renderização --

  if (!active) return null;

  return (
    <div className="camera-mode">
      {/* Cabeçalho com estado da ligação */}
      <div className="camera-controls">
        <span className={`camera-ws-status camera-ws-status--${wsState}`}>
          {getWsStatusLabel()}
        </span>

        {wsState === 'disconnected' && (
          <button
            className="camera-btn camera-btn--start"
            onClick={connectWebSocket}
          >
            🔄 Reconectar
          </button>
        )}
      </div>

      {/* Mensagem de erro */}
      {error && (
        <div className="camera-status-text camera-status-text--error">
          ⚠ {error}
        </div>
      )}

      {/* Painel principal — código de sessão */}
      <div className="camera-idle-message">
        <span className="camera-idle-icon">📱</span>
        <div className="camera-idle-text">
          <p style={{ margin: '0 0 8px 0' }}>
            Abra a app do telemóvel e introduza o código de sessão:
          </p>

          {/* Código da sessão */}
          <div
            className="session-code"
            onClick={copySessionId}
            title="Clique para copiar"
            style={{
              display: 'inline-block',
              fontSize: '1.8rem',
              fontWeight: 'bold',
              fontFamily: 'monospace',
              letterSpacing: '0.3em',
              padding: '12px 24px',
              background: 'var(--secondary)',
              color: 'var(--fg)',
              borderRadius: 'var(--radius-lg)',
              cursor: 'pointer',
              userSelect: 'all',
              border: '2px dashed var(--border)',
              transition: 'all 0.2s ease',
            }}
          >
            {sessionId}
          </div>

          <p style={{ margin: '8px 0 0 0', fontSize: '0.85rem', opacity: 0.7 }}>
            {copied ? '✅ Copiado!' : '📋 Clique para copiar'}
          </p>

          {/* Estado da deteção */}
          {lastFen ? (
            <div className="camera-status-text camera-status-text--found" style={{ marginTop: '12px' }}>
              <span className="status-dot status-dot--found" />
              Tabuleiro recebido
            </div>
          ) : wsState === 'connected' ? (
            <div className="camera-status-text camera-status-text--searching" style={{ marginTop: '12px' }}>
              <span className="status-dot status-dot--searching" />
              À espera de dados da app…
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default CameraMode;
