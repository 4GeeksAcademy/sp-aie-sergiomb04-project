import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Backoffice",
  description: "Panel interno de operaciones y gestion.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="es"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-slate-100 text-slate-900">
        <div className="flex min-h-full flex-col">
          <header className="border-b border-slate-200 bg-white/95 px-6 py-4 backdrop-blur lg:px-10">
            <div className="mx-auto flex w-full max-w-7xl items-center justify-between">
              <div>
                <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-500">
                  TrackFlow
                </p>
                <p className="text-lg font-semibold text-slate-950">Backoffice</p>
              </div>
            </div>
          </header>

          <div className="mx-auto flex w-full max-w-7xl flex-1">{children}</div>
        </div>
      </body>
    </html>
  );
}
