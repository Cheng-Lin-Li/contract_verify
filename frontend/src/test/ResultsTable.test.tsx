import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultsTable from "../components/ResultsTable";
import type { ReportRow } from "../types";

const rows: ReportRow[] = [
  { item_id: "r-001", layer: 1, type: "payment", priority: "Critical", status: "Superseded",
    confidence: 1, requirement_text: "Payment net-30", matched_clause_ids: [], notes: "" },
  { item_id: "r-007", layer: 1, type: "payment", status: "Covered",
    confidence: 0.9, requirement_text: "Payment net-45", matched_clause_ids: ["b-002"], notes: "" },
];

describe("ResultsTable", () => {
  it("renders one row per reference item", () => {
    render(<ResultsTable rows={rows} />);
    expect(screen.getByText("r-001")).toBeInTheDocument();
    expect(screen.getByText("r-007")).toBeInTheDocument();
  });

  it("shows the matched clause id", () => {
    render(<ResultsTable rows={rows} />);
    expect(screen.getByText("b-002")).toBeInTheDocument();
  });
});
