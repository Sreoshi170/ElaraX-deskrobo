import React from 'react';
import { GoogleConnectionStatus, InvoiceAutomationStatus, Overview } from '../lib/aether-api';
import { UiLanguage, getUiCopy } from '../lib/i18n';

export type ConnectionsStripProps = {
  isGoogleConnected: boolean;
  googleStatus?: GoogleConnectionStatus;
  googleConnecting: boolean;
  handleGoogleConnect: () => Promise<void>;
  handleGoogleDisconnect: () => Promise<void>;
  invoiceAutomation?: InvoiceAutomationStatus;
  invoiceAutomationUpdating: boolean;
  handleInvoiceAutomationToggle: () => Promise<void>;
  overview?: Overview;
  language: UiLanguage;
};

export default function ConnectionsStrip({
  isGoogleConnected,
  googleStatus,
  googleConnecting,
  handleGoogleConnect,
  handleGoogleDisconnect,
  invoiceAutomation,
  invoiceAutomationUpdating,
  handleInvoiceAutomationToggle,
  overview,
  language,
}: ConnectionsStripProps) {
  const copy = getUiCopy(language);
  return (
    <>
      <section className="connection-strip" id="connections" aria-label={copy.connections.aria}>
        <div className="strip-intro">
          <span className="strip-icon" aria-hidden="true">+</span>
          <div>
            <span>{copy.connections.connectedSurfaces}</span>
            <strong>{copy.connections.privateControls}</strong>
          </div>
        </div>
        
        <div className={`strip-item${isGoogleConnected ? ' connected' : ''}`} id="google-connection">
          <span className="strip-service-icon google-mark" aria-hidden="true">G</span>
          <div className="strip-copy">
            <strong>Google</strong>
            <span>{isGoogleConnected ? (googleStatus?.email ?? copy.connections.gmailCalendarActive) : copy.connections.gmailCalendar}</span>
          </div>
          <button 
            type="button" 
            className="strip-action" 
            onClick={() => void (isGoogleConnected ? handleGoogleDisconnect() : handleGoogleConnect())} 
            disabled={googleConnecting} 
            aria-busy={googleConnecting}
          >
            {isGoogleConnected ? copy.connections.disconnect : googleConnecting ? copy.connections.waiting : copy.connections.connect}
          </button>
        </div>
        
        <span className="strip-separator" aria-hidden="true" />
        
        <div className={`strip-item invoice-strip${invoiceAutomation?.enabled ? ' active' : ''}`} id="invoice-automation">
          <span className="strip-service-icon invoice-mark" aria-hidden="true">↺</span>
          <div className="strip-copy">
            <strong>{copy.connections.invoiceAssistant}</strong>
            <span>{invoiceAutomation?.enabled ? copy.connections.invoiceOn(invoiceAutomation.total_replies_sent) : copy.connections.invoicePaused}</span>
          </div>
          <button 
            type="button" 
            className={`switch${invoiceAutomation?.enabled ? ' on' : ''}`} 
            onClick={() => void handleInvoiceAutomationToggle()} 
            disabled={!isGoogleConnected || !invoiceAutomation || invoiceAutomationUpdating} 
            aria-label={invoiceAutomation?.enabled ? copy.connections.pauseInvoice : copy.connections.enableInvoice}
            aria-pressed={Boolean(invoiceAutomation?.enabled)}
          >
            <span />
          </button>
        </div>
      </section>
      
      {(googleStatus?.error || overview?.integration_error || invoiceAutomation?.last_error) && (
        <div className="integration-warning" role="status">
          {overview?.integration_error ?? googleStatus?.error ?? invoiceAutomation?.last_error}
        </div>
      )}
    </>
  );
}
