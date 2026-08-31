import { z } from "zod";

/** Login form schema — keep messages user-friendly. */
export const loginSchema = z.object({
  email: z.string().min(1, "Email is required").email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

export type LoginValues = z.infer<typeof loginSchema>;

/** Registration schema with confirmation + matching rule. */
export const registerSchema = z
  .object({
    name: z.string().min(2, "Name must be at least 2 characters").max(150),
    email: z.string().min(1, "Email is required").email("Enter a valid email"),
    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .max(128, "Password is too long"),
    password_confirm: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.password === data.password_confirm, {
    message: "Passwords do not match",
    path: ["password_confirm"],
  });

export type RegisterValues = z.infer<typeof registerSchema>;

/** Profile update schema. */
export const profileSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters").max(150),
  avatar: z.string().url("Enter a valid URL").or(z.literal("")),
});

export type ProfileValues = z.infer<typeof profileSchema>;

/** "Email me a reset link" form. */
export const forgotPasswordSchema = z.object({
  email: z.string().min(1, "Email is required").email("Enter a valid email"),
});

export type ForgotPasswordValues = z.infer<typeof forgotPasswordSchema>;

/**
 * Choosing a new password from a reset link.
 *
 * `uid` and `token` come from the link's query string, not from the user, so
 * they are carried through the form rather than typed into it.
 */
export const resetPasswordSchema = z
  .object({
    uid: z.string().min(1),
    token: z.string().min(1),
    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .max(128, "Password is too long"),
    password_confirm: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.password === data.password_confirm, {
    message: "Passwords do not match",
    path: ["password_confirm"],
  });

export type ResetPasswordValues = z.infer<typeof resetPasswordSchema>;
