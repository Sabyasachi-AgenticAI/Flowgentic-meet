import React from 'react';
import { useParticipants, useRoomContext } from '@livekit/components-react';
import { Track } from 'livekit-client';

interface AdminPanelProps {
  roomName: string;
}

export function AdminPanel({ roomName }: AdminPanelProps) {
  const participants = useParticipants();
  const room = useRoomContext();
  const [isOpen, setIsOpen] = React.useState(false);

  const toggleMute = async (identity: string, isCurrentlyMuted: boolean) => {
    const participant = participants.find(p => p.identity === identity);
    if (!participant) return;

    const audioTracks = Array.from(participant.audioTrackPublications.values() as IterableIterator<any>);
    if (audioTracks.length === 0) {
      alert('Participant has no audio track.');
      return;
    }

    const micTrack = audioTracks[0];

    try {
      if (micTrack) {
        // This disables/enables the track LOCALLY on the frontend
        // which bypasses any server-side privacy restrictions on unmuting
        micTrack.setEnabled(isCurrentlyMuted);
      }
    } catch (error) {
      console.error('Error toggling local mute:', error);
      alert('Failed to change audio state locally.');
    }
  };

  const muteAllHumans = async () => {
    const humans = participants.filter(p => !p.identity.toLowerCase().includes('agent') && !p.isLocal);
    for (const h of humans) {
      const audioTracks = Array.from(h.audioTrackPublications.values() as IterableIterator<any>);
      if (audioTracks.length > 0) {
        await fetch('/api/mute-participant', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            roomName,
            identity: h.identity,
            trackSid: audioTracks[0].trackSid,
            muted: true
          })
        });
      }
    }
    alert('Muted all human participants.');
  };

  return (
    <div style={{ position: 'fixed', bottom: '2rem', left: '2rem', zIndex: 1000 }}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        style={{ background: '#3b82f6', color: 'white', border: 'none', padding: '0.6rem 1.2rem', borderRadius: '2rem', cursor: 'pointer', fontWeight: 'bold' }}
      >
        Host Controls {isOpen ? '▲' : '▼'}
      </button>

      {isOpen && (
        <div style={{ position: 'absolute', bottom: '3rem', left: '0', background: 'rgba(15, 23, 42, 0.95)', border: '1px solid #334155', borderRadius: '0.75rem', padding: '1rem', width: '300px', backdropFilter: 'blur(10px)' }}>
          <h3 style={{ color: 'white', marginTop: 0, marginBottom: '1rem', fontSize: '1rem' }}>Admin Panel</h3>

          <button 
            onClick={muteAllHumans}
            style={{ width: '100%', background: '#dc2626', color: 'white', border: 'none', padding: '0.4rem', borderRadius: '0.5rem', marginBottom: '1rem', cursor: 'pointer' }}
          >
            Mute All Humans
          </button>

          <div style={{ maxHeight: '200px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {participants.map(p => {
              if (p.isLocal) return null; // Don't show host
              const isAgent = p.identity.toLowerCase().includes('agent');
              const audioTrack = Array.from(p.audioTrackPublications.values() as IterableIterator<any>)[0];
              const isMuted = audioTrack ? !audioTrack.isEnabled : true;
              
              return (
                <div key={p.identity} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.05)', padding: '0.5rem', borderRadius: '0.25rem' }}>
                  <span style={{ color: 'white', fontSize: '0.85rem', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', maxWidth: '150px' }}>
                    {p.identity} {isAgent && '(AI)'}
                  </span>
                  <button 
                    onClick={() => toggleMute(p.identity, isMuted)}
                    style={{ background: isMuted ? '#10b981' : '#f59e0b', color: 'white', border: 'none', padding: '0.2rem 0.5rem', borderRadius: '0.25rem', fontSize: '0.75rem', cursor: 'pointer' }}
                  >
                    {isMuted ? 'Unmute' : 'Mute'}
                  </button>
                </div>
              );
            })}
            {participants.filter(p => !p.isLocal).length === 0 && (
              <div style={{ color: '#94a3b8', fontSize: '0.8rem', textAlign: 'center' }}>No other participants</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
