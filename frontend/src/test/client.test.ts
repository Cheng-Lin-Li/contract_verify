import { describe, expect, it, beforeEach } from "vitest";
import { getToken, setToken } from "../api/client";

describe("api client token storage", () => {
  beforeEach(() => localStorage.clear());

  it("stores and clears the bearer token", () => {
    expect(getToken()).toBeNull();
    setToken("abc");
    expect(getToken()).toBe("abc");
    setToken(null);
    expect(getToken()).toBeNull();
  });
});
