"use client";

// Browser side of Better Auth (ADR-035): sign in, sign out, magic links.
import { magicLinkClient } from "better-auth/client/plugins";
import { createAuthClient } from "better-auth/react";

export const authClient = createAuthClient({ plugins: [magicLinkClient()] });
