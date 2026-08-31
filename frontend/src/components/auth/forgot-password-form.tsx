"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { MailCheck } from "lucide-react";

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
  forgotPasswordSchema,
  type ForgotPasswordValues,
} from "@/lib/validations/auth";
import { ROUTES } from "@/lib/constants";

export function ForgotPasswordForm() {
  const [sentTo, setSentTo] = React.useState<string | null>(null);

  const form = useForm<ForgotPasswordValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  });

  async function onSubmit(values: ForgotPasswordValues) {
    try {
      await authApi.requestPasswordReset(values);
      setSentTo(values.email);
    } catch (error) {
      applyFieldErrors(error, form.setError);
      form.setError("root", { message: getErrorMessage(error) });
    }
  }

  // The API will not say whether the address is registered, and neither does
  // this screen -- confirming it would leak who has an account.
  if (sentTo) {
    return (
      <div className="space-y-4 text-sm">
        <div className="flex items-start gap-3 rounded-md border p-3">
          <MailCheck className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
          <p className="text-muted-foreground">
            If an account exists for <span className="text-foreground">{sentTo}</span>,
            a reset link is on its way. The link expires in 24 hours.
          </p>
        </div>
        <p className="text-muted-foreground">
          Nothing arrived? Check the spam folder, or{" "}
          <button
            type="button"
            onClick={() => setSentTo(null)}
            className="text-foreground underline underline-offset-4"
          >
            try another address
          </button>
          .
        </p>
        <Button asChild variant="outline" className="w-full">
          <Link href={ROUTES.login}>Back to sign in</Link>
        </Button>
      </div>
    );
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input
                  type="email"
                  placeholder="you@example.com"
                  autoComplete="email"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {form.formState.errors.root ? (
          <p className="text-sm text-destructive">
            {form.formState.errors.root.message}
          </p>
        ) : null}
        <Button
          type="submit"
          className="w-full"
          disabled={form.formState.isSubmitting}
        >
          {form.formState.isSubmitting ? "Sending…" : "Send reset link"}
        </Button>
      </form>
      <p className="mt-4 text-center text-sm text-muted-foreground">
        Remembered it?{" "}
        <Link
          href={ROUTES.login}
          className="text-foreground underline underline-offset-4"
        >
          Sign in
        </Link>
      </p>
    </Form>
  );
}
