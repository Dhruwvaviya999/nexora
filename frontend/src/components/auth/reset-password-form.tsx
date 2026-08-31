"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { authApi } from "@/lib/api/auth";
import { applyFieldErrors, getErrorMessage } from "@/lib/api/errors";
import {
  resetPasswordSchema,
  type ResetPasswordValues,
} from "@/lib/validations/auth";
import { ROUTES } from "@/lib/constants";

export function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const uid = searchParams.get("uid") ?? "";
  const token = searchParams.get("token") ?? "";

  const form = useForm<ResetPasswordValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { uid, token, password: "", password_confirm: "" },
  });

  async function onSubmit(values: ResetPasswordValues) {
    try {
      await authApi.confirmPasswordReset(values);
      toast.success("Password updated. Sign in with your new password.");
      router.replace(ROUTES.login);
    } catch (error) {
      applyFieldErrors(error, form.setError);
      form.setError("root", { message: getErrorMessage(error) });
    }
  }

  // A link that lost its query string can never succeed; say so up front
  // rather than after the user has typed a password twice.
  if (!uid || !token) {
    return (
      <div className="space-y-4 text-sm">
        <p className="text-muted-foreground">
          This reset link is incomplete. Request a fresh one and open it
          directly from the email.
        </p>
        <Button asChild className="w-full">
          <Link href={ROUTES.forgotPassword}>Request a new link</Link>
        </Button>
      </div>
    );
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>New password</FormLabel>
              <FormControl>
                <Input
                  type="password"
                  placeholder="••••••••"
                  autoComplete="new-password"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password_confirm"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Confirm new password</FormLabel>
              <FormControl>
                <Input
                  type="password"
                  placeholder="••••••••"
                  autoComplete="new-password"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {form.formState.errors.root ? (
          <p className="text-sm text-destructive">
            {form.formState.errors.root.message}{" "}
            <Link
              href={ROUTES.forgotPassword}
              className="underline underline-offset-4"
            >
              Request a new link
            </Link>
          </p>
        ) : null}
        <Button
          type="submit"
          className="w-full"
          disabled={form.formState.isSubmitting}
        >
          {form.formState.isSubmitting ? "Updating…" : "Set new password"}
        </Button>
      </form>
    </Form>
  );
}
