'use client';

import React from 'react';
import { decodePassphrase } from '@/lib/client-utils';
import { DebugMode } from '@/lib/Debug';
import { KeyboardShortcuts } from '@/lib/KeyboardShortcuts';
import { RecordingIndicator } from '@/lib/RecordingIndicator';
import { SettingsMenu } from '@/lib/SettingsMenu';
import { ConnectionDetails } from '@/lib/types';
import {
  formatChatMessageLinks,
  LocalUserChoices,
  PreJoin,
  RoomContext,
  VideoConference,
} from '@livekit/components-react';
import {
  ExternalE2EEKeyProvider,
  RoomOptions,
  VideoCodec,
  VideoPresets,
  Room,
  DeviceUnsupportedError,
  RoomConnectOptions,
  RoomEvent,
  TrackPublishDefaults,
  VideoCaptureOptions,
  Track,
} from 'livekit-client';
import { useRouter } from 'next/navigation';
import { useSetupE2EE } from '@/lib/useSetupE2EE';
import { useLowCPUOptimizer } from '@/lib/usePerfomanceOptimiser';

const CONN_DETAILS_ENDPOINT =
  process.env.NEXT_PUBLIC_CONN_DETAILS_ENDPOINT ?? '/api/connection-details';
const SHOW_SETTINGS_MENU = process.env.NEXT_PUBLIC_SHOW_SETTINGS_MENU == 'true';

export function PageClientImpl(props: {
  roomName: string;
  region?: string;
  hq: boolean;
  codec: VideoCodec;
  singlePeerConnection: boolean;
  isHost?: boolean;
}) {
  const [preJoinChoices, setPreJoinChoices] = React.useState<LocalUserChoices | undefined>(
    undefined,
  );
  const preJoinDefaults = React.useMemo(() => {
    return {
      username: '',
      videoEnabled: true,
      audioEnabled: true,
    };
  }, []);
  const [connectionDetails, setConnectionDetails] = React.useState<ConnectionDetails | undefined>(
    undefined,
  );

  const handlePreJoinSubmit = React.useCallback(async (values: LocalUserChoices) => {
    setPreJoinChoices(values);
    const url = new URL(CONN_DETAILS_ENDPOINT, window.location.origin);
    url.searchParams.append('roomName', props.roomName);
    url.searchParams.append('participantName', values.username);
    url.searchParams.append('metadata', JSON.stringify({ sandboxId: 'allion-6ut898' }));
    if (props.region) {
      url.searchParams.append('region', props.region);
    }
    if (props.isHost) {
      url.searchParams.append('isHost', 'true');
    }
    const connectionDetailsResp = await fetch(url.toString());
    const connectionDetailsData = await connectionDetailsResp.json();
    setConnectionDetails(connectionDetailsData);
  }, []);
  const handlePreJoinError = React.useCallback((e: any) => console.error(e), []);

  return (
    <main data-lk-theme="default" style={{ height: '100%' }}>
      {connectionDetails === undefined || preJoinChoices === undefined ? (
        <div style={{ display: 'grid', placeItems: 'center', height: '100%' }}>
          <PreJoin
            defaults={preJoinDefaults}
            onSubmit={handlePreJoinSubmit}
            onError={handlePreJoinError}
          />
        </div>
      ) : (
        <VideoConferenceComponent
          connectionDetails={connectionDetails}
          userChoices={preJoinChoices}
          options={{
            codec: props.codec,
            hq: props.hq,
            singlePeerConnection: props.singlePeerConnection,
          }}
          isHost={props.isHost}
        />
      )}
    </main>
  );
}

function VideoConferenceComponent(props: {
  userChoices: LocalUserChoices;
  connectionDetails: ConnectionDetails;
  options: {
    hq: boolean;
    codec: VideoCodec;
    singlePeerConnection: boolean;
  };
  isHost?: boolean;
}) {
  const keyProvider = new ExternalE2EEKeyProvider();
  const { worker, e2eePassphrase } = useSetupE2EE();
  const e2eeEnabled = !!(e2eePassphrase && worker);

  const [e2eeSetupComplete, setE2eeSetupComplete] = React.useState(false);

  const roomOptions = React.useMemo((): RoomOptions => {
    let videoCodec: VideoCodec | undefined = props.options.codec ? props.options.codec : 'vp9';
    if (e2eeEnabled && (videoCodec === 'av1' || videoCodec === 'vp9')) {
      videoCodec = undefined;
    }
    const videoCaptureDefaults: VideoCaptureOptions = {
      deviceId: props.userChoices.videoDeviceId ?? undefined,
      resolution: props.options.hq ? VideoPresets.h2160 : VideoPresets.h720,
    };
    const publishDefaults: TrackPublishDefaults = {
      dtx: false,
      videoSimulcastLayers: props.options.hq
        ? [VideoPresets.h1080, VideoPresets.h720]
        : [VideoPresets.h540, VideoPresets.h216],
      red: !e2eeEnabled,
      videoCodec,
    };
    return {
      videoCaptureDefaults: videoCaptureDefaults,
      publishDefaults: publishDefaults,
      audioCaptureDefaults: {
        deviceId: props.userChoices.audioDeviceId ?? undefined,
      },
      adaptiveStream: true,
      dynacast: true,
      e2ee: keyProvider && worker && e2eeEnabled ? { keyProvider, worker } : undefined,
      singlePeerConnection: props.options.singlePeerConnection,
    };
  }, [props.userChoices, props.options.hq, props.options.codec]);

  const room = React.useMemo(() => new Room(roomOptions), []);

  React.useEffect(() => {
    if (e2eeEnabled) {
      keyProvider
        .setKey(decodePassphrase(e2eePassphrase))
        .then(() => {
          room.setE2EEEnabled(true).catch((e) => {
            if (e instanceof DeviceUnsupportedError) {
              alert(
                `You're trying to join an encrypted meeting, but your browser does not support it. Please update it to the latest version and try again.`,
              );
              console.error(e);
            } else {
              throw e;
            }
          });
        })
        .then(() => setE2eeSetupComplete(true));
    } else {
      setE2eeSetupComplete(true);
    }
  }, [e2eeEnabled, room, e2eePassphrase]);

  const connectOptions = React.useMemo((): RoomConnectOptions => {
    return {
      autoSubscribe: true,
    };
  }, []);

  React.useEffect(() => {
    room.on(RoomEvent.Disconnected, handleOnLeave);
    room.on(RoomEvent.EncryptionError, handleEncryptionError);
    room.on(RoomEvent.MediaDevicesError, handleError);

    if (e2eeSetupComplete) {
      room
        .connect(
          props.connectionDetails.serverUrl,
          props.connectionDetails.participantToken,
          connectOptions,
        )
        .catch((error) => {
          handleError(error);
        });
      if (props.userChoices.videoEnabled) {
        room.localParticipant.setCameraEnabled(true).catch((error) => {
          handleError(error);
        });
      }
      if (props.userChoices.audioEnabled) {
        room.localParticipant.setMicrophoneEnabled(true).catch((error) => {
          handleError(error);
        });
      }
    }
    return () => {
      room.off(RoomEvent.Disconnected, handleOnLeave);
      room.off(RoomEvent.EncryptionError, handleEncryptionError);
      room.off(RoomEvent.MediaDevicesError, handleError);
    };
  }, [e2eeSetupComplete, room, props.connectionDetails, props.userChoices]);

  const lowPowerMode = useLowCPUOptimizer(room);

  const router = useRouter();
  const handleOnLeave = React.useCallback(() => router.push('/'), [router]);
  const handleError = React.useCallback((error: Error) => {
    console.error(error);
    alert(`Encountered an unexpected error, check the console logs for details: ${error.message}`);
  }, []);
  const handleEncryptionError = React.useCallback((error: Error) => {
    console.error(error);
    alert(
      `Encountered an unexpected encryption error, check the console logs for details: ${error.message}`,
    );
  }, []);

  React.useEffect(() => {
    if (lowPowerMode) {
      console.warn('Low power mode enabled');
    }
  }, [lowPowerMode]);

  const [selectedAgent, setSelectedAgent] = React.useState('my-agent');
  const [isInviting, setIsInviting] = React.useState(false);
  
  const handleInviteAgent = React.useCallback(async () => {
    setIsInviting(true);
    try {
      const response = await fetch('/api/invite-agent', {
        method: 'POST',
        body: JSON.stringify({ 
          roomName: props.connectionDetails.roomName,
          agentName: selectedAgent 
        }),
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to invite agent');
      }
    } catch (error) {
      console.error(error);
      alert(`Failed to invite agent: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsInviting(false);
    }
  }, [props.connectionDetails.roomName, selectedAgent]);

  const handleMuteAgent = React.useCallback(async () => {
    const agentParticipant = Array.from(room.remoteParticipants.values()).find(p => 
      p.kind === 'agent' || 
      p.identity.toLowerCase().includes('agent') || 
      (p.name && p.name.toLowerCase().includes('agent'))
    );
    if (!agentParticipant) {
      alert('Agent is not currently in the room.');
      return;
    }
    
    const micTrack = agentParticipant.getTrackPublication(Track.Source.Microphone);
    if (!micTrack) {
      alert('Agent does not have an active microphone.');
      return;
    }

    try {
      const response = await fetch('/api/mute-participant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          roomName: props.connectionDetails.roomName,
          identity: agentParticipant.identity,
          trackSid: micTrack.trackSid,
          muted: true
        })
      });
      
      if (!response.ok) {
        throw new Error('Server returned ' + response.status);
      }
      alert('Agent muted successfully.');
    } catch (error) {
      console.error('Error muting agent:', error);
      alert('Failed to mute agent.');
    }
  }, [room, selectedAgent, props.connectionDetails.roomName]);

  return (
    <div className="lk-room-container" style={{ position: 'relative' }}>
      <RoomContext.Provider value={room}>
        <div style={{ position: 'fixed', top: '1.5rem', left: '1.5rem', zIndex: 1000 }}>
          <button 
            className="flowgentic-btn"
            style={{ background: 'rgba(0,0,0,0.5)', padding: '0.5rem 1.2rem', borderRadius: '2rem', border: '1px solid var(--border)', backdropFilter: 'blur(10px)', color: 'white', fontSize: '0.9rem', cursor: 'pointer' }}
            onClick={() => {
              navigator.clipboard.writeText(window.location.href);
              alert('Meeting link copied!');
            }}
          >
            Meeting Link
          </button>
        </div>

        <div style={{ position: 'fixed', top: '1.5rem', left: '50%', transform: 'translateX(-50%)', zIndex: 1000, display: 'flex', gap: '0.5rem', background: 'rgba(0,0,0,0.5)', padding: '0.3rem 0.5rem', borderRadius: '2rem', border: '1px solid var(--border)', backdropFilter: 'blur(10px)' }}>
          <select 
            value={selectedAgent} 
            onChange={(e) => setSelectedAgent(e.target.value)}
            style={{ background: 'transparent', color: 'white', border: 'none', padding: '0.2rem 0.5rem', cursor: 'pointer', outline: 'none' }}
          >
            <option value="my-agent">My Agent (Voice)</option>
            <option value="Samantha">Samantha (Meeting Assistant)</option>
            <option value="Jarvis">Jarvis (Tech Expert)</option>
            <option value="Nova">Nova (Creative Lead)</option>
          </select>
          <button 
            className="flowgentic-btn" 
            onClick={handleInviteAgent}
            disabled={isInviting}
            style={{ padding: '0.4rem 1.2rem', fontSize: '0.85rem' }}
          >
            {isInviting ? 'Summoning...' : 'Summon'}
          </button>
          {props.isHost && (
            <button 
              className="flowgentic-btn" 
              onClick={handleMuteAgent}
              style={{ padding: '0.4rem 1.2rem', fontSize: '0.85rem', background: 'rgba(220, 53, 69, 0.8)' }}
            >
              Mute Agent
            </button>
          )}
        </div>
        <KeyboardShortcuts />
        <VideoConference
          chatMessageFormatter={formatChatMessageLinks}
          SettingsComponent={SHOW_SETTINGS_MENU ? SettingsMenu : undefined}
        />
        <DebugMode />
        <RecordingIndicator />
      </RoomContext.Provider>
    </div>
  );
}
