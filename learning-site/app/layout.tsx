import type { Metadata } from 'next';
import './globals.css';

const basePath = '/learn';
const origin = new URL(process.env.LEARNING_SITE_ORIGIN || 'http://127.0.0.1:8080');
if (!['http:', 'https:'].includes(origin.protocol) || origin.username || origin.password
    || origin.pathname !== '/' || origin.search || origin.hash) {
  throw new Error('LEARNING_SITE_ORIGIN must be an HTTP(S) origin without credentials, path or query.');
}

export const metadata: Metadata = {
  metadataBase: origin,
  icons: { icon: `${basePath}/favicon.svg` },
  title: '市场情报系统源码导读 | Market Intel Lab',
  description: '逐步理解 Crawl4AI、Browser Use、n8n、PandasAI 与 Python，并组合成市场情报自动化系统。',
  openGraph: {
    title: '市场情报系统源码导读',
    description: 'Crawl4AI · Browser Use · n8n · PandasAI · Python',
    images: [{ url: `${basePath}/market-intel-og.png`, width: 1731, height: 909 }],
    locale: 'zh_CN',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: '市场情报系统源码导读',
    description: '从开源工具到可运行系统，逐步读懂入口、模块与调用链。',
    images: [`${basePath}/market-intel-og.png`],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
