import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import PhotoManager from "../PhotoManager";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "../../../contexts/ThemeProvider";
import type { Photo } from "../../../lib/api";

// Mock the hooks
const mockUploadMutation = {
  mutateAsync: vi.fn(),
  isPending: false,
};

const mockUpdateMutation = {
  mutateAsync: vi.fn(),
  isPending: false,
};

const mockDeleteMutation = {
  mutateAsync: vi.fn(),
  isPending: false,
};

const mockRotateMutation = {
  mutateAsync: vi.fn(),
  isPending: false,
};

vi.mock("../../../hooks/useLogPhotos", () => ({
  useUploadPhoto: () => mockUploadMutation,
  useUpdatePhoto: () => mockUpdateMutation,
  useDeletePhoto: () => mockDeleteMutation,
  useRotatePhoto: () => mockRotateMutation,
}));

vi.mock("../../../hooks/useUserProfile", () => ({
  useUserProfile: () => ({
    data: { ui_prefs: { default_photo_license: "Y" } },
    isLoading: false,
  }),
}));

// Create a wrapper with QueryClient and ThemeProvider
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </ThemeProvider>
  );
};

const mockPhoto: Photo = {
  id: 1,
  log_id: 123,
  user_id: 1,
  caption: "Test photo",
  text_desc: "A test description",
  type: "T",
  license: "Y",
  photo_url: "https://example.com/photo.jpg",
  icon_url: "https://example.com/photo_icon.jpg",
  filesize: 1024,
  height: 600,
  width: 800,
  icon_filesize: 128,
  icon_height: 64,
  icon_width: 64,
};

describe("PhotoManager - Basic Rendering", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should render Photos heading when editing", () => {
    render(
      <PhotoManager logId={123} photos={[]} isEditing={true} />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText(/Photos/)).toBeInTheDocument();
  });

  it("should return null when not editing and no photos", () => {
    const { container } = render(
      <PhotoManager logId={123} photos={[]} isEditing={false} />,
      { wrapper: createWrapper() }
    );

    // Component returns null when not editing and no photos
    expect(container.firstChild).toBeNull();
  });

  it("should show photo count in heading when photos exist", () => {
    render(
      <PhotoManager logId={123} photos={[mockPhoto]} isEditing={false} />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText(/Photos \(1\)/)).toBeInTheDocument();
  });

  it("should render photo thumbnails with icon_url", () => {
    render(
      <PhotoManager logId={123} photos={[mockPhoto]} isEditing={false} />,
      { wrapper: createWrapper() }
    );

    const img = screen.getByAltText("Test photo");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", mockPhoto.icon_url);
  });
});

describe("PhotoManager - Add Photo Button", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should show Add Photo button when editing", () => {
    render(
      <PhotoManager logId={123} photos={[]} isEditing={true} />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText("Add Photo")).toBeInTheDocument();
  });

  it("should not show Add Photo button when not editing", () => {
    render(
      <PhotoManager logId={123} photos={[]} isEditing={false} />,
      { wrapper: createWrapper() }
    );

    expect(screen.queryByText("Add Photo")).not.toBeInTheDocument();
  });

  it("should have primary variant (green) styling on Add Photo button", () => {
    render(
      <PhotoManager logId={123} photos={[]} isEditing={true} />,
      { wrapper: createWrapper() }
    );

    const addButton = screen.getByText("Add Photo").closest("button");
    expect(addButton).toBeInTheDocument();
    // The button should have green background class from primary variant
    expect(addButton).toHaveClass("bg-trig-green-600");
  });

  it("should not show Add Photo button when logId is undefined", () => {
    render(
      <PhotoManager logId={undefined} photos={[]} isEditing={true} />,
      { wrapper: createWrapper() }
    );

    expect(screen.queryByText("Add Photo")).not.toBeInTheDocument();
  });
});

describe("PhotoManager - Rotate Buttons", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should show rotate buttons when editing", () => {
    render(
      <PhotoManager logId={123} photos={[mockPhoto]} isEditing={true} />,
      { wrapper: createWrapper() }
    );

    // Check for rotate button titles
    const ccwButton = screen.getByTitle("Rotate 90° counter-clockwise");
    const cwButton = screen.getByTitle("Rotate 90° clockwise");
    
    expect(ccwButton).toBeInTheDocument();
    expect(cwButton).toBeInTheDocument();
  });

  it("should not show rotate buttons when not editing", () => {
    render(
      <PhotoManager logId={123} photos={[mockPhoto]} isEditing={false} />,
      { wrapper: createWrapper() }
    );

    expect(screen.queryByTitle("Rotate 90° counter-clockwise")).not.toBeInTheDocument();
    expect(screen.queryByTitle("Rotate 90° clockwise")).not.toBeInTheDocument();
  });

  it("should call rotateMutation with 270 for CCW rotation", async () => {
    render(
      <PhotoManager logId={123} photos={[mockPhoto]} isEditing={true} />,
      { wrapper: createWrapper() }
    );

    const ccwButton = screen.getByTitle("Rotate 90° counter-clockwise");
    fireEvent.click(ccwButton);

    await waitFor(() => {
      expect(mockRotateMutation.mutateAsync).toHaveBeenCalledWith({
        photoId: mockPhoto.id,
        angle: 270,
      });
    });
  });

  it("should call rotateMutation with 90 for CW rotation", async () => {
    render(
      <PhotoManager logId={123} photos={[mockPhoto]} isEditing={true} />,
      { wrapper: createWrapper() }
    );

    const cwButton = screen.getByTitle("Rotate 90° clockwise");
    fireEvent.click(cwButton);

    await waitFor(() => {
      expect(mockRotateMutation.mutateAsync).toHaveBeenCalledWith({
        photoId: mockPhoto.id,
        angle: 90,
      });
    });
  });

  it("should show delete button when editing", () => {
    render(
      <PhotoManager logId={123} photos={[mockPhoto]} isEditing={true} />,
      { wrapper: createWrapper() }
    );

    const deleteButton = screen.getByTitle("Delete photo");
    expect(deleteButton).toBeInTheDocument();
  });
});

describe("PhotoManager - Photo Display", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should display photo caption", () => {
    render(
      <PhotoManager logId={123} photos={[mockPhoto]} isEditing={false} />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText("Test photo")).toBeInTheDocument();
  });

  it("should display photo description", () => {
    render(
      <PhotoManager logId={123} photos={[mockPhoto]} isEditing={false} />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText("A test description")).toBeInTheDocument();
  });

  it("should show edit button for photo when editing", () => {
    render(
      <PhotoManager logId={123} photos={[mockPhoto]} isEditing={true} />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByTitle("Edit metadata")).toBeInTheDocument();
  });
});

describe("PhotoManager - Multiple Photos", () => {
  const multiplePhotos: Photo[] = [
    { ...mockPhoto, id: 1, caption: "Photo 1", icon_url: "https://example.com/photo1_icon.jpg" },
    { ...mockPhoto, id: 2, caption: "Photo 2", icon_url: "https://example.com/photo2_icon.jpg" },
    { ...mockPhoto, id: 3, caption: "Photo 3", icon_url: "https://example.com/photo3_icon.jpg" },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should render all photos", () => {
    render(
      <PhotoManager logId={123} photos={multiplePhotos} isEditing={false} />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText("Photo 1")).toBeInTheDocument();
    expect(screen.getByText("Photo 2")).toBeInTheDocument();
    expect(screen.getByText("Photo 3")).toBeInTheDocument();
  });

  it("should show correct photo count", () => {
    render(
      <PhotoManager logId={123} photos={multiplePhotos} isEditing={false} />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText(/Photos \(3\)/)).toBeInTheDocument();
  });

  it("should show rotate buttons for each photo when editing", () => {
    render(
      <PhotoManager logId={123} photos={multiplePhotos} isEditing={true} />,
      { wrapper: createWrapper() }
    );

    const ccwButtons = screen.getAllByTitle("Rotate 90° counter-clockwise");
    const cwButtons = screen.getAllByTitle("Rotate 90° clockwise");
    
    expect(ccwButtons).toHaveLength(3);
    expect(cwButtons).toHaveLength(3);
  });
});

