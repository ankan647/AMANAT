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

export interface ApiErrorBody {
  error: { code: string; message: string; details: Record<string, unknown>; request_id: string };
}

export class ApiError extends Error {
  code: string;
  details: Record<string, unknown>;
  status: number;

  constructor(status: number, body: ApiErrorBody) {
    super(body.error.message);
    this.code = body.error.code;
    this.details = body.error.details;
    this.status = status;
  }
}

/** Thin helpers so every call site gets a concretely-typed `data`, never `any`. */
export async function apiGet<T>(path: string, params?: Record<string, unknown>): Promise<T> {
  const { data, error, response } = await client.GET(path as never, {
    params: { query: params },
  } as never);
  if (error || !response.ok) {
    throw new ApiError(response.status, error as unknown as ApiErrorBody);
  }
  return data as T;
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const { data, error, response } = await client.POST(path as never, { body } as never);
  if (error || !response.ok) {
    throw new ApiError(response.status, error as unknown as ApiErrorBody);
  }
  return data as T;
}

export async function apiGetBlob(path: string): Promise<Blob> {
  const { data, error, response } = await client.GET(path as never, { parseAs: "blob" } as never);
  if (error || !response.ok) {
    throw new ApiError(response.status, error as unknown as ApiErrorBody);
  }
  return data as Blob;
}

export async function apiPostForm<T>(path: string, form: FormData): Promise<T> {
  const { data, error, response } = await client.POST(path as never, { body: form } as never);
  if (error || !response.ok) {
    throw new ApiError(response.status, error as unknown as ApiErrorBody);
  }
  return data as T;
}
