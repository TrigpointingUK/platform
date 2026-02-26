import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode } from "react";

// Mock useAvatarUpload hook
const mockMutateAsync = vi.fn();
vi.mock("../../../hooks/useAvatarUpload", () => ({
  useAvatarUpload: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
}));

// Mock react-easy-crop (not available in jsdom)
vi.mock("react-easy-crop", () => ({
  __esModule: true,
  default: ({ onCropComplete }: { onCropComplete: (a: unknown, b: unknown) => void }) => {
    // Immediately report a crop area so the upload button enables
    setTimeout(
      () =>
        onCropComplete(
          { x: 0, y: 0, width: 100, height: 100 },
          { x: 0, y: 0, width: 100, height: 100 }
        ),
      0
    );
    return <div data-testid="cropper">Cropper</div>;
  },
}));

// Mock getCroppedImg
vi.mock("../../../lib/cropImage", () => ({
  getCroppedImg: vi.fn().mockResolvedValue(new Blob(["fake"], { type: "image/jpeg" })),
}));

// Mock react-hot-toast
vi.mock("react-hot-toast", () => ({
  __esModule: true,
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import AvatarUploadModal from "../AvatarUploadModal";

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

const renderModal = (props?: Partial<{ currentPictureUrl: string; onUploaded: (url: string) => void }>) => {
  const defaultProps = {
    onUploaded: vi.fn(),
    ...props,
  };
  const Wrapper = createWrapper();
  return {
    ...render(
      <Wrapper>
        <AvatarUploadModal {...defaultProps} />
      </Wrapper>
    ),
    onUploaded: defaultProps.onUploaded,
  };
};

describe("AvatarUploadModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("trigger button", () => {
    it("should render a button to change the avatar", () => {
      renderModal();
      expect(screen.getByTitle("Change avatar")).toBeInTheDocument();
    });

    it("should display the current picture when provided", () => {
      renderModal({ currentPictureUrl: "https://example.com/avatar.jpg" });
      const img = screen.getByAltText("User avatar");
      expect(img).toHaveAttribute("src", "https://example.com/avatar.jpg");
    });

    it("should show a camera icon when no picture is set", () => {
      renderModal();
      expect(screen.queryByAltText("User avatar")).not.toBeInTheDocument();
    });
  });

  describe("dialog", () => {
    it("should open the dialog when the trigger is clicked", () => {
      renderModal();
      fireEvent.click(screen.getByTitle("Change avatar"));
      expect(screen.getByText("Update Avatar")).toBeInTheDocument();
      expect(screen.getByText("Choose Image")).toBeInTheDocument();
    });

    it("should show file format guidance text", () => {
      renderModal();
      fireEvent.click(screen.getByTitle("Change avatar"));
      expect(screen.getByText(/JPEG, PNG, or WebP/)).toBeInTheDocument();
    });

    it("should have a Cancel button", () => {
      renderModal();
      fireEvent.click(screen.getByTitle("Change avatar"));
      expect(screen.getByText("Cancel")).toBeInTheDocument();
    });

    it("should close when Cancel is clicked", () => {
      renderModal();
      fireEvent.click(screen.getByTitle("Change avatar"));
      expect(screen.getByText("Update Avatar")).toBeInTheDocument();

      fireEvent.click(screen.getByText("Cancel"));
      // Dialog title should no longer be visible
      expect(screen.queryByText("Update Avatar")).not.toBeInTheDocument();
    });
  });

  describe("file input", () => {
    it("should have a hidden file input that accepts images", () => {
      renderModal();
      fireEvent.click(screen.getByTitle("Change avatar"));

      const fileInput = document.querySelector(
        'input[type="file"]'
      ) as HTMLInputElement;
      expect(fileInput).not.toBeNull();
      expect(fileInput.accept).toBe("image/jpeg,image/png,image/webp");
      expect(fileInput.classList.contains("hidden")).toBe(true);
    });
  });
});
