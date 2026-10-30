export type Role =
  | "institution"
  | "scrutiny"
  | "senior_approver"
  | "competent_authority"
  | "admin"
  | "auditor"
  | "bank_officer";

export function roleLabel(role: Role): string {
  return role.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function homeRouteFor(role: Role, institutionId: number | null): string {
  if (role === "institution") return institutionId ? `/institutions/${institutionId}` : "/";
  if (role === "bank_officer") return "/bank";
  if (role === "auditor") return "/audit";
  return "/";
}
