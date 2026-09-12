'use client';

import { ActionItem, DashboardData } from '../lib/aether-api';

type DashboardPanelProps = {
  data?: DashboardData;
  loading: boolean;
  refreshing: boolean;
  onRefresh: () => void;
  onCompleteActionItem: (id: string) => void;
  completingActionItemId?: string;
};

function formatTime(value?: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

function display(value?: string | null): string {
  return value?.trim() || 'Not provided';
}

function activityTone(type: string): string {
  if (type === 'assistant') return 'activity-tone-lake';
  if (type === 'account') return 'activity-tone-coral';
  return 'activity-tone-signal';
}

export default function DashboardPanel({
  data,
  loading,
  refreshing,
  onRefresh,
  onCompleteActionItem,
  completingActionItemId,
}: DashboardPanelProps) {
  if (loading && !data) {
    return (
      <section className="dashboard-panel dashboard-loading" aria-label="Workspace dashboard">
        <div className="dashboard-skeleton dashboard-skeleton-wide" />
        <div className="dashboard-skeleton-grid">
          <div className="dashboard-skeleton" /><div className="dashboard-skeleton" /><div className="dashboard-skeleton" />
        </div>
        <p>Loading your live workspace records…</p>
      </section>
    );
  }

  if (!data) return null;

  const profile = data.user.profile;
  const openItems = data.action_items.filter((item) => item.status === 'open');
  const todayEvents = data.overview.today_events ?? [];
  const urgentEmails = data.overview.urgent_emails ?? [];

  return (
    <section className="dashboard-panel" aria-label="Workspace dashboard">
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">Live workspace dashboard</p>
          <h2>{display(profile.company_name)}</h2>
          <p className="dashboard-subtitle">{display(profile.industry)} · {display(profile.business_stage)} · {display(profile.business_model)}</p>
        </div>
        <div className="dashboard-header-actions">
          <span className="live-pill"><i /> Live · {formatTime(data.updated_at)}</span>
          <button type="button" className="dashboard-refresh" onClick={onRefresh} disabled={refreshing}>
            <span aria-hidden="true">↻</span>{refreshing ? 'Updating…' : 'Refresh'}
          </button>
        </div>
      </header>

      <div className="dashboard-kpis">
        <article><span>Open actions</span><strong>{data.stats.open_action_items}</strong><small>{data.stats.completed_action_items} completed</small></article>
        <article><span>Today</span><strong>{data.stats.today_events}</strong><small>{data.stats.tomorrow_events} planned tomorrow</small></article>
        <article><span>Priority inbox</span><strong>{data.stats.urgent_emails}</strong><small>{data.google.connected ? 'Google connected' : 'Connect Google to sync'}</small></article>
        <article><span>Profile complete</span><strong>{data.stats.profile_completion}%</strong><small>{data.stats.activity_count} recorded activities</small></article>
      </div>

      <section className="dashboard-progress-card">
        <div className="dashboard-card-heading"><div><span>Owner progress</span><h3>{display(profile.full_name)}’s tracked momentum</h3></div><b>{data.owner_progress.active_days}/7 active days</b></div>
        <div className="dashboard-progress-layout">
          <div className="dashboard-progress-metrics">
            <div><span>Workspace setup</span><strong>{data.owner_progress.profile_setup}%</strong><div className="progress-track"><i style={{ width: `${data.owner_progress.profile_setup}%` }} /></div></div>
            <div><span>Follow-through</span><strong>{data.owner_progress.action_completion}%</strong><div className="progress-track progress-track-coral"><i style={{ width: `${data.owner_progress.action_completion}%` }} /></div></div>
            <div><span>Weekly momentum</span><strong>{data.owner_progress.activity_momentum}%</strong><div className="progress-track progress-track-signal"><i style={{ width: `${data.owner_progress.activity_momentum}%` }} /></div></div>
          </div>
          <div className="activity-track" aria-label="Activity over the last seven days">
            <span>7-day activity track</span>
            <div className="activity-track-bars">
              {data.owner_progress.tracked_days.map((day) => {
                const maxCount = Math.max(1, ...data.owner_progress.tracked_days.map((entry) => entry.count));
                return <div className="activity-track-day" key={day.date} title={`${day.date}: ${day.count} activities`}><i style={{ height: `${Math.max(day.count ? 14 : 4, (day.count / maxCount) * 100)}%` }} /><small>{day.date.slice(5)}</small></div>;
              })}
            </div>
          </div>
        </div>
        <div className="progress-focus-row"><div><span>Current goal</span><strong>{display(data.owner_progress.goal)}</strong></div><div><span>Next tracked step</span><strong>{display(data.owner_progress.next_action)}</strong></div><div><span>Challenge being tracked</span><strong>{display(data.owner_progress.current_challenge)}</strong></div></div>
      </section>

      <div className="dashboard-grid">
        <section className="dashboard-card dashboard-profile-card">
          <div className="dashboard-card-heading"><div><span>Business profile</span><h3>Who you are building for</h3></div><b>{display(profile.occupation)}</b></div>
          <div className="dashboard-fields">
            <div><span>Founder</span><strong>{display(profile.full_name)}</strong></div>
            <div><span>Company</span><strong>{display(profile.company_name)}</strong></div>
            <div><span>Team size</span><strong>{display(profile.company_size)}</strong></div>
            <div><span>Revenue model</span><strong>{display(profile.revenue_model)}</strong></div>
            <div className="dashboard-field-wide"><span>Products or services</span><strong>{display(profile.products_services)}</strong></div>
            <div className="dashboard-field-wide"><span>Target customers</span><strong>{display(profile.target_customers)}</strong></div>
          </div>
        </section>

        <section className="dashboard-card dashboard-activity-card">
          <div className="dashboard-card-heading"><div><span>Recent records</span><h3>Activity timeline</h3></div><b>{data.activity.length} events</b></div>
          {data.activity.length ? (
            <div className="dashboard-activity-list">
              {data.activity.slice(0, 6).map((activity) => (
                <div className="dashboard-activity" key={activity.id}>
                  <i className={activityTone(activity.activity_type)} />
                  <div><strong>{activity.title}</strong><p>{activity.detail || activity.status}</p></div>
                  <time>{formatTime(activity.created_at)}</time>
                </div>
              ))}
            </div>
          ) : <p className="dashboard-empty">Your assistant activity will appear here as you work.</p>}
        </section>

        <section className="dashboard-card dashboard-operations-card">
          <div className="dashboard-card-heading"><div><span>Operational pulse</span><h3>What needs attention</h3></div><b>{data.health.status}</b></div>
          <div className="dashboard-operation-list">
            {urgentEmails.slice(0, 2).map((email) => <div className="dashboard-operation" key={email.id}><span className="operation-mark operation-mark-coral">!</span><div><strong>{email.subject}</strong><p>{email.sender}</p></div></div>)}
            {todayEvents.slice(0, 2).map((event) => <div className="dashboard-operation" key={event.id}><span className="operation-mark operation-mark-lake">◷</span><div><strong>{event.title}</strong><p>{event.time}</p></div></div>)}
            {!urgentEmails.length && !todayEvents.length && <p className="dashboard-empty">No urgent inbox or calendar records right now.</p>}
          </div>
        </section>

        <section className="dashboard-card dashboard-actions-card">
          <div className="dashboard-card-heading"><div><span>Follow-ups</span><h3>Action items</h3></div><b>{openItems.length} open</b></div>
          {openItems.length ? (
            <div className="dashboard-action-list">
              {openItems.slice(0, 5).map((item: ActionItem) => (
                <label className="dashboard-action" key={item.id}>
                  <input type="checkbox" checked={false} disabled={completingActionItemId === item.id} onChange={() => onCompleteActionItem(item.id)} />
                  <span><strong>{item.description}</strong><small>{item.due_date ? `Due ${item.due_date}` : item.source_subject || 'From assistant records'}</small></span>
                </label>
              ))}
            </div>
          ) : <p className="dashboard-empty">No open follow-ups. You are clear for now.</p>}
        </section>
      </div>

      <section className="dashboard-context-card">
        <div><span>Business context</span><h3>{display(profile.goals)}</h3><p>{display(profile.business_context)}</p></div>
        <div className="dashboard-context-meta"><span>Current challenges</span><strong>{display(profile.challenges)}</strong><small>{display(profile.website)}</small></div>
      </section>
    </section>
  );
}
