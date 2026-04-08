import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { auth } from '../services/api';

interface User {
  id: number;
  username: string;
  email?: string;
  isGuest: boolean;
  elo_rating?: number;
  games_played?: number;
  games_won?: number;
  games_lost?: number;
  games_drawn?: number;
  avatar?: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  guestLogin: () => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  updateProfile: (data: { username?: string; email?: string } | FormData) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadUser = async () => {
      try {
        const token = localStorage.getItem('token');
        const username = localStorage.getItem('username');
        const isGuest = localStorage.getItem('isGuest');

        if (token && username) {
          const userData = await auth.getCurrentUser();
          setUser({
            id: userData.id,
            username: userData.username,
            email: userData.email,
            isGuest: isGuest === 'true',
            elo_rating: userData.elo_rating,
            games_played: userData.games_played,
            games_won: userData.games_won,
            games_lost: userData.games_lost,
            games_drawn: userData.games_drawn,
            avatar: userData.avatar,
          });
        }
      } catch (error) {
        console.error('Failed to load user:', error);
        // Clear invalid auth data
        auth.logout();
      } finally {
        setLoading(false);
      }
    };

    loadUser();
  }, []);

  const login = async (username: string, password: string) => {
    await auth.login(username, password);
    const userData = await auth.getCurrentUser();
    setUser({
      id: userData.id,
      username: userData.username,
      email: userData.email,
      isGuest: false,
      elo_rating: userData.elo_rating,
      games_played: userData.games_played,
      games_won: userData.games_won,
      games_lost: userData.games_lost,
      games_drawn: userData.games_drawn,
      avatar: userData.avatar,
    });
  };

  const guestLogin = async () => {
    await auth.guestLogin();
    setUser({
      id: 0, // Guest users have id 0
      username: localStorage.getItem('username') || 'Guest',
      isGuest: true,
    });
  };

  const register = async (username: string, email: string, password: string) => {
    await auth.register(username, email, password);
    await login(username, password);
  };

  const logout = async () => {
    if (user?.isGuest) {
      await auth.deleteGuest();
    }
    auth.logout();
    setUser(null);
  };

  const updateProfile = async (data: { username?: string; email?: string } | FormData) => {
    const updatedData = await auth.updateProfile(data);
    if (user) {
      setUser({
        ...user,
        ...updatedData
      });
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, guestLogin, register, logout, updateProfile }}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};