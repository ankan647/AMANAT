import createClient from "openapi-fetch";
import type { paths } from "./schema.d.ts";

// Path keys from the generated schema already include the `/api/v1` prefix, so the base URL is
// just the origin the Vite dev server proxies `/api` from (see vite.config.ts).
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

function getToken(): string | null {
  try {
    return localStorage.getItem("amanat_token");
  } catch {
    return null;
  }
}

export const client = createClient<paths>({ baseUrl: BASE_URL });

client.use({
  onRequest({ request }) {
    const token = getToken();
    if (token) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  },
});

export type { paths };
