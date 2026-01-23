import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import Textarea from '../Textarea';

describe('Textarea', () => {
  it('should render a textarea element', () => {
    render(<Textarea data-testid="test-textarea" />);
    expect(screen.getByTestId('test-textarea')).toBeInTheDocument();
  });

  it('should accept and display value', () => {
    render(<Textarea defaultValue="test value" />);
    expect(screen.getByDisplayValue('test value')).toBeInTheDocument();
  });

  it('should call onChange when value changes', () => {
    const handleChange = vi.fn();
    render(<Textarea onChange={handleChange} />);

    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: 'new value' } });

    expect(handleChange).toHaveBeenCalled();
  });

  it('should apply custom className', () => {
    render(<Textarea className="custom-class" data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveClass('custom-class');
  });

  it('should be disabled when disabled prop is true', () => {
    render(<Textarea disabled data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toBeDisabled();
  });

  it('should accept placeholder text', () => {
    render(<Textarea placeholder="Enter text here" />);
    expect(screen.getByPlaceholderText('Enter text here')).toBeInTheDocument();
  });

  it('should support rows attribute', () => {
    render(<Textarea rows={5} data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveAttribute('rows', '5');
  });

  it('should be focusable', () => {
    render(<Textarea data-testid="textarea" />);
    const textarea = screen.getByTestId('textarea');

    textarea.focus();
    expect(textarea).toHaveFocus();
  });

  it('should support maxLength', () => {
    render(<Textarea maxLength={500} data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveAttribute('maxLength', '500');
  });

  it('should support required attribute', () => {
    render(<Textarea required data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toBeRequired();
  });

  it('should handle multiline input', () => {
    const handleChange = vi.fn();
    render(<Textarea onChange={handleChange} />);

    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: 'Line 1\nLine 2\nLine 3' } });

    expect(handleChange).toHaveBeenCalled();
  });

  it('should forward ref correctly', () => {
    const ref = vi.fn();
    render(<Textarea ref={ref} />);
    expect(ref).toHaveBeenCalled();
  });

  it('should apply error styling when error prop is true', () => {
    render(<Textarea error data-testid="textarea" />);
    expect(screen.getByTestId('textarea')).toHaveClass('border-red-500');
  });
});
