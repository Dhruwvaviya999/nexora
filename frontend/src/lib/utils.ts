import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge conditional class names and resolve Tailwind conflicts.
 * Used by every shadcn/ui component (`cn(...)`).
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
