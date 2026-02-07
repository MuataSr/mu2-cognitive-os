import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ModeProvider } from "@/components/providers/mode-provider";
import { FocusModeToggle } from "@/components/focus-mode-toggle";
import { KeyboardShortcutsButton } from "@/components/keyboard-shortcuts";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Mu2 Cognitive OS",
  description: "Adaptive Learning Platform with Focus Mode",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <ModeProvider>
          <a href="#main-content" className="skip-link">
            Skip to main content
          </a>
          <FocusModeToggle />
          <main id="main-content">{children}</main>
          <KeyboardShortcutsButton />
        </ModeProvider>
      </body>
    </html>
  );
}
