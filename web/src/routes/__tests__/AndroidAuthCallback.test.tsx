import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import AndroidAuthCallback from "../AndroidAuthCallback";

function renderCallbackRoute(initialEntry: string) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <AndroidAuthCallback />
    </MemoryRouter>
  );
}

describe("AndroidAuthCallback", () => {
  it("renders a release app deep-link button that preserves callback query and hash", () => {
    renderCallbackRoute(
      "/android/uk.trigpointing.android/callback?code=abc123&state=state123#id_token=token123"
    );

    const openAppButton = screen.getByRole("link", {
      name: /open trigpointinguk app/i,
    });

    expect(openAppButton).toHaveAttribute(
      "href",
      "uk.trigpointing.android://auth.trigpointing.uk/android/uk.trigpointing.android/callback?code=abc123&state=state123#id_token=token123"
    );

    // Sensitive callback values should not be rendered as visible text.
    expect(screen.queryByText("abc123")).not.toBeInTheDocument();
    expect(screen.queryByText("state123")).not.toBeInTheDocument();
    expect(screen.queryByText("token123")).not.toBeInTheDocument();
  });

  it("renders a debug app deep-link button for debug callback paths", () => {
    renderCallbackRoute(
      "/android/uk.trigpointing.android.debug/callback?code=debugcode&state=debugstate"
    );

    const openAppButton = screen.getByRole("link", {
      name: /open trigpointinguk app/i,
    });

    expect(openAppButton).toHaveAttribute(
      "href",
      "uk.trigpointing.android.debug://auth.trigpointing.uk/android/uk.trigpointing.android.debug/callback?code=debugcode&state=debugstate"
    );
  });

  it("shows a friendly error message when callback includes an error", () => {
    renderCallbackRoute("/android/uk.trigpointing.android/callback?error=access_denied");

    expect(
      screen.getByText(/we could not complete sign-in in the app/i)
    ).toBeInTheDocument();
  });

  it("sets noindex and no-store metadata on the page", async () => {
    renderCallbackRoute("/android/uk.trigpointing.android/callback?code=abc123");

    await waitFor(() => {
      expect(document.title).toBe("Open TrigpointingUK App");
    });

    expect(
      document.head.querySelector('meta[name="robots"]')?.getAttribute("content")
    ).toBe("noindex, nofollow, noarchive");

    expect(
      document.head.querySelector('meta[http-equiv="Cache-Control"]')?.getAttribute("content")
    ).toBe("no-store, no-cache, must-revalidate, max-age=0");
  });

  it("is matched by the app router instead of the generic 404 page", async () => {
    window.history.replaceState(
      {},
      "",
      "/android/uk.trigpointing.android/callback?code=abc123&state=state123"
    );

    const { default: AppRouter } = await import("../../router");
    render(<AppRouter />);

    expect(
      await screen.findByRole("link", { name: /open trigpointinguk app/i })
    ).toBeInTheDocument();
    expect(screen.queryByText(/404 - not found/i)).not.toBeInTheDocument();
  });
});
