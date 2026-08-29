"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { Plus } from "lucide-react";
import { useAppState } from "@/context/AppStateContext";
import { AnalyzeOverlay } from "@/components/ui/AnalyzeOverlay";
import { LogoMark } from "@/components/ui/LogoMark";

const navItems = [
  { label: "Library", href: "/library" },
  { label: "Opportunities", href: "/scene/rooftop-reflection" },
  { label: "Sponsor Finder", href: "/sponsor-search" },
  { label: "Marketplace", href: "/marketplace" },
  { label: "Deals", href: "/deals/aurelius-systems" },
  { label: "Agents", href: "/agents" },
  { label: "Analytics", href: "/analytics" },
];

function isNavActive(pathname: string, href: string): boolean {
  if (href === "/library") {
    return pathname === "/" || pathname === "/library";
  }
  if (href.startsWith("/scene/")) {
    return pathname.startsWith("/scene/") || pathname.startsWith("/opportunities/");
  }
  if (href.startsWith("/deals/")) {
    return pathname.startsWith("/deals/");
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { startAnalyze, analyzing, progress, analyzeWithFile, registerFileInput } = useAppState();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    registerFileInput(fileInputRef.current);
  }, [registerFileInput]);

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden bg-canvas font-ui text-ink">
      <header className="relative z-20 flex h-[72px] flex-none items-center justify-between gap-5 border-b border-line bg-canvas px-[clamp(20px,3vw,48px)]">
        <div className="flex min-w-0 items-center gap-[clamp(28px,4vw,64px)]">
          <Link href="/library" className="flex cursor-pointer items-center gap-3 text-ink hover:text-ink">
            <LogoMark />
            <span className="flex items-baseline gap-1 text-[15px] tracking-[-0.02em] text-ink">
              <span>CINE</span><i className="not-italic text-gold">/</i><strong>YIELD</strong>
            </span>
            <span className="hidden border-l border-line2 pl-3 font-mono text-[8px] font-bold uppercase tracking-[0.12em] text-ink3 xl:block">Sponsor intelligence</span>
          </Link>

          <nav className="hidden h-[72px] items-center gap-[clamp(18px,2vw,32px)] md:flex" aria-label="Main">
            {navItems.map((item) => {
              const active = isNavActive(pathname, item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`relative inline-flex h-[72px] cursor-pointer items-center border-none bg-none px-0 text-[12px] font-semibold tracking-[0.01em] transition-colors hover:text-ink ${
                    active
                      ? "text-ink after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[2px] after:bg-gold"
                      : "text-ink2"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex flex-none items-center gap-3">
          <div className="hidden items-center gap-1.5 lg:flex">
            <span className="h-[5px] w-[5px] animate-cypulse-slow rounded-full bg-green" />
            <span className="font-mono text-[11px] text-ink3">live</span>
          </div>

          <button
            type="button"
            onClick={startAnalyze}
            className="flex h-[38px] cursor-pointer items-center gap-4 bg-gold px-4 text-[10px] font-bold uppercase tracking-[0.06em] text-[#111214] transition-colors hover:bg-transparent hover:text-gold hover:outline hover:outline-1 hover:outline-gold"
          >
            <Plus size={15} strokeWidth={2.2} aria-hidden />
            Analyze a Cut
          </button>

          <details className="relative md:hidden">
            <summary className="cursor-pointer list-none border border-line2 px-3 py-2 text-[10px] font-bold uppercase tracking-[0.08em] text-ink">Menu</summary>
            <nav className="absolute right-0 top-[47px] flex w-[250px] flex-col border border-line2 border-t-2 border-t-gold bg-canvas p-4" aria-label="Mobile main navigation">
              {navItems.map((item) => <Link key={item.href} href={item.href} className="border-b border-line py-3 text-[13px] text-ink2 last:border-b-0 hover:text-gold">{item.label}</Link>)}
            </nav>
          </details>
        </div>
      </header>

      <div id="cy-content" className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-[1440px] px-[clamp(20px,3vw,48px)] pb-[88px] pt-8">
          {children}
        </div>
      </div>

      {analyzing && <AnalyzeOverlay progress={progress} />}

      <input
        ref={fileInputRef}
        type="file"
        accept="video/*,.mp4,.mov,.avi,.m4v"
        className="hidden"
        aria-hidden
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) analyzeWithFile(file);
          e.target.value = "";
        }}
      />
    </div>
  );
}
