"use client";

import {
  Children,
  type KeyboardEvent,
  type ReactNode,
  useEffect,
  useRef,
  useState,
} from "react";

const tabs = [
  { id: "comparison", label: "Comparison", hashes: ["comparison"] },
  { id: "execution", label: "Execution", hashes: ["execution", "attempts"] },
  { id: "provenance", label: "Provenance", hashes: ["provenance"] },
  { id: "evidence", label: "Evidence", hashes: ["evidence"] },
  { id: "limitations", label: "Limits", hashes: ["limitations"] },
] as const;

type TabId = (typeof tabs)[number]["id"];

function tabForHash(hash: string) {
  return tabs.find((tab) => tab.hashes.some((value) => value === hash));
}

export function ArmEvidenceTabs({ children }: { children: ReactNode }) {
  const panels = Children.toArray(children);
  const [activeTab, setActiveTab] = useState<TabId>("comparison");
  const rootRef = useRef<HTMLDivElement>(null);
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  useEffect(() => {
    function syncFromHash() {
      const hash = decodeURIComponent(window.location.hash.slice(1));
      const tab = tabForHash(hash);
      if (!tab) return;

      setActiveTab(tab.id);
      window.requestAnimationFrame(() => {
        if (hash === "attempts") {
          document.getElementById("attempts")?.scrollIntoView({ block: "start" });
          return;
        }
        rootRef.current?.scrollIntoView({ block: "start" });
      });
    }

    syncFromHash();
    window.addEventListener("hashchange", syncFromHash);
    return () => window.removeEventListener("hashchange", syncFromHash);
  }, []);

  function selectTab(id: TabId, focus = false) {
    setActiveTab(id);
    window.history.replaceState(
      window.history.state,
      "",
      window.location.pathname + window.location.search + "#" + id,
    );
    if (focus) {
      const index = tabs.findIndex((tab) => tab.id === id);
      tabRefs.current[index]?.focus();
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let nextIndex: number | undefined;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % tabs.length;
    if (event.key === "ArrowLeft") {
      nextIndex = (index - 1 + tabs.length) % tabs.length;
    }
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = tabs.length - 1;
    if (nextIndex === undefined) return;

    event.preventDefault();
    selectTab(tabs[nextIndex].id, true);
  }

  return (
    <div className="arm-tabs" ref={rootRef}>
      <div className="arm-tabs__sticky">
        <div className="shell arm-tabs__list" role="tablist" aria-label="Arm evidence">
          {tabs.map((tab, index) => (
            <button
              aria-controls={"arm-panel-" + tab.id}
              aria-selected={activeTab === tab.id}
              className={activeTab === tab.id ? "is-active" : undefined}
              id={"arm-tab-" + tab.id}
              key={tab.id}
              onClick={() => selectTab(tab.id)}
              onKeyDown={(event) => handleKeyDown(event, index)}
              ref={(node) => {
                tabRefs.current[index] = node;
              }}
              role="tab"
              tabIndex={activeTab === tab.id ? 0 : -1}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>
      <div className="arm-tabs__panels">
        {tabs.map((tab, index) => (
          <div
            aria-labelledby={"arm-tab-" + tab.id}
            hidden={activeTab !== tab.id}
            id={"arm-panel-" + tab.id}
            key={tab.id}
            role="tabpanel"
            tabIndex={0}
          >
            {panels[index]}
          </div>
        ))}
      </div>
    </div>
  );
}
