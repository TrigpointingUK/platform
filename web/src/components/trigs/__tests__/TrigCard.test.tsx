import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { TrigCard } from '../TrigCard';

// Wrapper to provide router context
const renderWithRouter = (ui: React.ReactElement) => {
  return render(ui, { wrapper: BrowserRouter });
};

const baseTrig = {
  id: 1,
  waypoint: 'TP0001',
  name: 'Test Trigpoint',
  physical_type: 'Pillar',
  condition: 'G',
  wgs_lat: '51.5074',
  wgs_long: '-0.1278',
  osgb_gridref: 'TQ 30000 80000',
};

describe('TrigCard', () => {
  describe('basic rendering', () => {
    it('should render trig name', () => {
      renderWithRouter(<TrigCard trig={baseTrig} />);
      
      expect(screen.getByText('Test Trigpoint')).toBeInTheDocument();
    });

    it('should render grid reference', () => {
      renderWithRouter(<TrigCard trig={baseTrig} />);
      
      expect(screen.getByText('TQ 30000 80000')).toBeInTheDocument();
    });

    it('should link to trig detail page', () => {
      renderWithRouter(<TrigCard trig={baseTrig} />);
      
      const link = screen.getByRole('link');
      expect(link).toHaveAttribute('href', '/trigs/1');
    });
  });

  describe('category_code icon rendering', () => {
    it('should render PILLAR category icon', () => {
      const trig = { ...baseTrig, category_code: 'PILLAR' };
      renderWithRouter(<TrigCard trig={trig} />);
      
      // Icon uses abbrev as alt and full name as title
      const icon = screen.getByTitle('Pillar');
      expect(icon).toHaveAttribute('src', '/icons/t_pillar.png');
    });

    it('should render FBM category icon', () => {
      const trig = { ...baseTrig, category_code: 'FBM' };
      renderWithRouter(<TrigCard trig={trig} />);
      
      const icon = screen.getByTitle('FBM');
      expect(icon).toHaveAttribute('src', '/icons/t_fbm.png');
    });

    it('should render SURVEY_MARK category icon', () => {
      const trig = { ...baseTrig, category_code: 'SURVEY_MARK' };
      renderWithRouter(<TrigCard trig={trig} />);
      
      const icon = screen.getByTitle('Survey mark');
      expect(icon).toHaveAttribute('src', '/icons/t_passive.png');
    });

    it('should render INTERSECTED category icon', () => {
      const trig = { ...baseTrig, category_code: 'INTERSECTED' };
      renderWithRouter(<TrigCard trig={trig} />);
      
      const icon = screen.getByTitle('Intersected');
      expect(icon).toHaveAttribute('src', '/icons/t_intersected.png');
    });

    it('should render ACTIVE category icon', () => {
      const trig = { ...baseTrig, category_code: 'ACTIVE' };
      renderWithRouter(<TrigCard trig={trig} />);
      
      const icon = screen.getByTitle('Active station');
      expect(icon).toHaveAttribute('src', '/icons/t_active.png');
    });

    it('should render OTHER category icon', () => {
      const trig = { ...baseTrig, category_code: 'OTHER' };
      renderWithRouter(<TrigCard trig={trig} />);
      
      const icon = screen.getByTitle('Other');
      expect(icon).toHaveAttribute('src', '/icons/t_other.svg');
    });

    it('should render fallback for unknown category', () => {
      const trig = { ...baseTrig, category_code: 'UNKNOWN' };
      renderWithRouter(<TrigCard trig={trig} />);
      
      // Unknown category shows "?" badge instead of icon
      expect(screen.getByText('?')).toBeInTheDocument();
    });

    it('should render fallback when category_code is undefined', () => {
      const trig = { ...baseTrig };
      renderWithRouter(<TrigCard trig={trig} />);
      
      // No category_code shows "?" badge
      expect(screen.getByText('?')).toBeInTheDocument();
    });
  });

  describe('condition rendering', () => {
    it('should render Good condition icon', () => {
      const trig = { ...baseTrig, condition: 'G' };
      renderWithRouter(<TrigCard trig={trig} />);
      
      const conditionIcon = screen.getByAltText('Good');
      expect(conditionIcon).toBeInTheDocument();
    });

    it('should render Damaged condition icon', () => {
      const trig = { ...baseTrig, condition: 'D' };
      renderWithRouter(<TrigCard trig={trig} />);
      
      const conditionIcon = screen.getByAltText('Damaged');
      expect(conditionIcon).toBeInTheDocument();
    });
  });

  describe('distance display', () => {
    it('should show distance when provided', () => {
      const trig = { ...baseTrig, distance_km: 5.5 };
      renderWithRouter(<TrigCard trig={trig} showDistance={true} />);
      
      expect(screen.getByText(/5.5/)).toBeInTheDocument();
    });

    it('should hide distance when showDistance is false', () => {
      const trig = { ...baseTrig, distance_km: 5.5 };
      renderWithRouter(<TrigCard trig={trig} showDistance={false} />);
      
      // Distance should not be in the document
      // (the card still renders but without distance display)
      expect(screen.queryByText(/km$/)).not.toBeInTheDocument();
    });

    it('should show bearing arrow when center coordinates provided', () => {
      const trig = { ...baseTrig, distance_km: 5.5 };
      renderWithRouter(
        <TrigCard 
          trig={trig} 
          showDistance={true} 
          centerLat={51.4} 
          centerLon={-0.1} 
        />
      );
      
      // The DirectionArrow component shows bearing in title
      const arrowContainer = screen.getByTitle(/Bearing:/);
      expect(arrowContainer).toBeInTheDocument();
      
      // Should contain an SVG
      const svg = arrowContainer.querySelector('svg');
      expect(svg).toBeInTheDocument();
    });
  });
});

