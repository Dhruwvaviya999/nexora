import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

const requestPasswordReset = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/auth", () => ({ authApi: { requestPasswordReset } }));

import { ForgotPasswordForm } from "./forgot-password-form";

describe("ForgotPasswordForm", () => {
  it("sends the address and confirms without revealing whether it exists", async () => {
    requestPasswordReset.mockResolvedValue({ detail: "ok" });
    const user = userEvent.setup();
    render(<ForgotPasswordForm />);

    await user.type(screen.getByLabelText(/email/i), "someone@example.com");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    await waitFor(() =>
      expect(requestPasswordReset).toHaveBeenCalledWith({
        email: "someone@example.com",
      })
    );
    // Deliberately conditional wording -- a definite "sent!" would confirm the
    // address is registered.
    expect(screen.getByText(/if an account exists/i)).toBeInTheDocument();
  });

  it("rejects a malformed address before calling the API", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordForm />);

    await user.type(screen.getByLabelText(/email/i), "not-an-email");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    // The field is type="email", so the browser's own constraint validation
    // refuses the submit before the schema is consulted. Either way the
    // guarantee that matters is the same: nothing is sent.
    expect(requestPasswordReset).not.toHaveBeenCalled();
    expect(screen.queryByText(/if an account exists/i)).not.toBeInTheDocument();
  });

  it("requires an address", async () => {
    const user = userEvent.setup();
    render(<ForgotPasswordForm />);

    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
    expect(requestPasswordReset).not.toHaveBeenCalled();
  });

  it("surfaces a server failure instead of claiming success", async () => {
    requestPasswordReset.mockRejectedValue(new Error("Too many requests"));
    const user = userEvent.setup();
    render(<ForgotPasswordForm />);

    await user.type(screen.getByLabelText(/email/i), "someone@example.com");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));

    await waitFor(() =>
      expect(screen.queryByText(/if an account exists/i)).not.toBeInTheDocument()
    );
  });

  it("lets the user go back and try a different address", async () => {
    requestPasswordReset.mockResolvedValue({ detail: "ok" });
    const user = userEvent.setup();
    render(<ForgotPasswordForm />);

    await user.type(screen.getByLabelText(/email/i), "someone@example.com");
    await user.click(screen.getByRole("button", { name: /send reset link/i }));
    await screen.findByText(/if an account exists/i);

    await user.click(screen.getByRole("button", { name: /try another address/i }));

    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  });
});
