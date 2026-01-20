import type { ReactNode } from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { useAuth0 } from "@auth0/auth0-react";
import TypesAdmin from "../TypesAdmin";

// Mock Auth0
vi.mock("@auth0/auth0-react", () => ({
  useAuth0: vi.fn(),
}));

// Mock Layout component
vi.mock("../../../components/layout/Layout", () => ({
  default: ({ children }: { children: ReactNode }) => <div data-testid="layout">{children}</div>,
}));

// Mock react-hot-toast
vi.mock("react-hot-toast", () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock lucide-react icons - include all used icons
vi.mock("lucide-react", () => ({
  Plus: () => <span data-testid="icon-plus">+</span>,
  Pencil: () => <span data-testid="icon-pencil">✏</span>,
  Trash2: () => <span data-testid="icon-trash">🗑</span>,
  ChevronDown: () => <span data-testid="icon-chevron-down">▼</span>,
  ChevronRight: () => <span data-testid="icon-chevron-right">▶</span>,
  GripVertical: () => <span data-testid="icon-grip">⋮</span>,
  ExternalLink: () => <span data-testid="icon-external">↗</span>,
  X: () => <span data-testid="icon-x">×</span>,
}));

// Mock API functions
vi.mock("../../../lib/api", () => ({
  fetchCategoriesWithTypes: vi.fn(),
  createCategory: vi.fn(),
  updateCategory: vi.fn(),
  deleteCategory: vi.fn(),
  reorderCategories: vi.fn(),
  createType: vi.fn(),
  updateType: vi.fn(),
  deleteType: vi.fn(),
  reorderTypes: vi.fn(),
  fetchTypeUsage: vi.fn(),
}));

// Mock DnD Kit
vi.mock("@dnd-kit/core", () => ({
  DndContext: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  closestCenter: vi.fn(),
  KeyboardSensor: vi.fn(),
  PointerSensor: vi.fn(),
  useSensor: vi.fn(),
  useSensors: vi.fn(() => []),
}));

vi.mock("@dnd-kit/sortable", () => ({
  arrayMove: vi.fn((array, from, to) => {
    const result = [...array];
    const [moved] = result.splice(from, 1);
    result.splice(to, 0, moved);
    return result;
  }),
  SortableContext: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  sortableKeyboardCoordinates: vi.fn(),
  useSortable: vi.fn(() => ({
    attributes: {},
    listeners: {},
    setNodeRef: vi.fn(),
    transform: null,
    transition: null,
    isDragging: false,
  })),
  verticalListSortingStrategy: vi.fn(),
}));

vi.mock("@dnd-kit/utilities", () => ({
  CSS: {
    Transform: {
      toString: vi.fn(() => ""),
    },
  },
}));

const mockUseAuth0 = vi.mocked(useAuth0);

// Import mocked API functions
import {
  fetchCategoriesWithTypes,
  createCategory,
  deleteCategory,
  fetchTypeUsage,
} from "../../../lib/api";

const mockFetchCategoriesWithTypes = vi.mocked(fetchCategoriesWithTypes);
const mockCreateCategory = vi.mocked(createCategory);
const mockDeleteCategory = vi.mocked(deleteCategory);
const mockFetchTypeUsage = vi.mocked(fetchTypeUsage);

const mockCategories = [
  {
    id: 1,
    code: "PILLAR",
    name: "Pillar",
    description: "Concrete pillars",
    wiki_url: "https://wiki.example.com/pillar",
    sort_order: 1,
    types: [
      {
        id: 1,
        code: "HOTINE",
        name: "Hotine Pillar",
        description: "Standard Hotine design",
        wiki_url: "https://wiki.example.com/hotine",
        sort_order: 1,
        category_id: 1,
      },
      {
        id: 2,
        code: "VANESSA",
        name: "Vanessa Pillar",
        description: "Vanessa design",
        wiki_url: null,
        sort_order: 2,
        category_id: 1,
      },
    ],
  },
  {
    id: 2,
    code: "BOLT",
    name: "Bolt",
    description: "Surface bolts",
    wiki_url: null,
    sort_order: 2,
    types: [],
  },
];

describe("TypesAdmin", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockUseAuth0.mockReturnValue({
      getAccessTokenSilently: vi.fn().mockResolvedValue("mock-token"),
      user: { name: "Admin User" },
      isAuthenticated: true,
      isLoading: false,
      loginWithRedirect: vi.fn(),
      logout: vi.fn(),
    } as unknown as ReturnType<typeof useAuth0>);
  });

  describe("Loading state", () => {
    it("shows loading spinner while fetching data", async () => {
      mockFetchCategoriesWithTypes.mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      render(<TypesAdmin />);

      expect(screen.getByText(/loading types and categories/i)).toBeInTheDocument();
    });
  });

  describe("Error state", () => {
    it("shows error message when fetch fails", async () => {
      mockFetchCategoriesWithTypes.mockRejectedValue(new Error("Network error"));

      render(<TypesAdmin />);

      await waitFor(() => {
        expect(screen.getByText("Network error")).toBeInTheDocument();
      });

      expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
    });

    it("retries loading when retry button is clicked", async () => {
      mockFetchCategoriesWithTypes
        .mockRejectedValueOnce(new Error("Network error"))
        .mockResolvedValueOnce([]);

      render(<TypesAdmin />);

      await waitFor(() => {
        expect(screen.getByText("Network error")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /retry/i }));

      await waitFor(() => {
        expect(mockFetchCategoriesWithTypes).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe("Success state", () => {
    beforeEach(() => {
      mockFetchCategoriesWithTypes.mockResolvedValue(mockCategories);
    });

    it("renders categories with their types", async () => {
      render(<TypesAdmin />);

      await waitFor(() => {
        expect(screen.getByText("Pillar")).toBeInTheDocument();
      });

      expect(screen.getByText("Bolt")).toBeInTheDocument();
      expect(screen.getByText("(2 types)")).toBeInTheDocument();
      expect(screen.getByText("(0 types)")).toBeInTheDocument();
    });

    it("renders types within expanded categories", async () => {
      render(<TypesAdmin />);

      await waitFor(() => {
        expect(screen.getByText("Hotine Pillar")).toBeInTheDocument();
      });

      expect(screen.getByText("Vanessa Pillar")).toBeInTheDocument();
    });

    it("displays category codes", async () => {
      render(<TypesAdmin />);

      await waitFor(() => {
        expect(screen.getByText("PILLAR")).toBeInTheDocument();
      });

      expect(screen.getByText("BOLT")).toBeInTheDocument();
    });

    it("displays type codes", async () => {
      render(<TypesAdmin />);

      await waitFor(() => {
        expect(screen.getByText(/Code: HOTINE/)).toBeInTheDocument();
      });

      expect(screen.getByText(/Code: VANESSA/)).toBeInTheDocument();
    });

    it("shows empty state message for category with no types", async () => {
      mockFetchCategoriesWithTypes.mockResolvedValue([
        {
          id: 1,
          code: "EMPTY",
          name: "Empty Category",
          description: null,
          wiki_url: null,
          sort_order: 1,
          types: [],
        },
      ]);

      render(<TypesAdmin />);

      await waitFor(() => {
        expect(screen.getByText(/no types in this category/i)).toBeInTheDocument();
      });
    });

    it("shows empty state when no categories exist", async () => {
      mockFetchCategoriesWithTypes.mockResolvedValue([]);

      render(<TypesAdmin />);

      await waitFor(() => {
        expect(
          screen.getByText(/no categories found/i)
        ).toBeInTheDocument();
      });
    });
  });

  describe("Add Category dialog", () => {
    beforeEach(() => {
      mockFetchCategoriesWithTypes.mockResolvedValue(mockCategories);
    });

    it("opens add category dialog when Add Category button is clicked", async () => {
      render(<TypesAdmin />);

      await waitFor(() => {
        expect(screen.getByText("Pillar")).toBeInTheDocument();
      });

      // Click the "Add Category" button in the header
      const addButtons = screen.getAllByRole("button", { name: /add category/i });
      fireEvent.click(addButtons[0]);

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });

      expect(screen.getByLabelText(/code/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^name/i)).toBeInTheDocument();
    });

    it("creates a new category when form is submitted", async () => {
      mockCreateCategory.mockResolvedValue({
        id: 3,
        code: "NEWCAT",
        name: "New Category",
        description: "A new category",
        wiki_url: null,
        sort_order: 3,
      });

      render(<TypesAdmin />);

      await waitFor(() => {
        expect(screen.getByText("Pillar")).toBeInTheDocument();
      });

      // Open dialog
      const addButtons = screen.getAllByRole("button", { name: /add category/i });
      fireEvent.click(addButtons[0]);

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });

      // Fill in the form
      fireEvent.change(screen.getByLabelText(/code/i), {
        target: { value: "NEWCAT" },
      });
      fireEvent.change(screen.getByLabelText(/^name/i), {
        target: { value: "New Category" },
      });

      // Submit
      fireEvent.click(screen.getByRole("button", { name: /create/i }));

      await waitFor(() => {
        expect(mockCreateCategory).toHaveBeenCalled();
      });
    });
  });

  describe("Delete Category", () => {
    beforeEach(() => {
      mockFetchCategoriesWithTypes.mockResolvedValue([
        {
          id: 2,
          code: "BOLT",
          name: "Bolt",
          description: null,
          wiki_url: null,
          sort_order: 2,
          types: [],
        },
      ]);
    });

    it("shows delete confirmation dialog with category details", async () => {
      render(<TypesAdmin />);

      await waitFor(() => {
        expect(screen.getByText("Bolt")).toBeInTheDocument();
      });

      // Find and click delete button for category
      const deleteButtons = screen.getAllByTitle(/delete category/i);
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByRole("alertdialog")).toBeInTheDocument();
      });

      expect(screen.getByText(/delete category/i)).toBeInTheDocument();
    });

    it("deletes category when confirmed", async () => {
      mockDeleteCategory.mockResolvedValue(undefined);

      render(<TypesAdmin />);

      await waitFor(() => {
        expect(screen.getByText("Bolt")).toBeInTheDocument();
      });

      // Click delete button
      const deleteButtons = screen.getAllByTitle(/delete category/i);
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByRole("alertdialog")).toBeInTheDocument();
      });

      // Confirm deletion
      fireEvent.click(screen.getByRole("button", { name: /^delete$/i }));

      await waitFor(() => {
        expect(mockDeleteCategory).toHaveBeenCalledWith(2, "mock-token");
      });
    });
  });

  describe("Delete Type", () => {
    beforeEach(() => {
      mockFetchCategoriesWithTypes.mockResolvedValue(mockCategories);
      mockFetchTypeUsage.mockResolvedValue({
        type_id: 1,
        type_code: "HOTINE",
        type_name: "Hotine Pillar",
        usage_count: 0,
      });
    });

    it("checks type usage before showing delete dialog", async () => {
      render(<TypesAdmin />);

      await waitFor(() => {
        expect(screen.getByText("Hotine Pillar")).toBeInTheDocument();
      });

      // Find and click delete button for type
      const deleteButtons = screen.getAllByTitle(/delete type/i);
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(mockFetchTypeUsage).toHaveBeenCalled();
      });
    });

    it("prevents deletion when type is in use", async () => {
      mockFetchTypeUsage.mockResolvedValue({
        type_id: 1,
        type_code: "HOTINE",
        type_name: "Hotine Pillar",
        usage_count: 5,
      });

      render(<TypesAdmin />);

      await waitFor(() => {
        expect(screen.getByText("Hotine Pillar")).toBeInTheDocument();
      });

      // Click delete button for type
      const deleteButtons = screen.getAllByTitle(/delete type/i);
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByRole("alertdialog")).toBeInTheDocument();
      });

      // Should show warning about type being in use
      expect(screen.getByText(/5 trigpoint/i)).toBeInTheDocument();
    });
  });

  describe("Add Type dialog", () => {
    beforeEach(() => {
      mockFetchCategoriesWithTypes.mockResolvedValue(mockCategories);
    });

    it("opens add type dialog when Add Type button is clicked", async () => {
      render(<TypesAdmin />);

      await waitFor(() => {
        expect(screen.getByText("Pillar")).toBeInTheDocument();
      });

      // Click Add Type button in a category
      const addTypeButtons = screen.getAllByRole("button", { name: /add type/i });
      fireEvent.click(addTypeButtons[0]);

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });

      expect(screen.getByLabelText(/category/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/code/i)).toBeInTheDocument();
    });
  });

  describe("Edit dialogs", () => {
    beforeEach(() => {
      mockFetchCategoriesWithTypes.mockResolvedValue(mockCategories);
    });

    it("opens edit category dialog with pre-filled values", async () => {
      render(<TypesAdmin />);

      await waitFor(() => {
        expect(screen.getByText("Pillar")).toBeInTheDocument();
      });

      // Click edit button for category
      const editButtons = screen.getAllByTitle(/edit category/i);
      fireEvent.click(editButtons[0]);

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });

      // Check pre-filled values
      const codeInput = screen.getByLabelText(/code/i) as HTMLInputElement;
      const nameInput = screen.getByLabelText(/^name/i) as HTMLInputElement;

      expect(codeInput.value).toBe("PILLAR");
      expect(nameInput.value).toBe("Pillar");
    });

    it("opens edit type dialog with pre-filled values", async () => {
      render(<TypesAdmin />);

      await waitFor(() => {
        expect(screen.getByText("Hotine Pillar")).toBeInTheDocument();
      });

      // Click edit button for type
      const editButtons = screen.getAllByTitle(/edit type/i);
      fireEvent.click(editButtons[0]);

      await waitFor(() => {
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });

      // Check pre-filled values
      const codeInput = screen.getByLabelText(/code/i) as HTMLInputElement;
      const nameInput = screen.getByLabelText(/^name/i) as HTMLInputElement;

      expect(codeInput.value).toBe("HOTINE");
      expect(nameInput.value).toBe("Hotine Pillar");
    });
  });

  describe("Wiki links", () => {
    beforeEach(() => {
      mockFetchCategoriesWithTypes.mockResolvedValue(mockCategories);
    });

    it("renders wiki links for categories with wiki_url", async () => {
      render(<TypesAdmin />);

      await waitFor(() => {
        expect(screen.getByText("Pillar")).toBeInTheDocument();
      });

      // Check for external link icons
      const externalLinks = screen.getAllByTestId("icon-external");
      expect(externalLinks.length).toBeGreaterThan(0);
    });
  });

  describe("Page title", () => {
    beforeEach(() => {
      mockFetchCategoriesWithTypes.mockResolvedValue(mockCategories);
    });

    it("displays correct page heading", async () => {
      render(<TypesAdmin />);

      await waitFor(() => {
        expect(screen.getByText("Types & Categories")).toBeInTheDocument();
      });
    });

    it("displays page description", async () => {
      render(<TypesAdmin />);

      await waitFor(() => {
        expect(
          screen.getByText(/manage trigpoint type classifications/i)
        ).toBeInTheDocument();
      });
    });
  });
});
