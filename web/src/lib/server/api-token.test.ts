import { decodeProtectedHeader, jwtVerify } from "jose";
import { describe, expect, it } from "vitest";

import { API_TOKEN_TTL_SECONDS, mintApiToken } from "./api-token";
import { env } from "./env";

// These are exactly the checks api/app/auth/tokens.py makes (ADR-036).
describe("mintApiToken", () => {
  it("issues the token FastAPI expects", async () => {
    const token = await mintApiToken("7");
    const { payload } = await jwtVerify(token, new TextEncoder().encode(env.apiJwtSecret), {
      issuer: "swr-web",
      audience: "swr-api",
      algorithms: ["HS256"],
    });
    expect(decodeProtectedHeader(token).alg).toBe("HS256");
    expect(payload.sub).toBe("7");
    expect(payload.exp! - payload.iat!).toBe(API_TOKEN_TTL_SECONDS);
  });

  it("refuses a non-numeric user id", async () => {
    await expect(mintApiToken("abc")).rejects.toThrow(/numeric/);
  });
});
