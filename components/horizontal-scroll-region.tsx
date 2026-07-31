"use client";

import { type ChangeEvent, type ReactNode, useEffect, useRef, useState } from "react";

export function HorizontalScrollRegion({
  children,
  label,
}: {
  children: ReactNode;
  label: string;
}) {
  const contentRef = useRef<HTMLDivElement>(null);
  const [maximumScroll, setMaximumScroll] = useState(0);
  const [scrollPosition, setScrollPosition] = useState(0);

  useEffect(() => {
    const observedContent = contentRef.current;
    if (!observedContent) return;

    function measure() {
      const content = contentRef.current;
      if (!content) return;
      const maximum = Math.max(0, content.scrollWidth - content.clientWidth);
      setMaximumScroll(maximum);
      setScrollPosition(Math.min(content.scrollLeft, maximum));
    }

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(observedContent);
    if (observedContent.firstElementChild) {
      observer.observe(observedContent.firstElementChild);
    }
    window.addEventListener("resize", measure);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, []);

  function setHorizontalPosition(event: ChangeEvent<HTMLInputElement>) {
    const content = contentRef.current;
    if (!content) return;
    const nextPosition = Number(event.currentTarget.value);
    content.scrollLeft = nextPosition;
    setScrollPosition(nextPosition);
  }

  function moveByViewport(direction: -1 | 1) {
    const content = contentRef.current;
    if (!content) return;
    const nextPosition = Math.max(
      0,
      Math.min(
        maximumScroll,
        content.scrollLeft + direction * content.clientWidth * 0.8,
      ),
    );
    content.scrollLeft = nextPosition;
    setScrollPosition(nextPosition);
  }

  return (
    <div className="horizontal-scroll-region">
      <div
        className="horizontal-scroll-region__controls"
        hidden={maximumScroll <= 1}
      >
        <button
          aria-label={`Scroll ${label} left`}
          disabled={scrollPosition <= 1}
          onClick={() => moveByViewport(-1)}
          type="button"
        >
          ←
        </button>
        <input
          aria-label={`Horizontal position for ${label}`}
          max={maximumScroll}
          min={0}
          onChange={setHorizontalPosition}
          step={1}
          type="range"
          value={scrollPosition}
        />
        <button
          aria-label={`Scroll ${label} right`}
          disabled={scrollPosition >= maximumScroll - 1}
          onClick={() => moveByViewport(1)}
          type="button"
        >
          →
        </button>
      </div>
      <div
        aria-label={label}
        className="table-scroll"
        onScroll={(event) => setScrollPosition(event.currentTarget.scrollLeft)}
        ref={contentRef}
        role="region"
        tabIndex={0}
      >
        {children}
      </div>
    </div>
  );
}
