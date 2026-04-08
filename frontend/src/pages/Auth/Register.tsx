import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './Auth.css';

interface RegisterResponse {
  success?: boolean;
  message?: string;
  requiresLogin?: boolean;
  user?: any;
}

const Register: React.FC = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!username.trim() || !email.trim() || !password || !confirmPassword) {
      setError('Todos os campos são obrigatórios.');
      return;
    }
    if (password !== confirmPassword) {
      setError('As palavras-passe não coincidem.');
      return;
    }
    if (password.length < 8) {
      setError('A palavra-passe deve ter pelo menos 8 caracteres.');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('Por favor, insira um endereço de email válido.');
      return;
    }

    try {
      setIsLoading(true);
      const result = await register(username, email, password) as RegisterResponse | void;

      if (result && 'requiresLogin' in result && result.requiresLogin) {
        setError(result.message || 'Registo concluído! Por favor, faça login.');
        setTimeout(() => navigate('/login'), 2000);
      } else {
        navigate('/');
      }
    } catch (err: any) {
      if (err.message) {
        setError(err.message);
      } else if (err.details) {
        const details = Object.entries(err.details)
          .map(([field, messages]) =>
            Array.isArray(messages) ? `${field}: ${messages.join(', ')}` : `${field}: ${messages}`
          )
          .join('\n');
        setError(details);
      } else {
        setError('Ocorreu um erro. Por favor, tente novamente.');
      }
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

        <h2>Criar conta</h2>
        <p className="auth-subtitle">Junte-se a milhares de jogadores</p>

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
              required
              autoComplete="username"
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              placeholder="o.seu@email.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              disabled={isLoading}
              required
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Palavra-passe</label>
            <input
              id="password"
              type="password"
              placeholder="Mínimo 8 caracteres"
              value={password}
              onChange={e => setPassword(e.target.value)}
              disabled={isLoading}
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">Confirmar palavra-passe</label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              disabled={isLoading}
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>

          <button type="submit" className="auth-button" disabled={isLoading}>
            <span>{isLoading ? 'A criar conta…' : 'Criar Conta'}</span>
          </button>
        </form>

        <div className="auth-footer">
          Já tem conta?{' '}
          <Link to="/login" className="auth-link">Iniciar sessão</Link>
        </div>
      </div>
    </div>
  );
};

export default Register;