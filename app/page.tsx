'use client';

import { useRouter } from 'next/navigation';
import React from 'react';
import { generateRoomId } from '@/lib/client-utils';
import styles from '../styles/Home.module.css';

export default function Page() {
  const router = useRouter();

  const startMeeting = () => {
    // Generate a secure, unique room ID
    const roomId = generateRoomId();
    router.push(`/rooms/${roomId}`);
  };

  return (
    <>
      <main className={styles.main}>
        <div className="header">
          <h1>Flowgentic <span>Meet</span></h1>
          <p>
            The next generation of AI-native video conferencing. 
            Collaborate seamlessly with intelligent voice agents.
          </p>
        </div>

        <div className={styles.actionContainer}>
          <button 
            className="flowgentic-btn-hero" 
            onClick={startMeeting}
          >
            Start Meeting
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
          </button>
        </div>
      </main>

      <footer>
        &copy; {new Date().getFullYear()} Flowgentic AI. All rights reserved.
      </footer>
    </>
  );
}
