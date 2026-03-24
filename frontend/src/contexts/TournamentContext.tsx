import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import api from '../services/api';
import { useAuth } from './AuthContext';

interface Tournament {
  id: number;
  name: string;
  description: string;
  max_participants: number;
  current_participants: number;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED';
  created_by: {
    id: number;
    username: string;
  };
  participants: any[];
  created_at: string;
  start_date?: string;
  end_date?: string;
}

interface TournamentContextType {
  tournaments: Tournament[];
  loading: boolean;
  error: string | null;
  selectedTournament: Tournament | null;
  
  // Tournament management
  fetchTournaments: () => Promise<void>;
  createTournament: (tournamentData: any) => Promise<Tournament>;
  joinTournament: (tournamentId: number) => Promise<void>;
  leaveTournament: (tournamentId: number) => Promise<void>;
  getTournament: (tournamentId: number) => Promise<Tournament>;
  
  // Tournament operations
  generatePairings: (tournamentId: number) => Promise<void>;
  assignBoards: (tournamentId: number, assignments: any) => Promise<void>;
  startRound: (tournamentId: number) => Promise<void>;
  getStandings: (tournamentId: number) => Promise<any>;
  
  // State management
  setSelectedTournament: (tournament: Tournament | null) => void;
  clearError: () => void;
}

const TournamentContext = createContext<TournamentContextType | null>(null);

export const TournamentProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [tournaments, setTournaments] = useState<Tournament[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTournament, setSelectedTournament] = useState<Tournament | null>(null);
  const { user } = useAuth();

  // Fetch all tournaments
  const fetchTournaments = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get('/tournaments/');
      setTournaments(response.data);
    } catch (err: any) {
      console.error('Error fetching tournaments:', err);
      setError('Failed to fetch tournaments');
    } finally {
      setLoading(false);
    }
  };

  // Create new tournament
  const createTournament = async (tournamentData: any): Promise<Tournament> => {
    try {
      setError(null);
      const response = await api.post('/tournaments/', tournamentData);
      const newTournament = response.data;
      setTournaments(prev => [newTournament, ...prev]);
      return newTournament;
    } catch (err: any) {
      console.error('Error creating tournament:', err);
      const errorMessage = err.response?.data?.detail || 'Failed to create tournament';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  };

  // Join tournament
  const joinTournament = async (tournamentId: number) => {
    try {
      setError(null);
      await api.post(`/tournaments/${tournamentId}/join/`);
      // Refresh tournaments to update participant count
      await fetchTournaments();
    } catch (err: any) {
      console.error('Error joining tournament:', err);
      const errorMessage = err.response?.data?.detail || 'Failed to join tournament';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  };

  // Leave tournament
  const leaveTournament = async (tournamentId: number) => {
    try {
      setError(null);
      await api.post(`/tournaments/${tournamentId}/leave/`);
      // Refresh tournaments to update participant count
      await fetchTournaments();
    } catch (err: any) {
      console.error('Error leaving tournament:', err);
      const errorMessage = err.response?.data?.detail || 'Failed to leave tournament';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  };

  // Get specific tournament details
  const getTournament = async (tournamentId: number): Promise<Tournament> => {
    try {
      setError(null);
      const response = await api.get(`/tournaments/${tournamentId}/`);
      const tournament = response.data;
      setSelectedTournament(tournament);
      return tournament;
    } catch (err: any) {
      console.error('Error fetching tournament:', err);
      const errorMessage = err.response?.data?.detail || 'Failed to fetch tournament details';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  };

  // Generate tournament pairings (Swiss algorithm)
  const generatePairings = async (tournamentId: number) => {
    try {
      setError(null);
      await api.post(`/tournaments/${tournamentId}/generate_pairings/`);
      // Refresh tournament data to show new pairings
      await getTournament(tournamentId);
    } catch (err: any) {
      console.error('Error generating pairings:', err);
      const errorMessage = err.response?.data?.detail || 'Failed to generate pairings';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  };

  // Assign boards for Vision AI integration
  const assignBoards = async (tournamentId: number, assignments: any) => {
    try {
      setError(null);
      await api.post(`/tournaments/${tournamentId}/assign_boards/`, assignments);
      // Refresh tournament data to show board assignments
      await getTournament(tournamentId);
    } catch (err: any) {
      console.error('Error assigning boards:', err);
      const errorMessage = err.response?.data?.detail || 'Failed to assign boards';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  };

  // Start tournament round
  const startRound = async (tournamentId: number) => {
    try {
      setError(null);
      await api.post(`/tournaments/${tournamentId}/start_round/`);
      // Refresh tournament data to show round start
      await getTournament(tournamentId);
    } catch (err: any) {
      console.error('Error starting round:', err);
      const errorMessage = err.response?.data?.detail || 'Failed to start round';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  };

  // Get tournament standings
  const getStandings = async (tournamentId: number) => {
    try {
      setError(null);
      const response = await api.get(`/tournaments/${tournamentId}/standings/`);
      return response.data;
    } catch (err: any) {
      console.error('Error fetching standings:', err);
      const errorMessage = err.response?.data?.detail || 'Failed to fetch standings';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  };

  // Clear error state
  const clearError = () => {
    setError(null);
  };

  // Load tournaments on mount and when user changes
  useEffect(() => {
    if (user) {
      fetchTournaments();
    } else {
      // Clear tournaments when user logs out
      setTournaments([]);
      setSelectedTournament(null);
      setError(null);
    }
  }, [user]);

  return (
    <TournamentContext.Provider
      value={{
        tournaments,
        loading,
        error,
        selectedTournament,
        fetchTournaments,
        createTournament,
        joinTournament,
        leaveTournament,
        getTournament,
        generatePairings,
        assignBoards,
        startRound,
        getStandings,
        setSelectedTournament,
        clearError,
      }}
    >
      {children}
    </TournamentContext.Provider>
  );
};

export const useTournament = () => {
  const context = useContext(TournamentContext);
  if (!context) {
    throw new Error('useTournament must be used within a TournamentProvider');
  }
  return context;
};
