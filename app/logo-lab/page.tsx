import type { Metadata } from "next";
import {
  NulspecMark,
  type NulspecMarkId,
} from "@/components/nulspec-mark";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

export const metadata: Metadata = {
  title: "Logo Lab | NULSPEC",
  description: "Twenty geometric identity directions for NULSPEC.",
  robots: {
    index: false,
    follow: false,
  },
};

type Option = {
  id: NulspecMarkId;
  name: string;
  meaning: string;
  risk: string;
  fablePick?: boolean;
};

type Family = {
  id: string;
  name: string;
  premise: string;
  options: Option[];
};

const families: Family[] = [
  {
    id: "A",
    name: "The Null Glyph",
    premise: "The null sign is defined by what the geometry refuses to draw.",
    options: [
      {
        id: "A1",
        name: "Phantom Slash",
        meaning: "The slash exists only as an interruption in the circle.",
        risk: "Must not read as a prohibition sign.",
        fablePick: true,
      },
      {
        id: "A2",
        name: "Overshoot",
        meaning: "A null result punctures and escapes its own boundary.",
        risk: "Closest to a conventional null symbol.",
      },
      {
        id: "A3",
        name: "Null Ligature",
        meaning: "The N and null notation collapse into one machine glyph.",
        risk: "Can drift toward a generic tech monogram.",
      },
      {
        id: "A4",
        name: "Null Bit",
        meaning: "A machine-native NUL cell rendered as a strict square.",
        risk: "Can resemble a checkbox or close control.",
      },
    ],
  },
  {
    id: "B",
    name: "The Ledger",
    premise: "The record remains complete even when its measured value is null.",
    options: [
      {
        id: "B1",
        name: "Tally Null",
        meaning: "Four recorded attempts are crossed by a fifth mark made of absence.",
        risk: "The bars must not collapse into a barcode.",
        fablePick: true,
      },
      {
        id: "B2",
        name: "Punched Entry",
        meaning: "A ledger row keeps the exact place where its result is missing.",
        risk: "At small sizes it can resemble a menu.",
      },
      {
        id: "B3",
        name: "Indexed Absence",
        meaning: "The empty result retains equal rank and a permanent address.",
        risk: "No connecting lines; that would enter Atlas territory.",
      },
      {
        id: "B4",
        name: "Carried Line",
        meaning: "A null entry is lifted from the sequence but never discarded.",
        risk: "The quietest and least favicon-like option.",
      },
    ],
  },
  {
    id: "C",
    name: "Frozen Protocol",
    premise: "Decision rules are geometry fixed before the evidence arrives.",
    options: [
      {
        id: "C1",
        name: "Frozen Gate",
        meaning: "A decision bar is held motionless inside a protocol boundary.",
        risk: "Bracket syntax is common in developer brands.",
        fablePick: true,
      },
      {
        id: "C2",
        name: "Latent Lattice",
        meaning: "A complete frozen structure is implied by alternating absences.",
        risk: "Must avoid generic hexagonal tech branding.",
      },
      {
        id: "C3",
        name: "Setpoint",
        meaning: "A threshold is pinned through the decision boundary in advance.",
        risk: "Has some road-sign and fintech adjacency.",
      },
      {
        id: "C4",
        name: "One-Way Key",
        meaning: "The protocol runs forward and cannot close back on itself.",
        risk: "Can read as a maze or geometric G.",
      },
    ],
  },
  {
    id: "D",
    name: "The Negative Machine",
    premise: "Null units become a machine whose negative space yields a positive.",
    options: [
      {
        id: "D1",
        name: "Sum of Nothing",
        meaning: "Four equal null units make the positive sign between them.",
        risk: "The spacing must distinguish it from app-suite marks.",
      },
      {
        id: "D2",
        name: "Yield Aperture",
        meaning: "The positive result appears as an opening inside the null.",
        risk: "The cross can acquire medical associations.",
        fablePick: true,
      },
      {
        id: "D3",
        name: "Annihilator",
        meaning: "Four forces cancel before touching, preserving an empty center.",
        risk: "Must not collapse into a close icon.",
      },
      {
        id: "D4",
        name: "Gain Stage",
        meaning: "Repeated nulls step toward one rare positive output.",
        risk: "The ascent can imply generic growth.",
      },
    ],
  },
  {
    id: "E",
    name: "Distributed Custody",
    premise: "The lab is globally held without a center, owner node, or literal globe.",
    options: [
      {
        id: "E1",
        name: "Quorum Ring",
        meaning: "Equal fragments jointly maintain a boundary around no center.",
        risk: "The rhythm must avoid looking like a loading spinner.",
        fablePick: true,
      },
      {
        id: "E2",
        name: "Departed Node",
        meaning: "Compute and custody begin to leave a single boundary.",
        risk: "The detached dot can suggest a power control.",
      },
      {
        id: "E3",
        name: "Handoff",
        meaning: "Responsibility stays in motion between peers that never merge.",
        risk: "The arcs can resemble a chain or refresh symbol.",
      },
      {
        id: "E4",
        name: "Drifting Slat",
        meaning: "One equal unit decentralizes without becoming the hero.",
        risk: "Can resemble an equalizer or intentional glitch.",
      },
    ],
  },
];

const palette = [
  ["Signal ice", "#5CE8FF"],
  ["Steel blue", "#4A7C94"],
  ["Pale ice", "#E6F7FB"],
  ["Near-black", "#0A0E12"],
  ["Raised ground", "#131A21"],
  ["Border", "#233240"],
  ["Muted", "#8CA3B0"],
  ["Alert", "#FF5D55"],
];

export default function LogoLab() {
  return (
    <>
      <SiteHeader />
      <main className="logo-lab">
        <header className="shell logo-lab__intro">
          <p className="section-kicker">Identity study / 20 marks</p>
          <h1>Build the positive from nothing.</h1>
          <p>
            Five families, four marks each. Every option is exact one-color SVG
            geometry designed to survive at favicon size. The Atlas lineage is
            structural—equal units and no superstar—but NULSPEC makes absence
            do the work.
          </p>
          <p className="logo-lab__note">
            After reviewing the rendered marks, Fable&apos;s strongest overall
            direction is D2. Its strongest compact bug is A1. A blue dot marks
            Fable&apos;s visual pick in each family.
          </p>
        </header>

        <section className="shell logo-palette" aria-labelledby="palette-title">
          <div>
            <p className="section-kicker">Cold signal system</p>
            <h2 id="palette-title">Neon ice, used like evidence.</h2>
          </div>
          <div className="logo-palette__chips">
            {palette.map(([name, value]) => (
              <div className="logo-palette__chip" key={name}>
                <span style={{ backgroundColor: value }} />
                <strong>{name}</strong>
                <code>{value}</code>
              </div>
            ))}
          </div>
        </section>

        {families.map((family) => (
          <section
            className="shell logo-family"
            id={`family-${family.id.toLowerCase()}`}
            key={family.id}
          >
            <header className="logo-family__header">
              <p className="section-kicker">Family {family.id}</p>
              <h2>{family.name}</h2>
              <p>{family.premise}</p>
            </header>
            <div className="logo-options">
              {family.options.map((option) => (
                <article className="logo-option" key={option.id}>
                  <div className="logo-option__stage">
                    <NulspecMark id={option.id} />
                    <div className="logo-option__favicon" aria-hidden="true">
                      <NulspecMark id={option.id} />
                    </div>
                    <div
                      className="logo-option__favicon logo-option__favicon--light"
                      aria-hidden="true"
                    >
                      <NulspecMark id={option.id} />
                    </div>
                  </div>
                  <div className="logo-option__meta">
                    <div className="logo-option__title">
                      <span>{option.id}</span>
                      <h3>{option.name}</h3>
                      {option.fablePick && (
                        <i aria-hidden="true" title="Fable family pick" />
                      )}
                    </div>
                    <p>{option.meaning}</p>
                    <small>Watch: {option.risk}</small>
                  </div>
                </article>
              ))}
            </div>
          </section>
        ))}
      </main>
      <SiteFooter />
    </>
  );
}
