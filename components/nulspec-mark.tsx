type NulspecMarkProps = {
  className?: string;
};

export function NulspecMark({ className }: NulspecMarkProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      focusable="false"
      viewBox="0 0 64 64"
      xmlns="http://www.w3.org/2000/svg"
    >
      <g fill="currentColor">
        <rect height="8" width="46" x="9" y="12" />
        <rect height="8" width="17" x="9" y="28" />
        <rect height="8" width="17" x="38" y="28" />
        <rect height="8" width="46" x="9" y="44" />
      </g>
    </svg>
  );
}
