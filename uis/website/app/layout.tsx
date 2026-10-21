import type { Metadata } from "next";
import { Geist } from "next/font/google";

import { Footer } from "../componentes/Footer";
import { Navbar } from "../componentes/Navbar";

import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "TrackFlow",
    template: "%s | TrackFlow",
  },
  description: "Soluciones inteligentes de logistica de ultima milla para e-commerce.",
};

const organizationJsonLd = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "TrackFlow",
  url: "https://trackflow.com",
  description:
    "Soluciones inteligentes de logistica de ultima milla para e-commerce.",
  email: "info@trackflow.com",
  telephone: "+1-213-555-0147",
  address: [
    {
      "@type": "PostalAddress",
      addressLocality: "Los Angeles",
      addressCountry: "US",
    },
    {
      "@type": "PostalAddress",
      addressLocality: "Zaragoza",
      addressCountry: "ES",
    },
  ],
  sameAs: [],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="es"
      className={`${geistSans.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('trackflow_theme');var d=window.matchMedia('(prefers-color-scheme: dark)').matches;if(t==='dark'||(!t&&d)){document.documentElement.classList.add('dark')}else{document.documentElement.classList.remove('dark')}}catch(e){}})()`,
          }}
        />
      </head>
      <body className="min-h-full bg-gray-100 font-sans text-gray-800 transition-colors duration-150 dark:bg-slate-950 dark:text-slate-100">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationJsonLd) }}
        />

        <div className="flex min-h-full flex-col">
          <a
            href="#main-content"
            className="sr-only rounded bg-white px-3 py-2 shadow focus:not-sr-only focus:absolute focus:top-4 focus:left-4"
          >
            Saltar al contenido principal
          </a>

          <Navbar />

          <div className="flex-1">{children}</div>

          <Footer />
        </div>
      </body>
    </html>
  );
}
