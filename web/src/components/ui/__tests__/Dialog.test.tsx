import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../Dialog';

// Mock lucide-react
vi.mock('lucide-react', () => ({
  X: () => <span data-testid="x-icon">×</span>,
}));

describe('Dialog', () => {
  it('should not render content when closed', () => {
    render(
      <Dialog open={false} onOpenChange={() => {}}>
        <DialogContent>
          <DialogTitle>Test Title</DialogTitle>
        </DialogContent>
      </Dialog>
    );

    expect(screen.queryByText('Test Title')).not.toBeInTheDocument();
  });

  it('should render content when open', () => {
    render(
      <Dialog open={true} onOpenChange={() => {}}>
        <DialogContent>
          <DialogTitle>Test Title</DialogTitle>
        </DialogContent>
      </Dialog>
    );

    expect(screen.getByText('Test Title')).toBeInTheDocument();
  });

  it('should call onOpenChange when close button is clicked', () => {
    const handleOpenChange = vi.fn();

    render(
      <Dialog open={true} onOpenChange={handleOpenChange}>
        <DialogContent>
          <DialogTitle>Test Title</DialogTitle>
        </DialogContent>
      </Dialog>
    );

    // Find the close button (the X button in the dialog)
    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);

    expect(handleOpenChange).toHaveBeenCalledWith(false);
  });

  it('should render DialogHeader with correct styling', () => {
    render(
      <Dialog open={true} onOpenChange={() => {}}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Header Title</DialogTitle>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    );

    expect(screen.getByText('Header Title')).toBeInTheDocument();
  });

  it('should render DialogDescription', () => {
    render(
      <Dialog open={true} onOpenChange={() => {}}>
        <DialogContent>
          <DialogTitle>Title</DialogTitle>
          <DialogDescription>This is a description</DialogDescription>
        </DialogContent>
      </Dialog>
    );

    expect(screen.getByText('This is a description')).toBeInTheDocument();
  });

  it('should render DialogFooter with children', () => {
    render(
      <Dialog open={true} onOpenChange={() => {}}>
        <DialogContent>
          <DialogTitle>Title</DialogTitle>
          <DialogFooter>
            <button>Save</button>
            <button>Cancel</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );

    expect(screen.getByText('Save')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('should apply custom className to DialogContent', () => {
    render(
      <Dialog open={true} onOpenChange={() => {}}>
        <DialogContent className="custom-content-class">
          <DialogTitle>Title</DialogTitle>
        </DialogContent>
      </Dialog>
    );

    // The content should have the custom class
    const content = screen.getByRole('dialog');
    expect(content).toHaveClass('custom-content-class');
  });

  it('should close on escape key when open', () => {
    const handleOpenChange = vi.fn();

    render(
      <Dialog open={true} onOpenChange={handleOpenChange}>
        <DialogContent>
          <DialogTitle>Title</DialogTitle>
        </DialogContent>
      </Dialog>
    );

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(handleOpenChange).toHaveBeenCalledWith(false);
  });

  it('should have dialog role', () => {
    render(
      <Dialog open={true} onOpenChange={() => {}}>
        <DialogContent>
          <DialogTitle>Title</DialogTitle>
        </DialogContent>
      </Dialog>
    );

    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('should render close button', () => {
    render(
      <Dialog open={true} onOpenChange={() => {}}>
        <DialogContent>
          <DialogTitle>Title</DialogTitle>
        </DialogContent>
      </Dialog>
    );

    expect(screen.getByRole('button', { name: /close/i })).toBeInTheDocument();
  });
});
