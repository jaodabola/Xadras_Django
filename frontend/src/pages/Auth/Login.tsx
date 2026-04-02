import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './Auth.css';

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login, guestLogin } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) {
      setError('Por favor, introduza o utilizador e a palavra-passe.');
      return;
    }
    try {
      setIsLoading(true);
      setError('');
      await login(username, password);
      navigate('/');
    } catch {
      setError('Credenciais inválidas. Por favor, tente novamente.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGuestLogin = async () => {
    try {
      setIsLoading(true);
      setError('');
      await guestLogin();
      navigate('/');
    } catch {
      setError('Falha ao entrar como convidado. Por favor, tente novamente.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">

        {/* Logo */}
        <div className="auth-logo">
          <span className="auth-logo-icon">♞</span>
          <span className="auth-logo-name">Xadras</span>
        </div>

        <h2>Bem-vindo de volta</h2>
        <p className="auth-subtitle">Inicie sessão para continuar a jogar</p>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="username">Nome de utilizador</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              disabled={isLoading}
              autoComplete="username"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Palavra-passe</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              disabled={isLoading}
              autoComplete="current-password"
            />
          </div>

          <button type="submit" className="auth-button" disabled={isLoading}>
            <span>{isLoading ? 'A iniciar sessão…' : 'Entrar'}</span>
          </button>

          <div className="auth-divider">ou</div>

          <button
            type="button"
            className="guest-button"
            onClick={handleGuestLogin}
            disabled={isLoading}
          >
            {isLoading ? 'A entrar…' : 'Jogar como Convidado'}
          </button>
        </form>

        <div className="auth-footer">
          Não tem conta?{' '}
          <Link to="/register" className="auth-link">Registar-se</Link>
        </div>
      </div>
    </div>
  );
};

export default Login;
