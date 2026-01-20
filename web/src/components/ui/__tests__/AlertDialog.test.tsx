import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import AlertDialog from '../AlertDialog';

describe('AlertDialog', () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    title: 'Test Title',
    description: 'Test Description',
    onConfirm: vi.fn(),
  };

  it('should not render content when closed', () => {
    render(<AlertDialog {...defaultProps} open={false} />);
    expect(screen.queryByText('Test Title')).not.toBeInTheDocument();
  });

  it('should render content when open', () => {
    render(<AlertDialog {...defaultProps} />);
    expect(screen.getByText('Test Title')).toBeInTheDocument();
    expect(screen.getByText('Test Description')).toBeInTheDocument();
  });

  it('should render default button text', () => {
    render(<AlertDialog {...defaultProps} />);
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument();
  });

  it('should render custom button text', () => {
    render(
      <AlertDialog
        {...defaultProps}
        cancelText="No"
        confirmText="Yes"
      />
    );
    expect(screen.getByRole('button', { name: 'No' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Yes' })).toBeInTheDocument();
  });

  it('should call onOpenChange with false when cancel is clicked', () => {
    const handleOpenChange = vi.fn();
    render(
      <AlertDialog {...defaultProps} onOpenChange={handleOpenChange} />
    );

    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(handleOpenChange).toHaveBeenCalledWith(false);
  });

  it('should call onConfirm when confirm is clicked', () => {
    const handleConfirm = vi.fn();
    render(<AlertDialog {...defaultProps} onConfirm={handleConfirm} />);

    fireEvent.click(screen.getByRole('button', { name: /confirm/i }));
    expect(handleConfirm).toHaveBeenCalled();
  });

  it('should close on escape key', () => {
    const handleOpenChange = vi.fn();
    render(
      <AlertDialog {...defaultProps} onOpenChange={handleOpenChange} />
    );

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(handleOpenChange).toHaveBeenCalledWith(false);
  });

  it('should have alertdialog role', () => {
    render(<AlertDialog {...defaultProps} />);
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
  });

  it('should disable confirm button when confirmDisabled is true', () => {
    render(<AlertDialog {...defaultProps} confirmDisabled />);
    expect(screen.getByRole('button', { name: /confirm/i })).toBeDisabled();
  });

  it('should close dialog on backdrop click', () => {
    const handleOpenChange = vi.fn();
    render(
      <AlertDialog {...defaultProps} onOpenChange={handleOpenChange} />
    );

    // Click on the backdrop (the outer container)
    const backdrop = document.querySelector('.fixed.inset-0.z-50');
    if (backdrop) {
      fireEvent.click(backdrop);
      expect(handleOpenChange).toHaveBeenCalledWith(false);
    }
  });
});
