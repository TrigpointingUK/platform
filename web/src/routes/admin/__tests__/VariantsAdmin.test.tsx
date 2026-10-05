import type { ReactNode } from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent, within } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import VariantsAdmin from "../VariantsAdmin";

vi.mock("@auth0/auth0-react", () => ({
  useAuth0: vi.fn(),
}));

vi.mock("react-hot-toast", () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("lucide-react", () => ({
  Plus: () => <span data-testid="icon-plus">+</span>,
  Pencil: () => <span data-testid="icon-pencil">✏</span>,
  Trash2: () => <span data-testid="icon-trash">🗑</span>,
  X: () => <span data-testid="icon-x">×</span>,
}));

vi.mock("../../../lib/api", () => ({
  fetchVariantGroupsAdmin: vi.fn(),
  createVariant: vi.fn(),
  updateVariant: vi.fn(),
  renameVariantGroup: vi.fn(),
  deleteVariant: vi.fn(),
  requireAccessToken: vi.fn(
    async (
      getAccessTokenSilently: (options?: unknown) => Promise<string | undefined>,
      options?: unknown
    ) => await getAccessTokenSilently(options)
  ),
}));

import toast from "react-hot-toast";
import {
  fetchVariantGroupsAdmin,
  createVariant,
  updateVariant,
  renameVariantGroup,
  deleteVariant,
} from "../../../lib/api";

const mockUseAuth0 = vi.mocked(useAuth0);
const mockFetch = vi.mocked(fetchVariantGroupsAdmin);
const mockCreate = vi.mocked(createVariant);
const mockUpdate = vi.mocked(updateVariant);
const mockRenameGroup = vi.mocked(renameVariantGroup);
const mockDelete = vi.mocked(deleteVariant);

const groups = [
  {
    code: "DETECTOR",
    name: "Detector material",
    type_names: ["Buried Block", "Bolt"],
    variants: [
      { id: 1, code: "CONCRETE_RING", name: "Concrete ring", sort_order: 10, trig_count: 1234 },
      { id: 2, code: "SCRAP_METAL", name: "Scrap metal", sort_order: 20, trig_count: 0 },
    ],
  },
  {
    code: "PILLAR",
    name: "Pillar design",
    type_names: ["Pillar"],
    variants: [{ id: 3, code: "HOTINE", name: "Hotine", sort_order: 10, trig_count: 0 }],
  },
];

function renderPage(queryClient = new QueryClient()) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return render(<VariantsAdmin />, { wrapper });
}

/** The "Add Variant" button on a group's card */
function addButtonFor(groupName: string) {
  const card = screen.getByRole("heading", { name: groupName }).closest("div.p-4") as HTMLElement;
  return within(card).getByRole("button", { name: /add variant/i });
}

describe("VariantsAdmin", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth0.mockReturnValue({
      getAccessTokenSilently: vi.fn().mockResolvedValue("mock-token"),
      isAuthenticated: true,
      isLoading: false,
      loginWithRedirect: vi.fn(),
    } as unknown as ReturnType<typeof useAuth0>);
    mockFetch.mockResolvedValue(groups);
  });

  it("lists the groups with their variants, trig counts and types", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Concrete ring")).toBeInTheDocument();
    });
    expect(screen.getByText("Variants Management")).toBeInTheDocument();
    expect(screen.getByText("Offered by Buried Block, Bolt")).toBeInTheDocument();
    expect(screen.getByText("1,234 trigpoints")).toBeInTheDocument();
    expect(screen.getByText("Hotine")).toBeInTheDocument();
    expect(mockFetch).toHaveBeenCalledWith("mock-token");
  });

  it("adds a variant to a group, deriving its code and order", async () => {
    const queryClient = new QueryClient();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    mockCreate.mockResolvedValue({
      id: 4,
      group_code: "DETECTOR",
      group_name: "Detector material",
      code: "COPPER_RING",
      name: "Copper ring",
      sort_order: 30,
    });
    renderPage(queryClient);

    await waitFor(() => screen.getByText("Concrete ring"));
    fireEvent.click(addButtonFor("Detector material"));
    expect(screen.getByRole("combobox", { name: /group/i })).toHaveValue("DETECTOR");
    fireEvent.change(screen.getByLabelText(/^name/i), { target: { value: "Copper ring" } });
    expect(screen.getByLabelText(/^code/i)).toHaveValue("COPPER_RING");
    expect(screen.getByLabelText(/sort order/i)).toHaveValue(30);
    fireEvent.click(screen.getByRole("button", { name: /create variant/i }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        { group_code: "DETECTOR", code: "COPPER_RING", name: "Copper ring", sort_order: 30 },
        "mock-token"
      );
    });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["reference", "variantGroups"] });
  });

  it("starts a new group", async () => {
    mockCreate.mockResolvedValue({
      id: 5,
      group_code: "BOLT_HEAD",
      group_name: "Bolt head",
      code: "ROUND",
      name: "Round",
      sort_order: 10,
    });
    renderPage();

    await waitFor(() => screen.getByText("Concrete ring"));
    fireEvent.click(addButtonFor("Pillar design"));
    fireEvent.change(screen.getByRole("combobox", { name: /group/i }), { target: { value: "__new__" } });
    fireEvent.change(screen.getByLabelText(/group name/i), { target: { value: "Bolt head" } });
    expect(screen.getByLabelText(/group code/i)).toHaveValue("BOLT_HEAD");
    fireEvent.change(screen.getByLabelText(/^name/i), { target: { value: "Round" } });
    expect(screen.getByLabelText(/sort order/i)).toHaveValue(10);
    fireEvent.click(screen.getByRole("button", { name: /create variant/i }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        {
          group_code: "BOLT_HEAD",
          group_name: "Bolt head",
          code: "ROUND",
          name: "Round",
          sort_order: 10,
        },
        "mock-token"
      );
    });
  });

  it("shows the API's reason when a change is refused", async () => {
    mockCreate.mockRejectedValue(
      new Error('HTTP 400: {"detail":"A variant with code HOTINE already exists"}')
    );
    renderPage();

    await waitFor(() => screen.getByText("Concrete ring"));
    fireEvent.click(addButtonFor("Pillar design"));
    fireEvent.change(screen.getByLabelText(/^name/i), { target: { value: "Hotine" } });
    fireEvent.click(screen.getByRole("button", { name: /create variant/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("A variant with code HOTINE already exists");
    });
  });

  it("renames a variant, keeping its code", async () => {
    mockUpdate.mockResolvedValue({
      id: 1,
      group_code: "DETECTOR",
      group_name: "Detector material",
      code: "CONCRETE_RING",
      name: "Concrete collar",
      sort_order: 10,
    });
    renderPage();

    await waitFor(() => screen.getByText("Concrete ring"));
    fireEvent.click(screen.getByTitle("Edit Concrete ring"));
    expect(screen.getByText(/1,234 trigpoint\(s\) with it will show the new name/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/^name/i), { target: { value: "Concrete collar" } });
    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(mockUpdate).toHaveBeenCalledWith(
        1,
        { name: "Concrete collar", sort_order: 10 },
        "mock-token"
      );
    });
  });

  it("renames a group", async () => {
    mockRenameGroup.mockResolvedValue({ code: "DETECTOR", name: "Detector type" });
    renderPage();

    await waitFor(() => screen.getByText("Concrete ring"));
    fireEvent.click(screen.getByTitle("Rename Detector material"));
    fireEvent.change(screen.getByLabelText(/group name/i), { target: { value: "Detector type" } });
    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(mockRenameGroup).toHaveBeenCalledWith("DETECTOR", "Detector type", "mock-token");
    });
  });

  it("does not offer delete for a variant recorded on trigpoints", async () => {
    renderPage();

    await waitFor(() => screen.getByText("Concrete ring"));
    fireEvent.click(screen.getByTitle("Delete Concrete ring"));

    expect(screen.getByText(/recorded on 1,234 trigpoint\(s\)/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(mockDelete).not.toHaveBeenCalled();
  });

  it("does not offer delete for the last variant of a group types offer", async () => {
    renderPage();

    await waitFor(() => screen.getByText("Hotine"));
    fireEvent.click(screen.getByTitle("Delete Hotine"));

    expect(screen.getByText(/last Pillar design value, and Pillar offer/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(mockDelete).not.toHaveBeenCalled();
  });

  it("deletes an unused variant", async () => {
    mockDelete.mockResolvedValue(undefined);
    renderPage();

    await waitFor(() => screen.getByText("Scrap metal"));
    fireEvent.click(screen.getByTitle("Delete Scrap metal"));
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(mockDelete).toHaveBeenCalledWith(2, "mock-token");
    });
  });
});
