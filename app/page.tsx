'use client';

import { useRouter } from 'next/navigation';
import React from 'react';
import { generateRoomId } from '@/lib/client-utils';
import { useAuth, SignInButton, UserButton } from '@clerk/nextjs';
import styles from '../styles/Home.module.css';

export default function Page() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();

  const [generatedLink, setGeneratedLink] = React.useState<string | null>(null);

  const startMeeting = () => {
    const roomId = generateRoomId();
    router.push(`/rooms/${roomId}?host=true`);
  };

  const createInviteLink = () => {
    const roomId = generateRoomId();
    const url = `${window.location.origin}/rooms/${roomId}`;
    setGeneratedLink(url);
    
    // Auto-copy to clipboard
    navigator.clipboard.writeText(url);
  };

  const emailSubject = encodeURIComponent("Join my Flowgentic Meet");
  const emailBody = (url: string) => encodeURIComponent(`Hi there,\n\nI'd like to invite you to a meeting on Flowgentic Meet.\n\nJoin the meeting here: ${url}\n\nSee you there!`);

  return (
    <>
      <main className={styles.main}>
        <div className="header">
          <div className="hero-logo-container">
            <img 
              src="/flowgentic-meet-icon.svg" 
              alt="Flowgentic Meet Logo" 
              className="hero-logo" 
            />
          </div>
          <h1>Flowgentic <span>Meet</span></h1>
          <p>
            The next generation of AI-native video conferencing. 
            Collaborate seamlessly with intelligent voice agents.
          </p>
        </div>

        {isLoaded && isSignedIn && (
          <div style={{ position: 'absolute', top: '1.5rem', right: '1.5rem' }}>
            <UserButton />
          </div>
        )}

        <div className={styles.actionContainer} style={{ width: '100%', maxWidth: '350px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <button 
            className="flowgentic-btn-hero" 
            onClick={startMeeting}
            style={{ width: '100%', marginBottom: '1rem', justifyContent: 'center' }}
          >
            Start Meeting
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
          </button>

          {!generatedLink ? (
            <button 
              onClick={createInviteLink}
              style={{ 
                background: 'transparent', 
                border: 'none',
                color: 'rgba(255, 255, 255, 0.7)',
                fontSize: '0.95rem',
                fontWeight: '500',
                padding: '0.5rem 1rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                transition: 'all 0.3s ease',
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.color = '#fff';
                e.currentTarget.style.textShadow = '0 0 12px rgba(255, 255, 255, 0.4)';
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.color = 'rgba(255, 255, 255, 0.7)';
                e.currentTarget.style.textShadow = 'none';
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
              <span style={{ borderBottom: '1px solid rgba(255,255,255,0.3)', paddingBottom: '1px' }}>
                Generate Meeting Link
              </span>
            </button>
          ) : (
            <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center' }}>
              <div style={{ width: '100%', background: 'rgba(255,255,255,0.05)', padding: '1rem 1.5rem', borderRadius: '2rem', border: '1px solid var(--border)', display: 'flex', gap: '1rem', alignItems: 'center', justifyContent: 'center' }}>
                <code style={{ fontSize: '0.9rem', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{generatedLink}</code>
                <span style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 'bold' }}>COPIED!</span>
              </div>
              <div style={{ display: 'flex', gap: '1rem', width: '100%', justifyContent: 'center' }}>
                <a 
                  href={`mailto:?subject=${emailSubject}&body=${emailBody(generatedLink)}`}
                  style={{ color: '#ec4899', textDecoration: 'none', fontSize: '0.95rem', fontWeight: '700' }}
                >
                  Send via Email
                </a>
                <span style={{ color: 'rgba(255,255,255,0.3)' }}>|</span>
                <a 
                  href={`${generatedLink}?host=true`}
                  style={{ color: '#10b981', textDecoration: 'none', fontSize: '0.95rem', fontWeight: '700' }}
                >
                  Join as Host
                </a>
              </div>
            </div>
          )}
        </div>
      </main>

      <footer>
        &copy; {new Date().getFullYear()} Flowgentic AI. All rights reserved.
      </footer>
    </>
  );
}
