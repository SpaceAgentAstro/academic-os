import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["300", "400"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AcademicOS",
  description: "Educational intelligence platform for Pearson Edexcel IAL revision",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-theme="light" suppressHydrationWarning>
      <head>
        {/* Apply the theme before first paint to avoid a light→dark flash for
            dark-mode users (RT-015). */}
        <script
          dangerouslySetInnerHTML={{
            __html:
              "try{var d=window.matchMedia('(prefers-color-scheme: dark)').matches;" +
              "document.documentElement.setAttribute('data-theme', d?'dark':'light');}catch(e){}",
          }}
        />
        {/* Pinned to an exact version (no floating @latest) and loaded with an
            explicit cross-origin to reduce supply-chain exposure (AOS-009). */}
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.44.0/dist/tabler-icons.min.css"
          crossOrigin="anonymous"
        />
      </head>
      <body className={`${inter.variable} ${jetbrainsMono.variable}`}>
        {children}
      </body>
    </html>
  );
}
