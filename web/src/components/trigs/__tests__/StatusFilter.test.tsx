import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { StatusFilter } from '../StatusFilter';

describe('StatusFilter', () => {
  const mockOnToggle = vi.fn();

  beforeEach(() => {
    mockOnToggle.mockClear();
  });

  describe('rendering', () => {
    it('should render all 6 group toggle buttons', () => {
      render(
        <StatusFilter 
          selectedStatuses={[]} 
          onToggleStatus={mockOnToggle} 
        />
      );

      const buttons = screen.getAllByRole('button');
      expect(buttons).toHaveLength(6);
    });

    it('should render correct icons for each group', () => {
      render(
        <StatusFilter 
          selectedStatuses={[]} 
          onToggleStatus={mockOnToggle} 
        />
      );

      // Check each group has its icon
      expect(screen.getByAltText('Pillar')).toBeInTheDocument();
      expect(screen.getByAltText('FBM')).toBeInTheDocument();
      expect(screen.getByAltText('Survey mark')).toBeInTheDocument();
      expect(screen.getByAltText('Intersected')).toBeInTheDocument();
      expect(screen.getByAltText('Active station')).toBeInTheDocument();
      expect(screen.getByAltText('Other')).toBeInTheDocument();
    });

    it('should have correct aria-labels', () => {
      render(
        <StatusFilter 
          selectedStatuses={[10]} 
          onToggleStatus={mockOnToggle} 
        />
      );

      // Selected button should say "Deselect"
      expect(screen.getByLabelText('Deselect Pillar')).toBeInTheDocument();
      
      // Unselected button should say "Select"
      expect(screen.getByLabelText('Select FBM')).toBeInTheDocument();
    });
  });

  describe('selection state', () => {
    it('should show selected state for selected statuses', () => {
      render(
        <StatusFilter 
          selectedStatuses={[10, 20]} 
          onToggleStatus={mockOnToggle} 
        />
      );

      const pillarButton = screen.getByLabelText('Deselect Pillar');
      const fbmButton = screen.getByLabelText('Deselect FBM');
      const surveyMarkButton = screen.getByLabelText('Select Survey mark');

      // Selected buttons should have aria-pressed="true"
      expect(pillarButton).toHaveAttribute('aria-pressed', 'true');
      expect(fbmButton).toHaveAttribute('aria-pressed', 'true');
      
      // Unselected button should have aria-pressed="false"
      expect(surveyMarkButton).toHaveAttribute('aria-pressed', 'false');
    });

    it('should apply selected styling class', () => {
      render(
        <StatusFilter 
          selectedStatuses={[10]} 
          onToggleStatus={mockOnToggle} 
        />
      );

      const selectedButton = screen.getByLabelText('Deselect Pillar');
      const unselectedButton = screen.getByLabelText('Select FBM');

      // Selected button should have the green background class
      expect(selectedButton.className).toContain('bg-trig-green-600');
      
      // Unselected button should have gray background
      expect(unselectedButton.className).toContain('bg-gray-200');
    });
  });

  describe('click handling', () => {
    it('should call onToggleStatus when button clicked', () => {
      render(
        <StatusFilter 
          selectedStatuses={[]} 
          onToggleStatus={mockOnToggle} 
        />
      );

      const pillarButton = screen.getByLabelText('Select Pillar');
      fireEvent.click(pillarButton);

      expect(mockOnToggle).toHaveBeenCalledTimes(1);
      expect(mockOnToggle).toHaveBeenCalledWith(10); // PILLAR id
    });

    it('should call onToggleStatus with correct id for each button', () => {
      render(
        <StatusFilter 
          selectedStatuses={[]} 
          onToggleStatus={mockOnToggle} 
        />
      );

      // Click FBM button
      fireEvent.click(screen.getByLabelText('Select FBM'));
      expect(mockOnToggle).toHaveBeenLastCalledWith(20);

      // Click Survey mark button
      fireEvent.click(screen.getByLabelText('Select Survey mark'));
      expect(mockOnToggle).toHaveBeenLastCalledWith(30);

      // Click Intersected button
      fireEvent.click(screen.getByLabelText('Select Intersected'));
      expect(mockOnToggle).toHaveBeenLastCalledWith(40);

      // Click Active station button
      fireEvent.click(screen.getByLabelText('Select Active station'));
      expect(mockOnToggle).toHaveBeenLastCalledWith(50);

      // Click Other button
      fireEvent.click(screen.getByLabelText('Select Other'));
      expect(mockOnToggle).toHaveBeenLastCalledWith(60);
    });
  });

  describe('visibleStatuses prop', () => {
    it('should only render specified statuses when visibleStatuses provided', () => {
      render(
        <StatusFilter 
          selectedStatuses={[]} 
          onToggleStatus={mockOnToggle}
          visibleStatuses={[10, 20]} // Only PILLAR and FBM
        />
      );

      const buttons = screen.getAllByRole('button');
      expect(buttons).toHaveLength(2);

      expect(screen.getByAltText('Pillar')).toBeInTheDocument();
      expect(screen.getByAltText('FBM')).toBeInTheDocument();
      expect(screen.queryByAltText('Survey mark')).not.toBeInTheDocument();
    });

    it('should render all statuses when visibleStatuses not provided', () => {
      render(
        <StatusFilter 
          selectedStatuses={[]} 
          onToggleStatus={mockOnToggle}
        />
      );

      const buttons = screen.getAllByRole('button');
      expect(buttons).toHaveLength(6);
    });
  });
});

