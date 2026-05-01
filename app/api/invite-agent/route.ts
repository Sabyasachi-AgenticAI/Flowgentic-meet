import { AgentDispatchClient } from 'livekit-server-sdk';
import { NextRequest, NextResponse } from 'next/server';

const API_KEY = process.env.LIVEKIT_API_KEY;
const API_SECRET = process.env.LIVEKIT_API_SECRET;
const LIVEKIT_URL = process.env.LIVEKIT_URL;
const DEFAULT_AGENT_NAME = process.env.LIVEKIT_AGENT_NAME || 'Riley-2252';

export async function POST(request: NextRequest) {
  try {
    const { roomName, agentName } = await request.json();
    const AGENT_TO_INVITE = agentName || DEFAULT_AGENT_NAME;

    if (!LIVEKIT_URL || !API_KEY || !API_SECRET) {
      return NextResponse.json({ error: 'Missing LiveKit configuration' }, { status: 500 });
    }

    const host = LIVEKIT_URL.replace('wss://', 'https://');
    console.log(`Dispatching agent "${AGENT_TO_INVITE}" to room "${roomName}" at host "${host}"`);
    const agentService = new AgentDispatchClient(host, API_KEY, API_SECRET);
    
    const dispatch = await agentService.createDispatch(roomName, AGENT_TO_INVITE);
    console.log('Agent dispatch created successfully:', dispatch);

    return NextResponse.json({ success: true, dispatchId: dispatch.id });
  } catch (error) {
    console.error('Failed to dispatch agent:', error);
    return NextResponse.json({ error: (error as Error).message }, { status: 500 });
  }
}
