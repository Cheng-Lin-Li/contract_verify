import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import GateBanner from "../components/GateBanner";
import type { ScoreSummary } from "../types";

const base: ScoreSummary = {
  coverage_score: 90, risk_score: 45, playbook_compliance: {}, standard_terms_completeness: {},
  auto_confirm: false, blocking_reasons: ["Low confidence (0.67) on r-003"],
};

describe("GateBanner", () => {
  it("lists blocking reasons when not auto-confirmed", () => {
    render(<GateBanner scores={base} />);
    expect(screen.getByText(/Low confidence/)).toBeInTheDocument();
  });

  it("shows the auto-confirm state when clean", () => {
    render(<GateBanner scores={{ ...base, auto_confirm: true, blocking_reasons: [] }} />);
    expect(screen.getByText(/✓/)).toBeInTheDocument();
  });
});
