import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

const vectors = JSON.parse(readFileSync(new URL("../reference/email-digest-vectors.json", import.meta.url), "utf8"));
for (const vector of vectors) {
  const roundTrip = JSON.stringify(JSON.parse(vector.canonical_json));
  if (roundTrip !== vector.canonical_json) throw new Error(`${vector.name}: canonical bytes differ`);
  const digest = `sha256:${createHash("sha256").update(roundTrip).digest("hex")}`;
  if (digest !== vector.sha256) throw new Error(`${vector.name}: digest mismatch`);
}
console.log(`verified ${vectors.length} email digest vectors in JavaScript`);
