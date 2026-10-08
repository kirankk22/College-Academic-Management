import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getSession,
  signIn,
  signOut,
} from "./auth";

const supabaseMocks = vi.hoisted(() => ({
  signInWithPassword: vi.fn(),
  signOut: vi.fn(),
  getSession: vi.fn(),
}));

vi.mock("@supabase/supabase-js", () => ({
  createClient: vi.fn(() => ({
    auth: {
      signInWithPassword:
        supabaseMocks.signInWithPassword,
      signOut: supabaseMocks.signOut,
      getSession: supabaseMocks.getSession,
      onAuthStateChange: vi.fn(() => ({
        data: {
          subscription: {
            unsubscribe: vi.fn(),
          },
        },
      })),
    },
  })),
}));

afterEach(() => {
  vi.clearAllMocks();
});

describe("authentication service", () => {
  it("signs in and returns the Supabase session", async () => {
    const session = {
      access_token: "access-token",
      token_type: "bearer",
    };

    supabaseMocks.signInWithPassword.mockResolvedValue({
      data: {
        session,
      },
      error: null,
    });

    const result = await signIn(
      "principal.demo@college-demo.local",
      "password",
    );

    expect(result).toEqual(session);

    expect(
      supabaseMocks.signInWithPassword,
    ).toHaveBeenCalledWith({
      email:
        "principal.demo@college-demo.local",
      password: "password",
    });
  });

  it("throws when Supabase login returns an error", async () => {
    supabaseMocks.signInWithPassword.mockResolvedValue({
      data: {
        session: null,
      },
      error: {
        message: "Invalid login credentials",
      },
    });

    await expect(
      signIn(
        "principal.demo@college-demo.local",
        "wrong-password",
      ),
    ).rejects.toThrow(
      "Invalid login credentials",
    );
  });

  it("throws when login succeeds without a session", async () => {
    supabaseMocks.signInWithPassword.mockResolvedValue({
      data: {
        session: null,
      },
      error: null,
    });

    await expect(
      signIn(
        "principal.demo@college-demo.local",
        "password",
      ),
    ).rejects.toThrow(
      "Supabase login did not return a session",
    );
  });

  it("returns the current session", async () => {
    const session = {
      access_token: "current-access-token",
      token_type: "bearer",
    };

    supabaseMocks.getSession.mockResolvedValue({
      data: {
        session,
      },
      error: null,
    });

    const result = await getSession();

    expect(result).toEqual(session);
  });

  it("signs out successfully", async () => {
    supabaseMocks.signOut.mockResolvedValue({
      error: null,
    });

    await expect(
      signOut(),
    ).resolves.toBeUndefined();

    expect(
      supabaseMocks.signOut,
    ).toHaveBeenCalledTimes(1);
  });
});