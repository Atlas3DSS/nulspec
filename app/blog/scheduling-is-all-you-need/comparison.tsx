"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import styles from "./page.module.css";

const comparisonLimit = 3;

export type ComparisonItem = {
  id: string;
  title: string;
  context: string;
  runtime: string;
  video: string;
};

type ComparisonContextValue = {
  canAdd: boolean;
  isSelected: (id: string) => boolean;
  toggle: (item: ComparisonItem) => void;
};

const ComparisonContext = createContext<ComparisonContextValue | null>(null);

function useComparison() {
  const value = useContext(ComparisonContext);
  if (!value) throw new Error("Compare controls must be inside ComparisonProvider");
  return value;
}

export function ComparisonProvider({ children }: { children: ReactNode }) {
  const [selected, setSelected] = useState<ComparisonItem[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const closeButton = useRef<HTMLButtonElement>(null);

  const toggle = useCallback(
    (item: ComparisonItem) => {
      const alreadySelected = selected.some((candidate) => candidate.id === item.id);
      const next = alreadySelected
        ? selected.filter((candidate) => candidate.id !== item.id)
        : selected.length < comparisonLimit
          ? [...selected, item]
          : selected;

      setSelected(next);
      if (!alreadySelected && next.length >= 2) setIsOpen(true);
      if (next.length < 2) setIsOpen(false);
    },
    [selected],
  );

  const clear = useCallback(() => {
    setSelected([]);
    setIsOpen(false);
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButton.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [isOpen]);

  const value = useMemo<ComparisonContextValue>(
    () => ({
      canAdd: selected.length < comparisonLimit,
      isSelected: (id) => selected.some((item) => item.id === id),
      toggle,
    }),
    [selected, toggle],
  );

  return (
    <ComparisonContext.Provider value={value}>
      {children}

      {selected.length === 1 ? (
        <div className={styles.compareHint} role="status">
          1 selected · choose one more
        </div>
      ) : null}

      {selected.length >= 2 && !isOpen ? (
        <button className={styles.compareLauncher} onClick={() => setIsOpen(true)} type="button">
          Compare {selected.length} / {comparisonLimit}
        </button>
      ) : null}

      {selected.length >= 2 && isOpen ? (
        <>
          <button
            aria-label="Close comparison"
            className={styles.compareScrim}
            onClick={() => setIsOpen(false)}
            type="button"
          />
          <aside
            aria-labelledby="compare-window-heading"
            aria-modal="true"
            className={styles.compareWindow}
            role="dialog"
          >
            <header className={styles.compareWindowHeader}>
              <div>
                <p>{selected.length} of {comparisonLimit} selected</p>
                <h2 id="compare-window-heading">Compare variants</h2>
              </div>
              <button ref={closeButton} onClick={() => setIsOpen(false)} type="button">
                {selected.length < comparisonLimit ? "Pick another" : "Close"}
              </button>
            </header>

            <div
              className={`${styles.compareGrid} ${
                selected.length === 2 ? styles.compareGridTwo : styles.compareGridThree
              }`}
            >
              {selected.map((item) => (
                <article className={styles.compareItem} key={item.id}>
                  <video controls playsInline preload="metadata" src={item.video} />
                  <div>
                    <p>{item.context}</p>
                    <h3>{item.title}</h3>
                    <span>{item.runtime}</span>
                    <button onClick={() => toggle(item)} type="button">
                      Remove
                    </button>
                  </div>
                </article>
              ))}
            </div>

            <footer className={styles.compareWindowFooter}>
              <p>Selections stay checked while you change NFE tabs and gallery pages.</p>
              <button onClick={clear} type="button">Clear all</button>
            </footer>
          </aside>
        </>
      ) : null}
    </ComparisonContext.Provider>
  );
}

export function CompareToggle({ item }: { item: ComparisonItem }) {
  const { canAdd, isSelected, toggle } = useComparison();
  const checked = isSelected(item.id);
  const disabled = !checked && !canAdd;

  return (
    <label
      className={`${styles.compareToggle} ${checked ? styles.compareToggleSelected : ""}`}
      data-disabled={disabled || undefined}
    >
      <input
        aria-label={`Compare ${item.title}`}
        checked={checked}
        disabled={disabled}
        onChange={() => toggle(item)}
        type="checkbox"
      />
      <span>{checked ? "Selected for comparison" : "Compare"}</span>
    </label>
  );
}
