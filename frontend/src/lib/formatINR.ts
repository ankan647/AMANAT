export function formatINR(paise: number): string {
  const rupees = paise / 100;
  const formatted = new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: rupees % 1 === 0 ? 0 : 2,
  }).format(rupees);
  return `₹${formatted}`;
}

export function paiseToRupees(paise: number): number {
  return paise / 100;
}

export function rupeesToPaise(rupees: number): number {
  return Math.round(rupees * 100);
}
