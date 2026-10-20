"use client";
import * as React from "react";

/** Keep list DOM/search/scroll while showing one focused mobile detail panel. */
export function useListDetail() {
  const [detailOpen, setDetailOpen] = React.useState(false);
  const listRef = React.useRef<HTMLDivElement>(null);
  const position = React.useRef({ y: 0, listY: 0, trigger: null as HTMLElement | null });
  const returning = React.useRef(false);
  const open = (trigger?: HTMLElement): void => {
    if (!detailOpen) position.current = { y: window.scrollY,
      listY: listRef.current?.querySelector<HTMLElement>("[data-list-scroll]")?.scrollTop || 0,
      trigger: trigger || null };
    setDetailOpen(true);
  };
  React.useLayoutEffect(() => {
    if (detailOpen && window.matchMedia("(max-width: 1023px)").matches) window.scrollTo(0, 0);
    if (!detailOpen && returning.current) {
      returning.current = false;
      const scroll = listRef.current?.querySelector<HTMLElement>("[data-list-scroll]");
      if (scroll) scroll.scrollTop = position.current.listY;
      if (position.current.trigger?.isConnected) position.current.trigger.focus({ preventScroll: true });
      window.scrollTo(0, position.current.y);
    }
  }, [detailOpen]);
  return { detailOpen, listRef, open, back: () => { returning.current = true; setDetailOpen(false); } };
}
