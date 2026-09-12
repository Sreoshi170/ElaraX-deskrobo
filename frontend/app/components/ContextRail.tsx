import React from 'react';
import { Overview, ActionItem, EmailResult } from '../lib/aether-api';
import { UiLanguage, getUiCopy, localeForUiLanguage } from '../lib/i18n';

export type ContextRailProps = {
  overview?: Overview;
  attentionCount?: number;
  urgentEmail?: EmailResult;
  todayEvents: Array<{
    id: string;
    title: string;
    time: string;
    participants: string[];
  }>;
  tomorrowEvents: Array<{
    id: string;
    title: string;
    time: string;
    participants: string[];
  }>;
  actionItems: ActionItem[];
  completingActionItemId?: string;
  submitCommand: (message: string) => Promise<void>;
  handleCompleteActionItem: (itemId: string) => Promise<void>;
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

export default function ContextRail({
  overview,
  attentionCount,
  urgentEmail,
  todayEvents,
  tomorrowEvents,
  actionItems,
  completingActionItemId,
  submitCommand,
  handleCompleteActionItem,
  language,
}: ContextRailProps) {
  const copy = getUiCopy(language);
  const locale = localeForUiLanguage(language);
  const robotMode = overview?.robot.mode ?? copy.robot.simulation;
  const robotMotion = overview?.robot.motion ?? copy.robot.stopped;
  return (
    <aside className="context-rail" aria-label={copy.context.aria}>
      <section className="today-surface" id="briefing">
        <div className="surface-header">
          <div>
            <p className="eyebrow">{copy.welcome.today}</p>
            <h2>{copy.context.title}</h2>
          </div>
          <span className="today-count">{copy.context.countInView(attentionCount)}</span>
        </div>
        
        <div className="today-summary">
          <div className={`summary-mark${urgentEmail ? ' urgent' : ''}`}>
            {urgentEmail ? '!' : '✓'}
          </div>
          <div>
            <span>{copy.context.attention}</span>
            <strong>{attentionCount !== undefined ? copy.context.attentionCount(attentionCount) : copy.context.loading}</strong>
            <p>{copy.context.summary}</p>
          </div>
        </div>
        
        <button type="button" className="briefing-action" onClick={() => void submitCommand(copy.commands.briefing)}>
          {copy.context.playBriefing} <span>{copy.context.voice}</span>
        </button>
        
        <div className="today-block" id="email">
          <div className="today-block-heading">
            <span>{copy.context.priorityInbox}</span>
            <strong>{overview ? copy.context.urgentCount(overview.urgent_emails.length) : copy.context.inboxLoading}</strong>
          </div>
          {urgentEmail ? (
            <button type="button" className="inbox-card" onClick={() => void submitCommand(copy.commands.urgentEmails)}>
              <div className="sender-avatar">{senderInitials(urgentEmail)}</div>
              <div>
                <span>{urgentEmail.sender_name || urgentEmail.sender} — {emailTimestamp(urgentEmail.date, locale) || copy.context.recent}</span>
                <strong>{urgentEmail.subject}</strong>
                <p>{urgentEmail.snippet || copy.conversation.noPreview}</p>
              </div>
              <i />
            </button>
          ) : (
            <div className="inbox-card">
              <div className="sender-avatar">✓</div>
              <div>
                <span>{copy.context.inboxClear}</span>
                <strong>{copy.context.noPriority}</strong>
                <p>{copy.context.nothingUrgent}</p>
              </div>
            </div>
          )}
        </div>
        
        {actionItems.length > 0 && (
          <div className="today-block action-items-block" id="action-items">
            <div className="today-block-heading">
              <span>{copy.context.followUps}</span>
              <strong>{copy.context.open(actionItems.length)}</strong>
            </div>
            <div className="action-item-list">
              {actionItems.map((item) => (
                <label className="action-item" key={item.id}>
                  <input 
                    type="checkbox" 
                    checked={false} 
                    disabled={completingActionItemId === item.id} 
                    onChange={() => void handleCompleteActionItem(item.id)} 
                  />
                  <span>
                    <strong>{item.description}</strong>
                    {item.due_date && <small>{copy.context.due(item.due_date)}</small>}
                    {item.source_subject && <small>{copy.context.from(item.source_subject)}</small>}
                  </span>
                </label>
              ))}
            </div>
          </div>
        )}
        
        <div className="today-block schedule-block" id="activity">
          <div className="today-block-heading">
            <span>{copy.context.schedule}</span>
            <button type="button" onClick={() => void submitCommand(copy.commands.calendar)}>
              {copy.context.askSchedule}
            </button>
          </div>
          <div className="timeline" id="calendar">
            {todayEvents.map((event) => (
              <article className="timeline-item" key={event.id}>
                <time>{event.time.replace(' AM', '').replace(' PM', '')}</time>
                <span className="timeline-dot mint" />
                <div>
                  <strong>{event.title}</strong>
                  <p>{copy.context.todayParticipants(event.participants.length)}</p>
                </div>
              </article>
            ))}
            {tomorrowEvents.map((event) => (
              <article className="timeline-item" key={event.id}>
                <time>{event.time.replace(' AM', '').replace(' PM', '')}</time>
                <span className="timeline-dot violet" />
                <div>
                  <strong>{event.title}</strong>
                  <p>{copy.context.tomorrowParticipants(event.participants.length)}</p>
                </div>
              </article>
            ))}
            {!todayEvents.length && !tomorrowEvents.length && (
              <p className="empty-timeline">{copy.context.noMeetings}</p>
            )}
          </div>
        </div>
      </section>
      
      <section className="robot-rail" id="robot">
        <div className="robot-rail-heading">
          <span>{copy.context.robot}</span>
          <span className="online-label">{copy.context.simulatorReady}</span>
        </div>
        <button type="button" className="robot-card" onClick={() => void submitCommand(copy.commands.robotStatus)}>
          <div className="robot-visual"><i /><i /></div>
          <div>
            <strong>Aether One</strong>
            <span>{copy.context.robotMode(robotMode, robotMotion)}</span>
          </div>
          <span className="robot-action">{copy.context.status}</span>
        </button>
      </section>
      <footer className="rail-footer"><i />{copy.context.privateSession}</footer>
    </aside>
  );
}
