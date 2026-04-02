import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './Navbar.css';

const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/');
      setMobileMenuOpen(false);
    } catch (error) {
      console.error('Erro ao terminar sessão', error);
    }
  };

  const closeMobile = () => setMobileMenuOpen(false);

  // Ocultar navbar nas páginas de autenticação
  if (['/login', '/register'].includes(location.pathname)) {
    return null;
  }

  return (
    <nav className="navbar">
      <div className="navbar-container">

        {/* Lado esquerdo: Logo + links de navegação */}
        <div className="navbar-left">
          <Link to="/" className="navbar-logo" onClick={closeMobile}>
            <img src="/public/logo/logo.png" alt="Logo" className="logo-icon" />
            <span className="logo-text">Xadras</span>
          </Link>

          {/* Links junto à logo (só mostra no mobile se menu aberto) */}
          {user && (
            <div className={`nav-links ${mobileMenuOpen ? 'mobile-open' : ''}`}>
              <Link
                to="/play"
                className={`nav-link ${location.pathname === '/play' ? 'active' : ''}`}
                onClick={closeMobile}
              >
                Jogar
              </Link>
              <Link
                to="/tournaments"
                className={`nav-link ${location.pathname.startsWith('/tournaments') ? 'active' : ''}`}
                onClick={closeMobile}
              >
                Torneios
              </Link>
              <Link
                to="/game"
                className={`nav-link ${location.pathname.startsWith('/game') ? 'active' : ''}`}
                onClick={closeMobile}
              >
                Jogo Local
              </Link>
            </div>
          )}
        </div>

        {/* Hamburger para mobile */}
        <button
          className={`mobile-menu-toggle ${mobileMenuOpen ? 'open' : ''}`}
          onClick={() => setMobileMenuOpen(v => !v)}
          aria-label="Abrir menu"
          aria-expanded={mobileMenuOpen}
        >
          <span />
          <span />
          <span />
        </button>

        {/* Lado direito: utilizador / auth */}
        <div className={`navbar-content ${mobileMenuOpen ? 'mobile-open' : ''}`}>
          <div className="user-section">
            {user ? (
              <div className="user-menu">
                {user.isGuest ? (
                  <div className="username-link" style={{ cursor: 'default' }}>
                    <div className="nav-avatar">
                      <span>{user.username.charAt(0).toUpperCase()}</span>
                    </div>
                    <span className="username-text">{user.username}</span>
                  </div>
                ) : (
                  <Link to="/profile" className="username-link" title="Ver Perfil" onClick={closeMobile}>
                    <div className="nav-avatar">
                      {user.avatar ? (
                        <img src={user.avatar} alt="Avatar" />
                      ) : (
                        <span>{user.username.charAt(0).toUpperCase()}</span>
                      )}
                    </div>
                    <span className="username-text">{user.username}</span>
                  </Link>
                )}
                <button onClick={handleLogout} className="logout-button">
                  Sair
                </button>
              </div>
            ) : (
              <div className="auth-buttons">
                <Link to="/login" className="login-button" onClick={closeMobile}>
                  Entrar
                </Link>
                <Link to="/register" className="register-button" onClick={closeMobile}>
                  Registar
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;