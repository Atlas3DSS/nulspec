import ledger from "@/site-data/public-archive/data/selection-ledger.json";

export type SelectionCandidate = (typeof ledger.candidates)[number];

export function getSelectionLedger() {
  return ledger;
}
