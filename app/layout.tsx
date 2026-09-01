import '../styles/globals.css';
import '@livekit/components-styles';
import '@livekit/components-styles/prefabs';
import type { Metadata, Viewport } from 'next';
import { Toaster } from 'react-hot-toast';

export const metadata: Metadata = {
  title: {
    default: 'Flowgentic Meet | Next-Gen AI Conferencing',
    template: '%s | Flowgentic Meet',
  },
  description:
    'The next generation of AI-native video conferencing. Collaborate seamlessly with intelligent voice agents on the Flowgentic Meet platform.',
  twitter: {
    creator: '@flowgentic',
    site: '@flowgentic',
    card: 'summary_large_image',
  },
  openGraph: {
    url: 'https://flowgentic.ai',
    images: [
      {
        url: '/images/flowgentic-og.png',
        width: 2000,
        height: 1000,
        type: 'image/png',
      },
    ],
    siteName: 'Flowgentic Meet',
  },
  icons: {
    icon: [
      { url: '/flowgentic-meet-icon.svg', type: 'image/svg+xml' },
      { url: '/favicon.ico' },
    ],
    shortcut: '/flowgentic-meet-icon.svg',
    apple: '/flowgentic-meet-icon.svg',
  },
};

export const viewport: Viewport = {
  themeColor: '#09090b',
};

import { ClerkProvider } from '@clerk/nextjs';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body data-lk-theme="default">
          <div className="bg-blob-1"></div>
          <div className="bg-blob-2"></div>
          <Toaster />
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
