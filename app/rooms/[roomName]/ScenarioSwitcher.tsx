'use client';

import React, { useState } from 'react';
import { useRoomContext } from '@livekit/components-react';

export function ScenarioSwitcher() {
  const room = useRoomContext();
  const [activeScenario, setActiveScenario] = useState<'gtm_product' | 'tech_compliance'>('gtm_product');
  const [isDeploying, setIsDeploying] = useState(false);

  const switchScenario = async (scenario: 'gtm_product' | 'tech_compliance') => {
    if (scenario === activeScenario || isDeploying) return;
    setIsDeploying(true);
    setActiveScenario(scenario);

    try {
      const encoder = new TextEncoder();
      const payload = encoder.encode(
        JSON.stringify({
          scenario,
          timestamp: Date.now(),
        })
      );

      await room.localParticipant.publishData(payload, {
        topic: 'lk-scenario-switch',
        reliable: true,
      });

      console.log(`[ScenarioSwitcher] Published scenario switch to ${scenario}`);
    } catch (err) {
      console.error('[ScenarioSwitcher] Failed to publish scenario switch:', err);
    } finally {
      setTimeout(() => setIsDeploying(false), 1200);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: '1.2rem',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 999,
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        background: 'rgba(15, 23, 42, 0.85)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        borderRadius: '9999px',
        padding: '0.35rem 0.5rem',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.37)',
      }}
    >
      <span
        style={{
          color: '#94a3b8',
          fontSize: '0.75rem',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          paddingLeft: '0.75rem',
          paddingRight: '0.25rem',
          userSelect: 'none',
        }}
      >
        Scenario:
      </span>

      <button
        onClick={() => switchScenario('gtm_product')}
        disabled={isDeploying}
        style={{
          background:
            activeScenario === 'gtm_product'
              ? 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)'
              : 'transparent',
          color: activeScenario === 'gtm_product' ? '#ffffff' : '#cbd5e1',
          border: 'none',
          borderRadius: '9999px',
          padding: '0.4rem 0.9rem',
          fontSize: '0.8rem',
          fontWeight: 600,
          cursor: isDeploying ? 'wait' : 'pointer',
          transition: 'all 0.2s ease',
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          boxShadow: activeScenario === 'gtm_product' ? '0 0 12px rgba(59, 130, 246, 0.4)' : 'none',
        }}
      >
        <span>🚀</span> GTM & Product
      </button>

      <button
        onClick={() => switchScenario('tech_compliance')}
        disabled={isDeploying}
        style={{
          background:
            activeScenario === 'tech_compliance'
              ? 'linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)'
              : 'transparent',
          color: activeScenario === 'tech_compliance' ? '#ffffff' : '#cbd5e1',
          border: 'none',
          borderRadius: '9999px',
          padding: '0.4rem 0.9rem',
          fontSize: '0.8rem',
          fontWeight: 600,
          cursor: isDeploying ? 'wait' : 'pointer',
          transition: 'all 0.2s ease',
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          boxShadow:
            activeScenario === 'tech_compliance' ? '0 0 12px rgba(139, 92, 246, 0.4)' : 'none',
        }}
      >
        <span>🛡️</span> Tech & Compliance
      </button>
    </div>
  );
}
