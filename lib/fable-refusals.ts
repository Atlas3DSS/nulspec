import ledger from "@/site-data/fable-refusals.json";

export type FableRefusal = (typeof ledger.refusals)[number];

export function getFableRefusalLedger() {
  return ledger;
}
