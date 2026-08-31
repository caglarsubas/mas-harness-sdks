import { createContext, instrumentSync, type SpanRecord } from "../../typescript/src/telemetry/index.ts";

const records: SpanRecord[] = [];
const context = createContext({
  traceId: "4bf92f3577b34da6a3ce929d0e0e4736",
  spanId: "00f067aa0ba902b7",
  traceFlags: "00",
  tenantId: "tenant-example",
  organizationId: "organization-example",
  harnessId: "knowledge.domain-semantic",
  planeId: "knowledge",
});

const inspectLocalFixture = instrumentSync(
  "harness.example.inspect",
  () => "accepted",
  {
    attributes: { "harness.label.scenario": "local_only" },
    traceIdFactory: () => "11111111111111111111111111111111",
    spanIdFactory: () => "1111111111111111",
    sink: (record) => records.push(record),
  },
);

inspectLocalFixture(context);
if (records.length !== 1) throw new Error("expected one local span record");
