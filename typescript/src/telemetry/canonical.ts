/** Deterministic JSON for cross-language golden telemetry vectors. */

function canonicalValue(value: unknown): unknown {
  if (value === null || typeof value === "string" || typeof value === "boolean") return value;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error("canonical telemetry JSON forbids non-finite numbers");
    return value;
  }
  if (Array.isArray(value)) return value.map(canonicalValue);
  if (typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Readonly<Record<string, unknown>>)
        .sort(([left], [right]) => (left < right ? -1 : left > right ? 1 : 0))
        .map(([key, item]) => [key, canonicalValue(item)]),
    );
  }
  throw new Error(`canonical telemetry JSON forbids ${typeof value}`);
}

export function canonicalJson(value: unknown): string {
  return JSON.stringify(canonicalValue(value));
}
