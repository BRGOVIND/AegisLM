import React from 'react';
import { NavLink } from 'react-router-dom';
import { Shield, Cpu, Zap, Play, Brain, FileText, BarChart2, TrendingUp, Shuffle, Bot, Trophy, Clock, Database } from 'lucide-react';
import ThreatPulse from './ThreatPulse';

interface NavItem {
  to: string;
  icon: React.ReactNode;
  label: string;
}

const navItems: NavItem[] = [
  { to: '/', icon: <Shield size={18} />, label: 'Dashboard' },
  { to: '/models', icon: <Cpu size={18} />, label: 'Models' },
  { to: '/attacks', icon: <Zap size={18} />, label: 'Attacks' },
  { to: '/run', icon: <Play size={18} />, label: 'Run Tests' },
  { to: '/hallucination', icon: <Brain size={18} />, label: 'Hallucination' },
  { to: '/compare', icon: <BarChart2 size={18} />, label: 'Compare Models' },
  { to: '/analytics', icon: <TrendingUp size={18} />, label: 'Analytics' },
  { to: '/mutations', icon: <Shuffle size={18} />, label: 'Mutations' },
  { to: '/agent', icon: <Bot size={18} />, label: 'Red Team Agent' },
  { to: '/leaderboard', icon: <Trophy size={18} />, label: 'Leaderboard' },
  { to: '/history', icon: <Clock size={18} />, label: 'History' },
  { to: '/dataset', icon: <Database size={18} />, label: 'Dataset' },
  { to: '/reports', icon: <FileText size={18} />, label: 'Reports' },
];

const Navbar: React.FC = () => {
  return (
    <nav
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        padding: '0',
      }}
    >
      {/* Logo */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '24px 20px 16px 20px',
          borderBottom: '1px solid #374151',
        }}
      >
        <span
          style={{
            fontFamily: "'JetBrains Mono', 'Courier New', monospace",
            fontWeight: 700,
            fontSize: '20px',
            color: '#EF4444',
            letterSpacing: '-0.5px',
            lineHeight: 1,
          }}
        >
          RF
        </span>
        <div>
          <span
            style={{
              fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
              fontWeight: 600,
              fontSize: '16px',
              color: '#FFFFFF',
              letterSpacing: '0.01em',
              display: 'block',
            }}
          >
            RedForge
          </span>
          <span style={{ fontSize: '10px', color: '#6B7280', fontFamily: 'monospace' }}>v2.0.0</span>
        </div>
      </div>

      {/* ThreatPulse */}
      <div style={{ padding: '12px 12px 6px 12px' }}>
        <ThreatPulse />
      </div>

      {/* Nav Links */}
      <ul
        style={{
          listStyle: 'none',
          margin: '4px 0 0 0',
          padding: '0 8px',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          gap: '1px',
          overflowY: 'auto',
        }}
      >
        {navItems.map(({ to, icon, label }) => (
          <li key={to}>
            <NavLink
              to={to}
              end={to === '/'}
              style={({ isActive }: { isActive: boolean }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '8px 12px',
                borderRadius: '6px',
                textDecoration: 'none',
                fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
                fontSize: '13px',
                fontWeight: isActive ? 500 : 400,
                color: isActive ? '#EF4444' : '#9CA3AF',
                background: isActive ? 'rgba(239, 68, 68, 0.10)' : 'transparent',
                borderLeft: isActive ? '2px solid #EF4444' : '2px solid transparent',
                transition: 'color 0.15s ease, background 0.15s ease',
                cursor: 'pointer',
              })}
              onMouseEnter={(e: React.MouseEvent<HTMLAnchorElement>) => {
                const el = e.currentTarget;
                if (!el.classList.contains('active')) {
                  el.style.color = '#FFFFFF';
                }
              }}
              onMouseLeave={(e: React.MouseEvent<HTMLAnchorElement>) => {
                const el = e.currentTarget;
                if (!el.classList.contains('active')) {
                  el.style.color = '#9CA3AF';
                }
              }}
            >
              {icon}
              {label}
            </NavLink>
          </li>
        ))}
      </ul>

      {/* Footer */}
      <div style={{ padding: '12px 20px', borderTop: '1px solid #374151' }}>
        <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '11px', color: '#4B5563' }}>
          AI Security Evaluation Platform
        </span>
      </div>
    </nav>
  );
};

export default Navbar;
