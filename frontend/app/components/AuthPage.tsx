'use client';

import { FormEvent, useState } from 'react';
import {
  AuthSession,
  SignUpInput,
  UserProfile,
  signIn,
  signUp,
} from '../lib/aether-api';

type Props = { onAuthenticated: (session: AuthSession) => void };
type FieldKey = keyof UserProfile;

const emptyProfile: UserProfile = {
  full_name: '',
  email: '',
  phone: '',
  country: '',
  timezone: 'Asia/Kolkata',
  occupation: '',
  company_name: '',
  website: '',
  industry: '',
  company_size: '',
  business_stage: '',
  business_model: '',
  revenue_model: '',
  products_services: '',
  target_customers: '',
  goals: '',
  challenges: '',
  business_context: '',
};

const personalFields: Array<[FieldKey, string, string]> = [
  ['full_name', 'Full name', 'Your name'],
  ['email', 'Email address', 'you@company.com'],
  ['phone', 'Phone number', '+91 …'],
  ['country', 'Country or region', 'India'],
  ['timezone', 'Timezone', 'Asia/Kolkata'],
  ['occupation', 'Occupation', 'Founder, consultant, product manager…'],
];

const businessFields: Array<[FieldKey, string, string]> = [
  ['company_name', 'Business or company name', 'The name people know you by'],
  ['website', 'Website', 'https://…'],
  ['industry', 'Industry', 'SaaS, retail, education, healthcare…'],
  ['company_size', 'Team size', 'Solo, 2–10, 11–50…'],
  ['business_stage', 'Business stage', 'Idea, launched, growing, scaling…'],
  ['business_model', 'Business model', 'How the business creates and delivers value'],
  ['revenue_model', 'Revenue model', 'Subscriptions, services, marketplace, ads…'],
  ['products_services', 'Products or services', 'What you offer and what makes it useful'],
  ['target_customers', 'Target customers', 'Who you serve and who pays'],
  ['goals', 'Goals', 'What should ElaraX help you accomplish?'],
  ['challenges', 'Current challenges', 'What is slowing the business down?'],
  ['business_context', 'Business context', 'Anything important ElaraX should understand about your work'],
];

export default function AuthPage({ onAuthenticated }: Props) {
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [profile, setProfile] = useState<UserProfile>(emptyProfile);
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const update = (key: FieldKey, value: string) => {
    setProfile((current) => ({ ...current, [key]: value }));
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const session = mode === 'signin'
        ? await signIn(profile.email, password)
        : await signUp({ ...profile, password } as SignUpInput);
      onAuthenticated(session);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Authentication failed.');
    } finally {
      setBusy(false);
    }
  };

  const switchMode = (nextMode: 'signin' | 'signup') => {
    setMode(nextMode);
    setError('');
    setPassword('');
  };

  return (
    <main className="auth-page">
      <section className="auth-intro">
        <div className="brand-mark">Elara<span>X</span></div>
        <span className="eyebrow">A calm second mind</span>
        <h1>Your work context,<br /><em>kept with care.</em></h1>
        <p>Set up your private ElaraX workspace so your assistant understands who you are, what you do, and where your business is going.</p>
        <div className="auth-promise"><i />Your profile stays in this local ElaraX workspace.</div>
      </section>

      <section className="auth-card" aria-labelledby="auth-heading">
        <div className="auth-tabs" role="tablist" aria-label="Account access">
          <button type="button" className={mode === 'signin' ? 'active' : ''} onClick={() => switchMode('signin')} role="tab" aria-selected={mode === 'signin'}>Sign in</button>
          <button type="button" className={mode === 'signup' ? 'active' : ''} onClick={() => switchMode('signup')} role="tab" aria-selected={mode === 'signup'}>Create account</button>
        </div>
        <div className="auth-heading">
          <span className="eyebrow">{mode === 'signin' ? 'Welcome back' : 'Your workspace'}</span>
          <h2 id="auth-heading">{mode === 'signin' ? 'Continue to ElaraX.' : 'Tell ElaraX about you.'}</h2>
          <p>{mode === 'signin' ? 'Sign in to return to your command center.' : 'A few thoughtful details make business research and daily assistance more useful.'}</p>
        </div>

        <form onSubmit={submit} className="auth-form">
          {mode === 'signin' ? (
            <div className="auth-section auth-section-single">
              <label>Email address<input type="email" value={profile.email} onChange={(event) => update('email', event.target.value)} placeholder="you@company.com" autoComplete="email" required /></label>
              <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Your password" autoComplete="current-password" required /></label>
            </div>
          ) : (
            <>
              <div className="auth-section">
                <div className="auth-section-title"><strong>About you</strong><span>Personal details</span></div>
                <div className="auth-grid">{personalFields.map(([key, label, placeholder]) => (
                  <label key={key} className={key === 'full_name' || key === 'occupation' ? 'wide' : ''}>{label}<input type={key === 'email' ? 'email' : 'text'} value={profile[key]} onChange={(event) => update(key, event.target.value)} placeholder={placeholder} autoComplete={key === 'full_name' ? 'name' : key === 'email' ? 'email' : 'off'} required={['full_name', 'email', 'occupation'].includes(key)} /></label>
                ))}</div>
              </div>
              <div className="auth-section">
                <div className="auth-section-title"><strong>Business context</strong><span>What you are building</span></div>
                <div className="auth-grid">{businessFields.map(([key, label, placeholder]) => (
                  <label key={key} className={['business_model', 'products_services', 'target_customers', 'goals', 'challenges', 'business_context'].includes(key) ? 'wide' : ''}>
                    {label}
                    {['business_model', 'revenue_model', 'products_services', 'target_customers', 'goals', 'challenges', 'business_context'].includes(key)
                      ? <textarea rows={key === 'business_context' ? 3 : 2} value={profile[key]} onChange={(event) => update(key, event.target.value)} placeholder={placeholder} required={['company_name', 'industry', 'business_model', 'business_context'].includes(key)} />
                      : <input type="text" value={profile[key]} onChange={(event) => update(key, event.target.value)} placeholder={placeholder} autoComplete="organization" required={['company_name', 'industry'].includes(key)} />}
                  </label>
                ))}</div>
              </div>
              <div className="auth-section auth-section-single"><label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" autoComplete="new-password" minLength={8} required /></label></div>
            </>
          )}
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button className="auth-submit" type="submit" disabled={busy}>{busy ? 'Please wait…' : mode === 'signin' ? 'Open my workspace' : 'Create my workspace'}</button>
        </form>
        <p className="auth-switch">{mode === 'signin' ? 'New to ElaraX?' : 'Already have an account?'} <button type="button" onClick={() => switchMode(mode === 'signin' ? 'signup' : 'signin')}>{mode === 'signin' ? 'Create an account' : 'Sign in'}</button></p>
      </section>
    </main>
  );
}
