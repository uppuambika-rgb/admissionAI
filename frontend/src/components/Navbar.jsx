import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const navLinks = [
    { label: 'Home', href: '/' },
    { label: 'About', href: '/#about' },
    { label: 'Colleges', href: '/topic/college-info' },
    { label: 'AI Counsellor', href: '/topic/ai-counsellor' },
    { label: 'Help', href: '/#features' },
  ];

  const isHome = location.pathname === '/';

  return (
    <nav className="site-navbar" role="navigation" aria-label="Main navigation">
      <div className="navbar-inner">
        {/* Brand */}
        <Link to="/" className="nav-brand" aria-label="AdmissionAI Home">
          <div className="nav-brand-icon" aria-hidden="true">🎓</div>
          <span className="nav-brand-name">AdmissionAI</span>
        </Link>

        {/* Desktop links */}
        <ul className="nav-links" role="list">
          {navLinks.map((link) => (
            <li key={link.label}>
              <Link
                to={link.href}
                className={`nav-link ${location.pathname === link.href ? 'nav-link-active' : ''}`}
              >
                {link.label}
              </Link>
            </li>
          ))}
        </ul>

        {/* Right side */}
        <div className="nav-right">
          <span className="nav-online-badge" aria-label="System status: online">
            <span className="nav-online-dot" aria-hidden="true"></span>
            System Online
          </span>
          <button
            className="nav-profile-btn"
            aria-label="User profile"
            onClick={() => navigate('/topic/ai-counsellor')}
          >
            <span aria-hidden="true">👤</span>
          </button>
          {/* Mobile hamburger */}
          <button
            className="nav-hamburger"
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((o) => !o)}
          >
            <span className={`hamburger-bar ${menuOpen ? 'open' : ''}`}></span>
            <span className={`hamburger-bar ${menuOpen ? 'open' : ''}`}></span>
            <span className={`hamburger-bar ${menuOpen ? 'open' : ''}`}></span>
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {menuOpen && (
        <div className="nav-mobile-drawer" role="menu">
          {navLinks.map((link) => (
            <Link
              key={link.label}
              to={link.href}
              className="nav-mobile-link"
              role="menuitem"
              onClick={() => setMenuOpen(false)}
            >
              {link.label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  );
}
