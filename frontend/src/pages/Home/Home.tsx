import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import './Home.css';

/* ──────────────── Chess board graphic ──────────────── */
const PIECES: { row: number; col: number; piece: string; color: 'light' | 'dark' }[] = [
  { row: 0, col: 4, piece: 'king', color: 'dark' },
  { row: 0, col: 3, piece: 'queen', color: 'dark' },
  { row: 1, col: 2, piece: 'pawn', color: 'dark' },
  { row: 1, col: 5, piece: 'pawn', color: 'dark' },
  { row: 7, col: 4, piece: 'king', color: 'light' },
  { row: 6, col: 3, piece: 'pawn', color: 'light' },
  { row: 5, col: 5, piece: 'knight', color: 'light' },
];

/* ── Mapeamento peça → nome de ficheiro SVG (Lichess cburnett) ── */
const PIECE_SVG: Record<string, { light: string; dark: string }> = {
  king: { light: 'wK', dark: 'bK' },
  queen: { light: 'wQ', dark: 'bQ' },
  rook: { light: 'wR', dark: 'bR' },
  bishop: { light: 'wB', dark: 'bB' },
  knight: { light: 'wN', dark: 'bN' },
  pawn: { light: 'wP', dark: 'bP' },
};

function ChessboardGraphic() {
  return (
    <div className="cb-wrapper">
      <div className="cb-shadow" />
      <div className="cb-board">
        {Array.from({ length: 64 }).map((_, i) => {
          const row = Math.floor(i / 8);
          const col = i % 8;
          const isLight = (row + col) % 2 === 0;
          const piece = PIECES.find(p => p.row === row && p.col === col);
          const svgName = piece ? PIECE_SVG[piece.piece]?.[piece.color] : null;
          return (
            <div key={i} className={`cb-cell ${isLight ? 'cb-light' : 'cb-dark'}`}>
              {svgName && (
                <img
                  src={`/pieces/${svgName}.svg`}
                  alt={svgName}
                  draggable={false}
                  className="cb-piece-img"
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ──────────────── Features ──────────────── */
const FEATURES = [
  {
    icon: '⚡',
    title: 'Encontrar Jogo Rápido',
    description: 'Encontre adversários em segundos com o nosso sistema inteligente de matchmaking baseado em rating.',
    href: '/play',
  },
  {
    icon: '🏆',
    title: 'Torneios',
    description: 'Participe em torneios diários e semanais e demonstre o seu valor contra jogadores de todo o mundo.',
    href: '/play',
  },
  {
    icon: '🖥️',
    title: 'Jogo Local',
    description: 'Jogue xadrez com um amigo no mesmo dispositivo. Sem necessidade de conta.',
    href: '/play',
  },
];

const HIGHLIGHTS = [
  { icon: '⚡', text: 'Jogos instantâneos' },
  { icon: '🛡️', text: 'Jogo justo' },
  { icon: '⏱️', text: 'Todos os ritmos' },
];

/* ──────────────── Main Component ──────────────── */
const Home: React.FC = () => {
  const navigate = useNavigate();
  const { user, loading } = useAuth();

  const handlePlayClick = () => {
    if (user) {
      navigate('/play');
    } else {
      navigate('/login', { state: { from: '/play' } });
    }
  };

  if (loading) {
    return (
      <div className="home-container">
        <div className="home-loading">A carregar…</div>
      </div>
    );
  }

  return (
    <div className="home-container">

      {/* ── HERO ── */}
      <section className="hero-section">
        <div className="hero-inner">

          {/* Left */}
          <div className="hero-left">
            {/* Online badge
            <div className="hero-badge">
              <span className="badge-dot" />
              <span>1.247 jogadores online</span>
            </div>
            */}
            {/* Title */}
            <h1 className="hero-title">
              Jogue Xadrez.
              <span className="hero-title-sub">Domine o Jogo.</span>
            </h1>

            {/* Subtitle */}
            <p className="hero-subtitle">
              Junte-se à nossa comunidade de xadrez. Dispute partidas,
              suba no ranking e demonstre as suas capacidades no Xadras.
            </p>

            {/* CTA buttons */}
            <div className="hero-cta">
              <button className="btn-primary" onClick={handlePlayClick}>
                <span>▶</span>
                {user ? 'Jogar Agora' : 'Jogar Agora'}
              </button>
              <Link to="/play" className="btn-outline">Ver Torneios</Link>
            </div>

            {/* Guest notice */}
            {user && user.isGuest && (
              <div className="guest-notice">
                <p>
                  A utilizar a conta de convidado.{' '}
                  <Link to="/register" className="register-link">Crie uma conta</Link>
                  {' '}para desbloquear todas as funcionalidades.
                </p>
              </div>
            )}


          </div>

          {/* Right – decorative board */}
          <div className="hero-right">
            <ChessboardGraphic />
          </div>

        </div>
      </section>

      {/* ── FEATURES ── */}
      <section className="features-section">
        <div className="features-inner">

          {/* Header */}
          <div className="features-header">
            <h2 className="features-title">Tudo o que necessita para jogar</h2>
            <p className="features-subtitle">Simples, rápido e feito para amantes de xadrez.</p>
          </div>

          {/* Cards */}
          <div className="features-grid">
            {FEATURES.map(f => (
              <Link key={f.title} to={f.href} className="feature-card">
                <div className="feature-icon-box">
                  <span>{f.icon}</span>
                </div>
                <h3 className="feature-card-title">{f.title}</h3>
                <p className="feature-card-desc">{f.description}</p>
                <div className="feature-card-cta">
                  Começar <span className="feature-arrow">→</span>
                </div>
              </Link>
            ))}
          </div>

          {/* Highlights bar */}
          <div className="highlights-bar">
            {HIGHLIGHTS.map((h, i) => (
              <div key={i} className="highlight-item">
                <span>{h.icon}</span>
                <span>{h.text}</span>
              </div>
            ))}
          </div>

        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="home-footer">
        <div className="footer-inner">
          <div className="footer-brand">
            <Link to="/" className="footer-logo">
              <span className="footer-logo-icon">♞</span>
              <span className="footer-logo-name">Xadras</span>
            </Link>
            <p className="footer-tagline">Jogue xadrez, à sua maneira.</p>
          </div>

          <nav className="footer-nav">
            {[
              { to: '/', label: 'Início' },
              { to: '/play', label: 'Encontrar Jogo' },
              { to: '/play', label: 'Torneios' },
              { to: '/play', label: 'Jogo Local' },
            ].map(l => (
              <Link key={l.label} to={l.to} className="footer-link">{l.label}</Link>
            ))}
          </nav>
        </div>

        <div className="footer-copy">
          <p>© {new Date().getFullYear()} Xadras. Todos os direitos reservados.</p>
        </div>
      </footer>

    </div>
  );
};

export default Home;