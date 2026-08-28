import type { Metadata } from "next";
import { AppStateProvider } from "@/context/AppStateContext";
import { AppShell } from "@/components/layout/AppShell";
import "./globals.css";

export const metadata: Metadata = {
  title: "CINEYIELD — Sponsor Intelligence",
  description: "Match finished scenes with qualified sponsor demand while keeping producers in control.",
  icons: { icon: "/cineyield-mark.svg", shortcut: "/cineyield-mark.svg" },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <AppStateProvider>
          <AppShell>{children}</AppShell>
        </AppStateProvider>
      </body>
    </html>
  );
}
