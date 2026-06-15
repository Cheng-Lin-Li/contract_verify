import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ScoreCards from "../components/ScoreCards";
import type { ScoreSummary } from "../types";

const scores: ScoreSummary = {
  coverage_score: 90,
  risk_score: 45,
  playbook_compliance: { Compliant: 3, Deviation: 1 },
  standard_terms_completeness: { Present: 2, "Non-standard": 3 },
  auto_confirm: false,
  blocking_reasons: [],
};

describe("ScoreCards", () => {
  it("renders the coverage percentage", () => {
    render(<ScoreCards scores={scores} />);
    expect(screen.getByText("90%")).toBeInTheDocument();
  });

  it("renders the risk score", () => {
    render(<ScoreCards scores={scores} />);
    expect(screen.getByText("45")).toBeInTheDocument();
  });

  it("tallies playbook compliance", () => {
    render(<ScoreCards scores={scores} />);
    expect(screen.getByText(/Compliant: 3/)).toBeInTheDocument();
  });
});
