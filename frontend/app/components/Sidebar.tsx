import React from 'react';
import { UiLanguage, getUiCopy } from '../lib/i18n';

export type WorkspaceView = 'home' | 'dashboard';

export default function Sidebar({
  language,
  activeView,
  onViewChange,
}: {
  language: UiLanguage;
  activeView: WorkspaceView;
  onViewChange: (view: WorkspaceView) => void;
}) {
  const copy = getUiCopy(language);
  return (
    <aside className="sidebar" aria-label={copy.nav.aria}>
      <a className="brand" href="#command" aria-label={`ElaraX: ${copy.nav.home}`}>
        <span className="brand-mark"><i /></span>
        <span className="brand-copy">Elara<span>X</span></span>
      </a>
      <div className="sidebar-intro">
        <span className="sidebar-kicker">{copy.nav.intro}</span>
        <p>{copy.nav.introBody}</p>
      </div>
      <nav className="nav-stack">
        <p className="nav-label">{copy.nav.workspace}</p>
        <a className={`nav-item${activeView === 'dashboard' ? ' active' : ''}`} href="#dashboard" onClick={(event) => { event.preventDefault(); onViewChange('dashboard'); }}><span className="nav-glyph">▦</span>{copy.nav.dashboard}</a>
        <a className={`nav-item${activeView === 'home' ? ' active' : ''}`} href="#command" onClick={() => onViewChange('home')}><span className="nav-glyph">+</span>{copy.nav.command}</a>
        <a className="nav-item" href="#briefing" onClick={() => onViewChange('home')}><span className="nav-glyph">○</span>{copy.nav.today}</a>
        <a className="nav-item" href="#connections" onClick={() => onViewChange('home')}><span className="nav-glyph">~</span>{copy.nav.connections}</a>
        <a className="nav-item" href="#robot" onClick={() => onViewChange('home')}><span className="nav-glyph">□</span>{copy.nav.robot}</a>
      </nav>
      <div className="sidebar-footer">
        <div className="avatar">AH</div>
        <div>
          <strong>Hazra</strong>
          <span>{copy.nav.localWorkspace}</span>
        </div>
        <button type="button" aria-label={copy.nav.settings}>...</button>
      </div>
    </aside>
  );
}
