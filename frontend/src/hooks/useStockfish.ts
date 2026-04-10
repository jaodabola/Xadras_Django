import { useState, useEffect, useRef, useCallback } from 'react';

export interface StockfishEvaluation {
  score: number; 
  mate: number | null;
  bestMove: string | null;
  depth: number;
}

export function useStockfish() {
  const workerRef = useRef<Worker | null>(null);
  const [evaluation, setEvaluation] = useState<StockfishEvaluation | null>(null);
  const [isEngineReady, setIsEngineReady] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const lastAnalyzedFen = useRef<string | null>(null);
  
  const isAnalyzingRef = useRef(false);
  const ignoringOldSearch = useRef(false);

  useEffect(() => {
    // Carregar o worker do stockfish
    const worker = new Worker('/engine/stockfish.js');
    workerRef.current = worker;

    worker.onmessage = (e) => {
      const msg = e.data;
      if (typeof msg !== 'string') return;
      
      // console.log("STOCKFISH:", msg); // Descomentar para debug local

      if (msg === 'uciok') {
        worker.postMessage('setoption name Hash value 64');
        worker.postMessage('isready');
      } else if (msg === 'readyok') {
        if (!isEngineReady) setIsEngineReady(true);
        ignoringOldSearch.current = false; // Barreira ultrapassada: a nova pesquisa começou!
      } else if (msg.startsWith('info') && /\bdepth\s+\d+/.test(msg)) {
        if (ignoringOldSearch.current) return; // Ignorar rasto antigo
        
        let cpMatch = msg.match(/score\s+cp\s+(-?\d+)/);
        let mateMatch = msg.match(/score\s+mate\s+(-?\d+)/);
        let pvMatch = msg.match(/\bpv\s+([a-h][1-8][a-h][1-8][qrbn]?)/);
        
        // Bloquear react render spam de status inúteis (currmove sem PV)
        if (!cpMatch && !mateMatch && !pvMatch) return; 

        let depthMatch = msg.match(/\bdepth\s+(\d+)/);
        
        const fen = lastAnalyzedFen.current || '';
        const isBlackMove = fen.includes(' b ');
        const multiplier = isBlackMove ? -1 : 1;

        setEvaluation(prev => {
          let score = cpMatch ? (parseInt(cpMatch[1], 10) / 100.0) * multiplier : 0;
          let mate = mateMatch ? parseInt(mateMatch[1], 10) * multiplier : null;
          
          if (!cpMatch && !mateMatch) {
            score = prev?.score || 0;
            mate = prev?.mate || null;
          }

          let depth = depthMatch ? parseInt(depthMatch[1], 10) : (prev?.depth || 0);
          let bestMove = pvMatch ? pvMatch[1] : (prev?.bestMove || null);

          return { score, mate, bestMove, depth };
        });
      } else if (msg.startsWith('bestmove')) {
        if (ignoringOldSearch.current) return; // Descartar bestmove se a barreira isready ainda não desbloqueou

        isAnalyzingRef.current = false;
        setIsAnalyzing(false);

        const match = msg.match(/^bestmove\s+([\w\d]+)/);
        if (match) {
          setEvaluation(prev => ({ 
            score: prev?.score || 0, 
            mate: prev?.mate || null, 
            bestMove: match[1],
            depth: prev?.depth || 0
          }));
        }
      }
    };

    worker.postMessage('uci');

    return () => {
      worker.terminate();
    };
  }, []);

  const analyzeFen = useCallback((fen: string) => {
    const worker = workerRef.current;
    if (!worker || !isEngineReady) return;

    if (fen === lastAnalyzedFen.current) return;
    lastAnalyzedFen.current = fen;

    if (isAnalyzingRef.current) {
      ignoringOldSearch.current = true; // Activa o escudo impenetrável
    }

    isAnalyzingRef.current = true;
    setIsAnalyzing(true);
    setEvaluation(null);
    
    worker.postMessage('stop');
    worker.postMessage('isready'); // A BARREIRA: Obriga o motor a emitir readyok e apaga sincronizações duvidosas
    
    // Reparar FENs parciais vindos da câmara que poderiam crashar o stockfish
    let safeFen = fen.trim();
    if (safeFen.split(' ').length < 2) {
      safeFen += ' w - - 0 1';
    }

    worker.postMessage(`position fen ${safeFen}`);
    worker.postMessage('go depth 15');
  }, [isEngineReady]);
  
  const stopAnalysis = useCallback(() => {
    const worker = workerRef.current;
    if (worker) {
      if (isAnalyzingRef.current) {
        ignoringOldSearch.current = true;
      }
      worker.postMessage('stop');
      isAnalyzingRef.current = false;
      setIsAnalyzing(false);
      lastAnalyzedFen.current = null;
    }
  }, []);

  return { evaluation, isEngineReady, isAnalyzing, analyzeFen, stopAnalysis };
}
