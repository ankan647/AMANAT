export interface AuthUser {
  id: number;
  name: string;
  email: string;
  role:
    | "institution"
    | "scrutiny"
    | "senior_approver"
    | "competent_authority"
    | "admin"
    | "auditor"
    | "bank_officer";
  bank_name: string | null;
  institution_id: number | null;
}

const TOKEN_KEY = "amanat_token";
const USER_KEY = "amanat_user";

export function saveSession(token: string, user: AuthUser) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getStoredUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
