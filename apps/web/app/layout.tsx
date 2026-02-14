import type { Metadata } from "next";
import { Montserrat } from "next/font/google";
import { Inter } from "next/font/google";
import "./globals.css";
import { ModeProvider } from "@/components/providers/mode-provider";
import { ClientBodyWrapper } from "@/components/client-body-wrapper";

// Kut Different Fonts: Montserrat (headings) and Inter (body)
const montserrat = Montserrat({
  variable: "--font-montserrat",
  subsets: ["latin"],
  weight: ["700", "800", "900"],
  display: "swap",
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["300", "400", "600"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Kut Different - Mu2 Cognitive OS",
  description: "Mu2 Cognitive OS: Guiding young men to own their greatness through local, adaptive intelligence.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${montserrat.variable} ${inter.variable} antialiased`}>
        <ModeProvider>
          <ClientBodyWrapper>{children}</ClientBodyWrapper>
        </ModeProvider>
      </body>
    </html>
  );
}
