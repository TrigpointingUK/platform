import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import Label from '../Label';

describe('Label', () => {
  it('should render label text', () => {
    render(<Label>Test Label</Label>);
    expect(screen.getByText('Test Label')).toBeInTheDocument();
  });

  it('should associate with input via htmlFor', () => {
    render(
      <>
        <Label htmlFor="test-input">Label Text</Label>
        <input id="test-input" />
      </>
    );

    const label = screen.getByText('Label Text');
    expect(label).toHaveAttribute('for', 'test-input');
  });

  it('should apply custom className', () => {
    render(<Label className="custom-class">Label</Label>);
    expect(screen.getByText('Label')).toHaveClass('custom-class');
  });

  it('should render as a label element', () => {
    render(<Label>Label Text</Label>);
    const label = screen.getByText('Label Text');
    expect(label.tagName).toBe('LABEL');
  });

  it('should apply default styling classes', () => {
    render(<Label>Styled Label</Label>);
    const label = screen.getByText('Styled Label');
    expect(label).toHaveClass('text-sm');
    expect(label).toHaveClass('font-medium');
  });

  it('should support nested content', () => {
    render(
      <Label>
        <span>Nested</span> Content
      </Label>
    );
    expect(screen.getByText('Nested')).toBeInTheDocument();
    expect(screen.getByText(/Content/)).toBeInTheDocument();
  });

  it('should show required indicator when required prop is true', () => {
    render(<Label required>Required Label</Label>);
    expect(screen.getByText('*')).toBeInTheDocument();
  });
});
