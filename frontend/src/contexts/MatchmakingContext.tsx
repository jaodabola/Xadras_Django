import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import api, { matchmaking } from '../services/api';
import { useAuth } from './AuthContext';

interface MatchmakingContextType {
  isInQueue: boolean;
  joinQueue: (preferredColor: 'WHITE' | 'BLACK' | 'ANY') => Promise<void>;
  leaveQueue: () => Promise<void>;
  leaveGame: () => void;
  matchFound: boolean;
  matchData: any | null;
  currentMatch: any | null;
  error: string | null;
  checkMatchStatus: () => Promise<void>;
}

const MatchmakingContext = createContext<MatchmakingContextType | null>(null);

export const MatchmakingProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isInQueue, setIsInQueue] = useState(false);
  const [matchFound, setMatchFound] = useState(false);
  const [matchData, setMatchData] = useState<any | null>(null);
  const [currentMatch, setCurrentMatch] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checkInterval, setCheckInterval] = useState<NodeJS.Timeout | null>(null);
  const { user } = useAuth();

  const checkMatchStatus = async () => {
    if (!isInQueue) return;
    
    try {
      const status = await matchmaking.checkMatchStatus();
      
      // Backend variant A: explicit match_found + match_data
      if (status.match_found && status.match_data) {
        setMatchFound(true);
        setMatchData(status.match_data);
        setIsInQueue(false);
        if (checkInterval) {
          clearInterval(checkInterval);
          setCheckInterval(null);
        }
        return;
      }

      // Backend variant B: { status: 'match_found', game_id, color, opponent, opponent_color }
      if (status.status === 'match_found' && status.game_id) {
        setMatchFound(true);
        setMatchData({
          game_id: status.game_id,
          color: status.color,
          opponent: status.opponent,
          opponent_color: status.opponent_color,
        });
        setIsInQueue(false);
        if (checkInterval) {
          clearInterval(checkInterval);
          setCheckInterval(null);
        }
        return;
      }

      // Fallback: user removed from queue but game created separately
      if ((status.in_queue === false || status.status === 'not_in_queue') && user) {
        try {
          const gamesResponse = await api.get('/game/');
          const games = Array.isArray(gamesResponse.data) ? gamesResponse.data : [];

          // Find most recent IN_PROGRESS game for this user
          const activeGames = games
            .filter((game: any) => game.status === 'IN_PROGRESS')
            .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

          if (activeGames.length > 0) {
            const game = activeGames[0];
            const isWhite = game.white_player?.id === user.id;
            const color = isWhite ? 'WHITE' : 'BLACK';
            const opponentUser = isWhite ? game.black_player : game.white_player;

            setMatchFound(true);
            setMatchData({
              game_id: game.id,
              color,
              opponent: opponentUser?.username,
              opponent_color: isWhite ? 'BLACK' : 'WHITE',
            });
            setIsInQueue(false);
            if (checkInterval) {
              clearInterval(checkInterval);
              setCheckInterval(null);
            }
          }
        } catch (gameErr) {
          console.error('Error checking active games after leaving queue:', gameErr);
        }
      }
    } catch (err) {
      console.error('Error checking match status:', err);
      setError('Failed to check match status');
    }
  };

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    
    if (isInQueue) {
      // Check for match every 3 seconds
      interval = setInterval(checkMatchStatus, 3000);
      setCheckInterval(interval);
    } else {
      // Clear interval when not in queue
      if (checkInterval) {
        clearInterval(checkInterval);
        setCheckInterval(null);
      }
    }
    
    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [isInQueue]); // Only depend on isInQueue to prevent infinite loops

  const joinQueue = async (preferredColor: 'WHITE' | 'BLACK' | 'ANY' = 'ANY') => {
    try {
      setError(null);
      const response = await matchmaking.joinQueue(preferredColor);

      // Backend variant A: immediate match_found response from join
      if (response && (response.match_found || response.status === 'match_found') && response.game_id) {
        setMatchFound(true);
        setMatchData({
          game_id: response.game_id,
          color: response.color,
          opponent: response.opponent,
          opponent_color: response.opponent_color,
        });
        setIsInQueue(false);
        if (checkInterval) {
          clearInterval(checkInterval);
          setCheckInterval(null);
        }
      } else {
        // Default behaviour: user enters queue and polling will detect match
        setIsInQueue(true);
      }
    } catch (err) {
      console.error('Failed to join queue:', err);
      setError('Failed to join matchmaking queue');
      throw err;
    }
  };

  const leaveQueue = async () => {
    try {
      await matchmaking.leaveQueue();
      setIsInQueue(false);
      setMatchFound(false);
      setMatchData(null);
      if (checkInterval) {
        clearInterval(checkInterval);
        setCheckInterval(null);
      }
    } catch (err) {
      console.error('Failed to leave queue:', err);
      setError('Failed to leave matchmaking queue');
      throw err;
    }
  };

  const leaveGame = () => {
    setCurrentMatch(null);
    setMatchFound(false);
    setMatchData(null);
    // Any other cleanup needed when leaving a game
  };

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (checkInterval) {
        clearInterval(checkInterval);
      }
    };
  }, []); // Empty deps - only cleanup on unmount

  // Reset matchmaking state when user logs out
  useEffect(() => {
    if (!user) {
      setIsInQueue(false);
      setMatchFound(false);
      setMatchData(null);
      setError(null);
      // Clear interval when user logs out
      if (checkInterval) {
        clearInterval(checkInterval);
        setCheckInterval(null);
      }
    }
  }, [user, checkInterval]); // Include checkInterval in dependencies

  return (
    <MatchmakingContext.Provider
      value={{
        isInQueue,
        joinQueue,
        leaveQueue,
        leaveGame,
        matchFound,
        matchData,
        currentMatch,
        error,
        checkMatchStatus,
      }}
    >
      {children}
    </MatchmakingContext.Provider>
  );
};

export const useMatchmaking = () => {
  const context = useContext(MatchmakingContext);
  if (!context) {
    throw new Error('useMatchmaking must be used within a MatchmakingProvider');
  }
  return context;
};
