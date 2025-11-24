import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { BrowserRouter } from 'react-router-dom';
import LogCard from '../LogCard';

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('LogCard', () => {
  const mockLog = {
    id: 1,
    trig_id: 12345,
    user_id: 100,
    date: '2024-01-15',
    time: '14:30',
    condition: 'G',
    comment: 'Great condition, easy to find',
    score: 4,
  };

  it('should render trig ID as TP format', () => {
    renderWithRouter(<LogCard log={mockLog} />);
    expect(screen.getByText('TP12345')).toBeInTheDocument();
  });

  it('should render trig name when provided', () => {
    renderWithRouter(<LogCard log={mockLog} trigName="Whitchurch Hill" />);
    expect(screen.getByText('Whitchurch Hill')).toBeInTheDocument();
    // TP12345 should still be shown alongside the trig name
    expect(screen.getByText('TP12345')).toBeInTheDocument();
  });

  it('should render user information', () => {
    renderWithRouter(<LogCard log={mockLog} userName="John Doe" />);
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('should render default user ID when no username provided', () => {
    renderWithRouter(<LogCard log={mockLog} />);
    expect(screen.getByText(/User #100/)).toBeInTheDocument();
  });

  it('should render condition icon with hover text', () => {
    renderWithRouter(<LogCard log={mockLog} />);
    // The condition is now displayed as an icon with title attribute
    const conditionIcon = screen.getByTitle('Good');
    expect(conditionIcon).toBeInTheDocument();
    expect(conditionIcon).toHaveAttribute('src', '/icons/conditions/c_good.png');
  });

  it('should render score out of 10', () => {
    renderWithRouter(<LogCard log={mockLog} />);
    // Score is 4, displayed as stars with a title attribute of "4/10"
    const starContainer = screen.getByTitle('4/10');
    expect(starContainer).toBeInTheDocument();
  });

  it('should render formatted date', () => {
    renderWithRouter(<LogCard log={mockLog} />);
    expect(screen.getByText('15 Jan 2024')).toBeInTheDocument();
  });

  it('should render time', () => {
    renderWithRouter(<LogCard log={mockLog} />);
    expect(screen.getByText('14:30')).toBeInTheDocument();
  });

  it('should render comment when present', () => {
    renderWithRouter(<LogCard log={mockLog} />);
    expect(screen.getByText('Great condition, easy to find')).toBeInTheDocument();
  });

  it('should not render comment section when comment is empty', () => {
    const logWithoutComment = { ...mockLog, comment: '' };
    renderWithRouter(<LogCard log={logWithoutComment} />);
    expect(screen.queryByText('Great condition, easy to find')).not.toBeInTheDocument();
  });

  it('should render photos when present', () => {
    const logWithPhotos = {
      ...mockLog,
      photos: [
        {
          id: 1,
          log_id: 1,
          user_id: 100,
          icon_url: 'photo1.jpg',
          photo_url: 'photo1_full.jpg',
          caption: 'Photo 1',
          type: 'T',
          filesize: 1024000,
          height: 1200,
          width: 1600,
          icon_filesize: 10240,
          icon_height: 150,
          icon_width: 200,
          text_desc: 'Test photo 1',
          license: 'Y',
        },
        {
          id: 2,
          log_id: 1,
          user_id: 100,
          icon_url: 'photo2.jpg',
          photo_url: 'photo2_full.jpg',
          caption: 'Photo 2',
          type: 'L',
          filesize: 2048000,
          height: 1200,
          width: 1600,
          icon_filesize: 10240,
          icon_height: 150,
          icon_width: 200,
          text_desc: 'Test photo 2',
          license: 'Y',
        },
      ],
    };
    renderWithRouter(<LogCard log={logWithPhotos} />);
    
    const images = screen.getAllByRole('img');
    // 1 condition icon + 2 photos = 3 images total
    expect(images).toHaveLength(3);
    // Check the photo images (skip the first one which is the condition icon)
    const photoImages = images.slice(1);
    expect(photoImages[0]).toHaveAttribute('src', 'photo1.jpg');
    expect(photoImages[1]).toHaveAttribute('src', 'photo2.jpg');
  });

  it('should show +X indicator when more than 20 photos', () => {
    const photos = Array.from({ length: 25 }, (_, i) => ({
      id: i + 1,
      log_id: 1,
      user_id: 100,
      icon_url: `photo${i + 1}.jpg`,
      photo_url: `photo${i + 1}_full.jpg`,
      caption: `Photo ${i + 1}`,
      type: 'T',
      filesize: 1024000,
      height: 1200,
      width: 1600,
      icon_filesize: 10240,
      icon_height: 150,
      icon_width: 200,
      text_desc: `Test photo ${i + 1}`,
      license: 'Y',
    }));
    
    const logWithManyPhotos = { ...mockLog, photos };
    renderWithRouter(<LogCard log={logWithManyPhotos} />);
    
    expect(screen.getByText('+5')).toBeInTheDocument();
  });

  it('should handle different condition codes', () => {
    const conditions = [
      { code: 'G', label: 'Good', icon: 'c_good.png' },
      { code: 'S', label: 'Slightly Damaged', icon: 'c_slightlydamaged.png' },
      { code: 'D', label: 'Damaged', icon: 'c_damaged.png' },
      { code: 'M', label: 'Moved', icon: 'c_toppled.png' },
      { code: 'Q', label: 'Possibly Missing', icon: 'c_possiblymissing.png' },
      { code: 'P', label: 'Inaccessible', icon: 'c_unknown.png' },
      { code: 'U', label: 'Unknown', icon: 'c_unknown.png' },
      { code: 'X', label: 'Destroyed', icon: 'c_definitelymissing.png' },
    ];

    conditions.forEach(({ code, label, icon }) => {
      const { unmount } = renderWithRouter(
        <LogCard log={{ ...mockLog, condition: code }} />
      );
      const conditionIcon = screen.getByTitle(label);
      expect(conditionIcon).toBeInTheDocument();
      expect(conditionIcon).toHaveAttribute('src', `/icons/conditions/${icon}`);
      unmount();
    });
  });

  it('should render links to trig and user pages', () => {
    renderWithRouter(<LogCard log={mockLog} />);
    
    const links = screen.getAllByRole('link');
    const trigLink = links.find(link => link.getAttribute('href') === '/trigs/12345');
    const userLink = links.find(link => link.getAttribute('href') === '/profile/100');
    
    expect(trigLink).toBeInTheDocument();
    expect(userLink).toBeInTheDocument();
  });
});

