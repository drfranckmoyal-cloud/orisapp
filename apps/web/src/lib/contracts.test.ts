import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import {
  CLINICAL_FACT_ASSERTION_VALUES,
  CLINICAL_FACT_CLINICAL_STATUS_VALUES,
  type ClinicalFact,
} from "@/contracts/generated";

const repoRoot = resolve(__dirname, "../../../..");

describe("generated contracts", () => {
  it("expose the schema enums", () => {
    const schema = JSON.parse(
      readFileSync(resolve(repoRoot, "schemas/clinical_fact.schema.json"), "utf-8"),
    );
    expect([...CLINICAL_FACT_ASSERTION_VALUES]).toEqual(schema.properties.assertion.enum);
    expect([...CLINICAL_FACT_CLINICAL_STATUS_VALUES]).toEqual(
      schema.properties.clinical_status.enum,
    );
  });

  it("type the synthetic corpus facts", () => {
    const firstCase = readFileSync(
      resolve(repoRoot, "corpus/synthetic_consultations_100.jsonl"),
      "utf-8",
    ).split("\n")[0];
    const facts: ClinicalFact[] = JSON.parse(firstCase ?? "{}").expected.facts;
    expect(facts.every((fact) => CLINICAL_FACT_ASSERTION_VALUES.includes(fact.assertion))).toBe(true);
  });
});
