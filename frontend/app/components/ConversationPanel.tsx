import React from 'react';
import { EmailResult, PendingAction, ResearchReport } from '../lib/aether-api';
import { UiLanguage, displayIntent, displayLanguage, displayRisk, getUiCopy, localeForUiLanguage } from '../lib/i18n';

export type ConversationMessage = {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  intent?: string;
  risk?: string | null;
  language?: string | null;
  emails?: EmailResult[];
  agentMode?: 'deterministic' | 'gemini';
  taskCount?: number;
  showEmailResults?: boolean;
  research?: ResearchReport | null;
};

export type PendingConfirmation = { 
  threadId: string; 
  action: PendingAction; 
};

export type ConversationPanelProps = {
  messages: ConversationMessage[];
  pending?: PendingConfirmation;
  busy: boolean;
  handleConfirmation: (decision: 'approve' | 'reject') => Promise<void>;
  onClear: () => void;
  endRef: React.RefObject<HTMLDivElement | null>;
  language: UiLanguage;
};

function senderInitials(email: EmailResult): string {
  const name = email.sender_name || email.sender || 'Unknown';
  return name.charAt(0).toUpperCase();
}

function emailTimestamp(dateString: string | null | undefined, locale: string): string {
  if (!dateString) return '';
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return '';
  const now = new Date();
  if (date.toDateString() === now.toDateString()) return date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
  return date.toLocaleDateString(locale, { day: 'numeric', month: 'short' });
}

export default function ConversationPanel({
  messages,
  pending,
  busy,
  handleConfirmation,
  onClear,
  endRef,
  language,
}: ConversationPanelProps) {
  const copy = getUiCopy(language);
  const locale = localeForUiLanguage(language);
  if (messages.length === 0 && !busy) {
    return null;
  }

  return (
    <section className="conversation-panel" aria-label={copy.conversation.aria} aria-live="polite">
      <div className="conversation-heading">
        <span>{copy.conversation.heading}</span>
        <button type="button" onClick={onClear}>{copy.conversation.clear}</button>
      </div>
      <div className="message-list">
        {messages.map((message) => (
          <article className={`message ${message.role}`} key={message.id}>
            <div className="message-avatar">{message.role === 'assistant' ? '+' : 'AH'}</div>
            <div className="message-body">
              <span>{message.role === 'assistant' ? 'ElaraX' : copy.conversation.you}</span>
              <p>{message.text}</p>
              
              {message.role === 'assistant' && message.showEmailResults && message.emails && message.emails.length > 0 && (
                <div className="email-results" role="list" aria-label={copy.conversation.emailResults(message.emails.length)}>
                  {message.emails.map((email) => (
                    <article className={`email-result${email.unread ? ' unread' : ''}`} role="listitem" key={email.id}>
                      <div className="email-result-avatar">{senderInitials(email)}</div>
                      <div className="email-result-copy">
                        <div className="email-result-sender">
                          <strong>{email.sender_name || email.sender}</strong>
                          <time>{emailTimestamp(email.date, locale)}</time>
                        </div>
                        <h4>{email.subject}</h4>
                        <p>{email.snippet || copy.conversation.noPreview}</p>
                      </div>
                      {email.urgent && <span className="important-dot" title={copy.conversation.markedImportant} aria-label={copy.conversation.markedImportant} />}
                    </article>
                  ))}
                </div>
              )}

              {message.role === 'assistant' && message.research && (
                <ResearchCard report={message.research} language={language} />
              )}
              
              {message.intent && (
                <div className="message-meta">
                  {message.agentMode && <i>{message.agentMode === 'gemini' ? copy.conversation.geminiSupervisor : copy.conversation.safeFallback}</i>}
                  {message.taskCount && message.taskCount > 1 && <i>{copy.conversation.steps(message.taskCount)}</i>}
                  <i>{displayIntent(message.intent, copy)}</i>
                  {message.language && <i>{displayLanguage(message.language, copy)}</i>}
                  {message.risk && <i className={`risk-${message.risk.toLowerCase()}`}>{displayRisk(message.risk, copy)}</i>}
                </div>
              )}
            </div>
          </article>
        ))}
        
        {pending && (
          <article className="approval-card">
            <div className="approval-icon">!</div>
            <div>
              <span>{copy.conversation.confirmationRequired}</span>
              <strong>{displayIntent(pending.action.action, copy)}</strong>
              <p>{copy.conversation.approvalPrompt}</p>
            </div>
            <div className="approval-actions">
              <button type="button" onClick={() => void handleConfirmation('reject')} disabled={busy}>{copy.conversation.cancel}</button>
              <button type="button" className="approve" onClick={() => void handleConfirmation('approve')} disabled={busy}>{copy.conversation.approve}</button>
            </div>
          </article>
        )}
        
        {busy && (
          <article className="message assistant loading-message">
            <div className="message-avatar">+</div>
            <div className="typing-dots"><i /><i /><i /></div>
          </article>
        )}
        <div ref={endRef} />
      </div>
    </section>
  );
}

function ResearchCard({ report, language }: { report: ResearchReport; language: UiLanguage }) {
  const copy = getUiCopy(language);
  const swot = report.swot || { strengths: [], weaknesses: [], opportunities: [], threats: [] };
  const columns = [
    [copy.conversation.swot.strengths, swot.strengths, 'strengths'],
    [copy.conversation.swot.weaknesses, swot.weaknesses, 'weaknesses'],
    [copy.conversation.swot.opportunities, swot.opportunities, 'opportunities'],
    [copy.conversation.swot.threats, swot.threats, 'threats'],
  ] as const;
  return (
    <section className="research-card" aria-label={copy.conversation.research}>
      <div className="research-card-heading">
        <span>{copy.conversation.research}</span>
        <small>{copy.conversation.sources(report.sources_used_count ?? report.sources?.length ?? 0)}</small>
      </div>
      <h4>{report.topic || report.query}</h4>
      <p>{report.executive_summary}</p>
      {report.market_overview && <p className="research-overview">{report.market_overview}</p>}
      {report.key_trends?.length > 0 && (
        <div className="research-section"><strong>{copy.conversation.keyTrends}</strong><ul>{report.key_trends.map((item) => <li key={item}>{item}</li>)}</ul></div>
      )}
      {([['Recommendations', report.recommendations], ['How to compete', report.competitive_strategy], ['Risks & assumptions', report.risks_and_assumptions], ['Next steps', report.next_steps]] as const).map(([label, values]) => values?.length ? <div className="research-section" key={label}><strong>{label}</strong><ul>{values.map((item) => <li key={item}>{item}</li>)}</ul></div> : null)}
      <div className="research-swot">
        {columns.map(([label, values, className]) => (
          <div className={`research-swot-column ${className}`} key={label}><strong>{label}</strong><ul>{values.length ? values.map((item) => <li key={item}>{item}</li>) : <li>{copy.conversation.sourceBackedFinding}</li>}</ul></div>
        ))}
      </div>
      {report.sources?.length > 0 && (
        <div className="research-sources"><strong>{copy.conversation.sources(report.sources.length)}</strong>{report.sources.map((source) => <a href={source.url} target="_blank" rel="noreferrer" key={source.url}>{source.title || source.url}</a>)}</div>
      )}
      {report.warnings?.map((warning) => <small className="research-warning" key={warning}>{warning}</small>)}
    </section>
  );
}
