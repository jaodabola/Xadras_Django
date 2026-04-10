import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { MatchmakingProvider } from './contexts/MatchmakingContext';
import { TournamentProvider } from './contexts/TournamentContext';
import ProtectedRoute from './components/ProtectedRoute/ProtectedRoute';
import Navbar from './components/Navbar/Navbar';
import Home from './pages/Home/Home';
import Game from './components/Game/Game';
import Login from './pages/Auth/Login';
import Register from './pages/Auth/Register';
import Matchmaking from './pages/Matchmaking/Matchmaking';
import TournamentDashboard from './pages/Tournament/TournamentDashboard';
import TournamentCreator from './pages/Tournament/TournamentCreator';
import TournamentDetail from './pages/Tournament/TournamentDetail';
import Profile from './pages/Profile/Profile';
import MyGames from './pages/MyGames/MyGames';
import GameReplay from './pages/MyGames/GameReplay';
import './App.css';

const App: React.FC = () => {
  return (
    <Router>
      <AuthProvider>
        <MatchmakingProvider>
          <TournamentProvider>
            <div className="app">
              <Navbar />
              <main className="app-content">
                <Routes>
                  {/* Public routes */}
                  <Route path="/" element={<Home />} />
                  <Route path="/login" element={
                    <ProtectedRoute requireGuest>
                      <Login />
                    </ProtectedRoute>
                  } />
                  <Route path="/register" element={
                    <ProtectedRoute requireGuest>
                      <Register />
                    </ProtectedRoute>
                  } />

                  {/* Protected routes */}
                  <Route element={<ProtectedRoute requireAuth />}>
                    <Route path="/game" element={<Game />} />
                    <Route path="/game/:gameId" element={<Game />} />
                    <Route path="/play" element={<Matchmaking />} />
                    <Route path="/profile" element={<Profile />} />
                    <Route path="/my-games" element={<MyGames />} />
                    <Route path="/my-games/:gameId" element={<GameReplay />} />

                    {/* Tournament routes */}
                    <Route path="/tournaments" element={<TournamentDashboard />} />
                    <Route path="/tournaments/create" element={<TournamentCreator />} />
                    <Route path="/tournaments/:id" element={<TournamentDetail />} />
                  </Route>

                  {/* 404 - Redirect to home */}
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </main>
            </div>
          </TournamentProvider>
        </MatchmakingProvider>
      </AuthProvider>
    </Router>
  );
};

export default App;