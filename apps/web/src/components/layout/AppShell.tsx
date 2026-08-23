"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { Plus, Search } from "lucide-react";
import { useAppState } from "@/context/AppStateContext";
import { AnalyzeOverlay } from "@/components/ui/AnalyzeOverlay";
import { LogoMark } from "@/components/ui/LogoMark";

const navItems = [
  { label: "Library", href: "/library" },
  { label: "Opportunities", href: "/scene/rooftop-reflection" },
  { label: "Marketplace", href: "/marketplace" },
  { label: "Deals", href: "/deals/aurelius-systems" },
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
      <div className="flex h-10 flex-none items-center justify-center gap-2 bg-gradient-to-r from-[#2563eb] via-[#3b82f6] to-[#2563eb] text-[13px] font-medium tracking-[0.01em] text-[#eaf2ff]">
        <span className="opacity-85">✨</span>
        Introducing CineYield — turn every scene into sellable inventory
        <span className="opacity-80">›</span>
      </div>

      <header className="relative z-20 flex h-[60px] flex-none items-center justify-between gap-5 border-b border-line bg-[rgba(9,9,11,0.82)] px-7 backdrop-blur-[10px]">
        <div className="flex min-w-0 items-center gap-8">
          <Link href="/library" className="flex cursor-pointer items-center gap-2">
            <LogoMark />
            <span className="text-[18px] font-bold tracking-[-0.02em] text-ink">
              CineYield
            </span>
          </Link>

          <nav className="flex h-[60px] items-center gap-[22px]" aria-label="Main">
            {navItems.map((item) => {
              const active = isNavActive(pathname, item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`inline-flex h-[60px] cursor-pointer items-center border-none bg-none px-0 text-[14px] font-medium tracking-[-0.01em] transition-colors hover:text-ink ${
                    active
                      ? "text-ink shadow-[inset_0_-2px_0_var(--color-gold)]"
                      : "text-ink2"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex flex-none items-center gap-3.5">
          <div
            data-search
            className="hidden h-[34px] w-[200px] items-center gap-2 rounded-lg border border-line2 bg-panel px-2.5 pl-3 text-[13px] text-ink3"
          >
            <Search size={14} strokeWidth={1.8} aria-hidden />
            <span className="flex-1 overflow-hidden whitespace-nowrap">
              Search catalog…
            </span>
            <span className="rounded border border-line2 px-[5px] py-px font-mono text-[11px] font-medium">
              ⌘K
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="h-[5px] w-[5px] animate-cypulse-slow rounded-full bg-green" />
            <span className="font-mono text-[11px] text-ink3">live</span>
          </div>

          <button
            type="button"
            onClick={startAnalyze}
            className="flex h-9 cursor-pointer items-center gap-1.5 rounded-lg bg-gold px-4 text-[13px] font-semibold text-white transition-[filter] hover:brightness-110"
          >
            <Plus size={15} strokeWidth={2.2} aria-hidden />
            Analyze a Cut
          </button>
        </div>
      </header>

      <div id="cy-content" className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-[1200px] px-10 pb-[88px] pt-7">
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
