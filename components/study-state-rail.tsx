const states = [
  "SPEC-FROZEN",
  "RUNNING",
  "RUNS-COMPLETE",
  "ANALYSIS-OPEN",
  "REPORTED",
] as const;

export function StudyStateRail({ current }: { current: (typeof states)[number] }) {
  const currentIndex = states.indexOf(current);

  return (
    <ol className="state-rail" aria-label={`Study state: ${current}`}>
      {states.map((state, index) => {
        const stateClass =
          index < currentIndex ? "is-past" : index === currentIndex ? "is-current" : "";
        return (
          <li className={stateClass} key={state}>
            <span className="state-rail__marker" aria-hidden="true" />
            <span>{state}</span>
          </li>
        );
      })}
    </ol>
  );
}
