export type NulspecMarkId =
  | "A1"
  | "A2"
  | "A3"
  | "A4"
  | "B1"
  | "B2"
  | "B3"
  | "B4"
  | "C1"
  | "C2"
  | "C3"
  | "C4"
  | "D1"
  | "D2"
  | "D3"
  | "D4"
  | "E1"
  | "E2"
  | "E3"
  | "E4";

type NulspecMarkProps = {
  id: NulspecMarkId;
  className?: string;
};

function markGeometry(id: NulspecMarkId) {
  switch (id) {
    case "A1":
      return (
        <g
          fill="none"
          stroke="currentColor"
          strokeLinecap="square"
          strokeWidth="8"
        >
          <path d="M42 11A23 23 0 0 0 11 42" />
          <path d="M22 53A23 23 0 0 0 53 22" />
        </g>
      );
    case "A2":
      return (
        <g
          fill="none"
          stroke="currentColor"
          strokeLinecap="square"
          strokeWidth="7"
        >
          <circle
            cx="32"
            cy="32"
            r="21"
            strokeDasharray="58 8 58 8"
            transform="rotate(-45 32 32)"
          />
          <path d="M10 54 54 10" />
        </g>
      );
    case "A3":
      return (
        <g
          fill="none"
          stroke="currentColor"
          strokeLinecap="square"
          strokeLinejoin="miter"
          strokeWidth="6"
        >
          <circle
            cx="32"
            cy="32"
            r="23"
            strokeDasharray="62 10 62 10"
            transform="rotate(45 32 32)"
          />
          <path d="M19 47V17l26 30V17" />
        </g>
      );
    case "A4":
      return (
        <g
          fill="none"
          stroke="currentColor"
          strokeLinecap="square"
          strokeLinejoin="miter"
          strokeWidth="7"
        >
          <rect height="42" width="42" x="11" y="11" />
          <path d="M19 19 45 45" />
        </g>
      );
    case "B1":
      return (
        <g fill="currentColor">
          <path d="M10 8h7v10h-7zm0 18h7v30h-7z" />
          <path d="M22 8h7v18h-7zm0 26h7v22h-7z" />
          <path d="M34 8h7v26h-7zm0 34h7v14h-7z" />
          <path d="M46 8h7v34h-7zm0 42h7v6h-7z" />
        </g>
      );
    case "B2":
      return (
        <g fill="currentColor">
          <rect height="8" width="46" x="9" y="12" />
          <rect height="8" width="17" x="9" y="28" />
          <rect height="8" width="17" x="38" y="28" />
          <rect height="8" width="46" x="9" y="44" />
        </g>
      );
    case "B3":
      return (
        <g fill="currentColor">
          {[16, 32, 48].flatMap((cy) =>
            [16, 32, 48].map((cx) =>
              cx === 32 && cy === 32 ? (
                <rect
                  fill="none"
                  height="8"
                  key={`${cx}-${cy}`}
                  stroke="currentColor"
                  strokeWidth="2.5"
                  width="8"
                  x={cx - 4}
                  y={cy - 4}
                />
              ) : (
                <rect
                  height="8"
                  key={`${cx}-${cy}`}
                  width="8"
                  x={cx - 4}
                  y={cy - 4}
                />
              ),
            ),
          )}
        </g>
      );
    case "B4":
      return (
        <g
          fill="none"
          stroke="currentColor"
          strokeLinecap="square"
          strokeWidth="8"
        >
          <path d="M9 39h15m16 0h15" />
          <path d="M24 25h16" />
        </g>
      );
    case "C1":
      return (
        <g
          fill="none"
          stroke="currentColor"
          strokeLinecap="square"
          strokeLinejoin="miter"
          strokeWidth="7"
        >
          <path d="M22 11H11v42h11M42 11h11v42H42" />
          <path d="M32 16v32" />
        </g>
      );
    case "C2":
      return (
        <g
          fill="none"
          stroke="currentColor"
          strokeLinecap="square"
          strokeWidth="7"
        >
          <path d="m31 8 22 13" />
          <path d="m52 43-21 13" />
          <path d="M11 43V21" />
        </g>
      );
    case "C3":
      return (
        <g
          fill="none"
          stroke="currentColor"
          strokeLinecap="square"
          strokeLinejoin="miter"
          strokeWidth="6"
        >
          <path d="m32 8 21 24-21 24-21-24Z" />
          <path d="M5 32h54" />
        </g>
      );
    case "C4":
      return (
        <path
          d="M52 53V11H12v34h31V20H21v16h13v-7"
          fill="none"
          stroke="currentColor"
          strokeLinecap="square"
          strokeLinejoin="miter"
          strokeWidth="7"
        />
      );
    case "D1":
      return (
        <g fill="currentColor">
          <circle cx="20" cy="20" r="10" />
          <circle cx="44" cy="20" r="10" />
          <circle cx="20" cy="44" r="10" />
          <circle cx="44" cy="44" r="10" />
        </g>
      );
    case "D2":
      return (
        <path
          clipRule="evenodd"
          d="M32 6a26 26 0 1 0 0 52 26 26 0 1 0 0-52Zm-3 11h6v12h12v6H35v12h-6V35H17v-6h12V17Z"
          fill="currentColor"
          fillRule="evenodd"
        />
      );
    case "D3":
      return (
        <g
          fill="none"
          stroke="currentColor"
          strokeLinecap="square"
          strokeWidth="8"
        >
          <path d="m10 10 15 15M54 10 39 25M10 54l15-15M54 54 39 39" />
        </g>
      );
    case "D4":
      return (
        <g fill="currentColor">
          <rect height="7" width="13" x="9" y="45" />
          <rect height="7" width="13" x="22" y="32" />
          <rect height="7" width="13" x="35" y="19" />
          <circle cx="53" cy="11" r="6" />
        </g>
      );
    case "E1":
      return (
        <circle
          cx="32"
          cy="32"
          fill="none"
          r="22"
          stroke="currentColor"
          strokeDasharray="19.6 8"
          strokeLinecap="butt"
          strokeWidth="8"
          transform="rotate(-90 32 32)"
        />
      );
    case "E2":
      return (
        <g fill="none" stroke="currentColor" strokeWidth="7">
          <circle
            cx="29"
            cy="34"
            r="20"
            strokeDasharray="103 23"
            transform="rotate(-46 29 34)"
          />
          <circle cx="53" cy="10" fill="currentColor" r="5" stroke="none" />
        </g>
      );
    case "E3":
      return (
        <g
          fill="none"
          stroke="currentColor"
          strokeLinecap="square"
          strokeWidth="8"
        >
          <path d="M10 30A20 20 0 0 1 43 15" />
          <path d="M54 34A20 20 0 0 1 21 49" />
        </g>
      );
    case "E4":
      return (
        <g fill="currentColor">
          <rect height="35" width="7" x="11" y="10" />
          <rect height="35" width="7" x="23" y="10" />
          <rect height="35" width="7" x="35" y="10" />
          <rect height="35" width="7" x="47" y="19" />
        </g>
      );
  }
}

export function NulspecMark({ id, className }: NulspecMarkProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      focusable="false"
      viewBox="0 0 64 64"
      xmlns="http://www.w3.org/2000/svg"
    >
      {markGeometry(id)}
    </svg>
  );
}
