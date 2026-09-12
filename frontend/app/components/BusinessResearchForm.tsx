import React, { FormEvent, useState } from 'react';

type Props = { busy: boolean; submitCommand: (command: string) => void };

const fields = [
  ['business_name', 'Business / product name', 'e.g. FreshCart'],
  ['industry', 'Industry and market', 'e.g. grocery delivery in Bengaluru'],
  ['location', 'Target geography', 'City, country, or online market'],
  ['stage', 'Business stage', 'Idea, launched, growing, or revenue'],
  ['offer', 'What do you sell?', 'Product, service, pricing, and key differentiator'],
  ['customer', 'Ideal customer', 'Who buys, and what do they need?'],
  ['problem', 'Problem to solve', 'What pain or unmet need are you addressing?'],
  ['competitors', 'Known competitors / alternatives', 'Names or “not sure”'],
  ['goal', 'Main goal', 'e.g. find product-market fit or increase sales'],
];

export default function BusinessResearchForm({ busy, submitCommand }: Props) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [open, setOpen] = useState(false);
  const update = (key: string, value: string) => setValues((current) => ({ ...current, [key]: value }));
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const lines = fields.map(([key]) => `${key.replace('_', ' ')}: ${(values[key] || '').trim()}`).filter((line) => !line.endsWith(':'));
    if (lines.length < 3) return;
    submitCommand(`Business brief research\nBUSINESS BRIEF\n${lines.join('\n')}\n\nResearch this market and provide: an evidence-backed overview, pros and cons, SWOT, competitors, improvements, ways to beat competitors, business strategies, risks, and a 30/60/90-day action plan.`);
  };
  return (
    <section className="business-research-panel" aria-label="Business strategy research">
      <button type="button" className="business-research-toggle" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        <span><strong>Startup & small-business research</strong><small>Give ElaraX your context for a practical market and strategy report</small></span><b>{open ? '−' : '+'}</b>
      </button>
      {open && <form className="business-research-form" onSubmit={submit}>
        <p>Share what you know. ElaraX will separate sourced findings from assumptions and return SWOT, competitive moves, improvements, risks, and next steps.</p>
        <div className="business-research-grid">{fields.map(([key, label, placeholder]) => (
          <label key={key} className={key === 'offer' || key === 'problem' ? 'wide' : ''}>{label}<textarea rows={key === 'offer' || key === 'problem' ? 2 : 1} value={values[key] || ''} onChange={(event) => update(key, event.target.value)} placeholder={placeholder} /></label>
        ))}</div>
        <button className="business-research-submit" type="submit" disabled={busy}>Run business research</button>
      </form>}
    </section>
  );
}
