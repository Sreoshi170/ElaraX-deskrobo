import type { Metadata } from 'next';
import { DM_Mono, DM_Sans } from 'next/font/google';
import './globals.css';

const dmSans = DM_Sans({
  variable: '--font-elara-sans',
  subsets: ['latin'],
});

const dmMono = DM_Mono({
  variable: '--font-elara-mono',
  weight: ['400', '500'],
  subsets: ['latin'],
});

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? 'https://aetherbot-command-center.sreoshibhowmik28.chatgpt.site',
  ),
  title: 'ElaraX — Executive command center',
  description: 'A multilingual AI command center for email, calendar, briefings, and your desk robot.',
  openGraph: {
    title: 'ElaraX — Executive command center',
    description: 'A multilingual AI command center for email, calendar, briefings, and your desk robot.',
    type: 'website',
    images: [{ url: '/og.png', width: 1200, height: 630, alt: 'ElaraX executive command center' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'ElaraX — Executive command center',
    description: 'A multilingual AI command center for email, calendar, briefings, and your desk robot.',
    images: ['/og.png'],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
  <body className={`${dmSans.variable} ${dmMono.variable}`}>{children}</body>
    </html>
  );
}
