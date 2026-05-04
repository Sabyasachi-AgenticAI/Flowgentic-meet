import { RoomServiceClient } from 'livekit-server-sdk';
import { NextRequest, NextResponse } from 'next/server';

const API_KEY = process.env.LIVEKIT_API_KEY;
const API_SECRET = process.env.LIVEKIT_API_SECRET;
const LIVEKIT_URL = process.env.LIVEKIT_URL;

export async function POST(request: NextRequest) {
  try {
    const { roomName, identity, trackSid, muted } = await request.json();

    if (!LIVEKIT_URL || !API_KEY || !API_SECRET) {
      return NextResponse.json({ error: 'Missing LiveKit configuration' }, { status: 500 });
    }

    const host = LIVEKIT_URL.replace('wss://', 'https://');
    const roomService = new RoomServiceClient(host, API_KEY, API_SECRET);
    
    await roomService.mutePublishedTrack(roomName, identity, trackSid, muted);
    
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Failed to mute participant:', error);
    return NextResponse.json({ error: (error as Error).message }, { status: 500 });
  }
}
