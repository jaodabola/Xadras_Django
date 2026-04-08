import { useEffect, useRef, useState } from 'react';
import './GameClock.css';

const TIME_CONTROL_SECONDS: Record<string, number> = {
    bullet: 60,
    blitz: 300,
    rapid: 600,
    classical: 1800,
};

function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
}

function getLowSecs(timeControl: string): number {
    switch (timeControl) {
        case 'bullet': return 10;
        case 'blitz': return 30;
        case 'rapid': return 60;
        case 'classical': return 120;
        default: return 0;
    }
}

/* ─── Painel individual (usado acima/abaixo do tabuleiro) ─── */
interface ClockPanelProps {
    label: string;
    time: number;        // segundos restantes
    isActive: boolean;
    isLow: boolean;
    isUnlimited: boolean;
    timeControl: string;
}

export const ClockPanel: React.FC<ClockPanelProps> = ({
    label, time, isActive, isLow, isUnlimited, timeControl,
}) => (
    <div className={[
        'clock-panel',
        isActive ? 'clock-panel--active' : '',
        isLow ? 'clock-panel--low' : '',
    ].filter(Boolean).join(' ')}>
        <span className="clock-panel__label">{label}</span>
        {isUnlimited
            ? <span className="clock-panel__time clock-panel__unlimited">∞</span>
            : <span className="clock-panel__time">{formatTime(time)}</span>
        }
        {isActive && !isUnlimited && <span className="clock-panel__pulse" />}
        {isActive && !isUnlimited && (
            <span className="clock-panel__badge">{timeControl}</span>
        )}
    </div>
);

/* ─── Hook central que gere o estado dos dois relógios ─── */
interface UseGameClockOptions {
    timeControl: string;
    activeColor: 'w' | 'b';
    isGameOver: boolean;
    onTimeout: (color: 'w' | 'b') => void;
    moveCount: number;  // relógio só arranca após a 1ª jogada
}

export function useGameClock({
    timeControl,
    activeColor,
    isGameOver,
    onTimeout,
    moveCount,
}: UseGameClockOptions) {
    const isUnlimited = timeControl === 'unlimited' || !(timeControl in TIME_CONTROL_SECONDS);
    const initial = TIME_CONTROL_SECONDS[timeControl] ?? 600;
    const started = moveCount > 0; // relógio só corre depois da 1ª jogada

    const [whiteTime, setWhiteTime] = useState(initial);
    const [blackTime, setBlackTime] = useState(initial);

    const whiteRef = useRef(initial);
    const blackRef = useRef(initial);
    const activeRef = useRef(activeColor);
    const gameOverRef = useRef(isGameOver);
    const startedRef = useRef(started);

    useEffect(() => { activeRef.current = activeColor; }, [activeColor]);
    useEffect(() => { gameOverRef.current = isGameOver; }, [isGameOver]);
    useEffect(() => { startedRef.current = started; }, [started]);

    // Reiniciar relógios quando o ritmo de jogo muda (ex: gameData carrega)
    useEffect(() => {
        const secs = TIME_CONTROL_SECONDS[timeControl] ?? 600;
        whiteRef.current = secs;
        blackRef.current = secs;
        setWhiteTime(secs);
        setBlackTime(secs);
    }, [timeControl]);

    useEffect(() => {
        if (isUnlimited) return;

        const id = setInterval(() => {
            // Não contar se o jogo acabou ou se ainda não houve jogadas
            if (gameOverRef.current || !startedRef.current) return;

            if (activeRef.current === 'w') {
                whiteRef.current = Math.max(0, whiteRef.current - 1);
                setWhiteTime(whiteRef.current);
                if (whiteRef.current <= 0) { onTimeout('w'); clearInterval(id); }
            } else {
                blackRef.current = Math.max(0, blackRef.current - 1);
                setBlackTime(blackRef.current);
                if (blackRef.current <= 0) { onTimeout('b'); clearInterval(id); }
            }
        }, 1000);

        return () => clearInterval(id);
    }, [timeControl, isUnlimited]); // eslint-disable-line react-hooks/exhaustive-deps

    const lowSecs = getLowSecs(timeControl);

    return {
        isUnlimited,
        white: {
            time: whiteTime,
            isLow: !isUnlimited && whiteTime <= lowSecs,
        },
        black: {
            time: blackTime,
            isLow: !isUnlimited && blackTime <= lowSecs,
        },
    };
}

export default useGameClock;