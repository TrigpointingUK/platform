import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import LogCard from '../LogCard';

// Create a test query client
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{component}</BrowserRouter>
    </QueryClientProvider>
  );
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
    renderWithProviders(<LogCard log={mockLog} />);
    expect(screen.getByText('TP12345')).toBeInTheDocument();
  });

  it('should render trig name when provided', () => {
    renderWithProviders(<LogCard log={mockLog} trigName="Whitchurch Hill" />);
    expect(screen.getByText('Whitchurch Hill')).toBeInTheDocument();
    // TP12345 should still be shown alongside the trig name
    expect(screen.getByText('TP12345')).toBeInTheDocument();
  });

  it('should render user information', () => {
    renderWithProviders(<LogCard log={mockLog} userName="John Doe" />);
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('should render default user ID when no username provided', () => {
    renderWithProviders(<LogCard log={mockLog} />);
    expect(screen.getByText(/User #100/)).toBeInTheDocument();
  });

  it('should render condition icon with hover text', () => {
    renderWithProviders(<LogCard log={mockLog} />);
    // The condition is now displayed as an icon with title attribute
    const conditionIcon = screen.getByTitle('Good');
    expect(conditionIcon).toBeInTheDocument();
    expect(conditionIcon).toHaveAttribute('src', '/icons/conditions/c_good.png');
  });

  it('should render score out of 10', () => {
    renderWithProviders(<LogCard log={mockLog} />);
    // Score is 4, displayed as stars with a title attribute of "4/10"
    const starContainer = screen.getByTitle('4/10');
    expect(starContainer).toBeInTheDocument();
  });

  it('should render formatted date', () => {
    renderWithProviders(<LogCard log={mockLog} />);
    expect(screen.getByText('15 Jan 2024')).toBeInTheDocument();
  });

  it('should render time', () => {
    renderWithProviders(<LogCard log={mockLog} />);
    expect(screen.getByText('14:30')).toBeInTheDocument();
  });

  it('should render comment when present', () => {
    renderWithProviders(<LogCard log={mockLog} />);
    expect(screen.getByText('Great condition, easy to find')).toBeInTheDocument();
  });

  it('should not render comment section when comment is empty', () => {
    const logWithoutComment = { ...mockLog, comment: '' };
    renderWithProviders(<LogCard log={logWithoutComment} />);
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
    renderWithProviders(<LogCard log={logWithPhotos} />);
    
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
    renderWithProviders(<LogCard log={logWithManyPhotos} />);
    
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
      const { unmount } = renderWithProviders(
        <LogCard log={{ ...mockLog, condition: code }} />
      );
      const conditionIcon = screen.getByTitle(label);
      expect(conditionIcon).toBeInTheDocument();
      expect(conditionIcon).toHaveAttribute('src', `/icons/conditions/${icon}`);
      unmount();
    });
  });

  it('should render links to trig and user pages', () => {
    renderWithProviders(<LogCard log={mockLog} />);
    
    const links = screen.getAllByRole('link');
    const trigLink = links.find(link => link.getAttribute('href') === '/trigs/12345');
    const userLink = links.find(link => link.getAttribute('href') === '/profile/100');
    
    expect(trigLink).toBeInTheDocument();
    expect(userLink).toBeInTheDocument();
  });

  it('should hide trig info when showTrigInfo is false', () => {
    renderWithProviders(<LogCard log={mockLog} showTrigInfo={false} />);
    
    // Trig ID should not be rendered
    expect(screen.queryByText('TP12345')).not.toBeInTheDocument();
    
    // Trig link should not exist
    const links = screen.getAllByRole('link');
    const trigLink = links.find(link => link.getAttribute('href') === '/trigs/12345');
    expect(trigLink).toBeUndefined();
    
    // User link should still exist
    const userLink = links.find(link => link.getAttribute('href') === '/profile/100');
    expect(userLink).toBeInTheDocument();
  });

  it('should show trig info by default', () => {
    renderWithProviders(<LogCard log={mockLog} />);
    
    // Trig ID should be rendered
    expect(screen.getByText('TP12345')).toBeInTheDocument();
    
    // Trig link should exist
    const links = screen.getAllByRole('link');
    const trigLink = links.find(link => link.getAttribute('href') === '/trigs/12345');
    expect(trigLink).toBeInTheDocument();
  });

  describe('avatar image', () => {
    it('should render an avatar img with the correct S3 URL based on user_id', () => {
      renderWithProviders(<LogCard log={mockLog} />);

      const avatarImg = document.querySelector(
        'img[src*="trigpointinguk-avatars.s3.amazonaws.com"]'
      ) as HTMLImageElement;
      expect(avatarImg).not.toBeNull();
      expect(avatarImg.src).toContain('U00100.jpg');
    });

    it('should zero-pad user_id to 5 digits in the avatar URL', () => {
      const logWithSmallId = { ...mockLog, user_id: 7 };
      renderWithProviders(<LogCard log={logWithSmallId} />);

      const avatarImg = document.querySelector(
        'img[src*="trigpointinguk-avatars"]'
      ) as HTMLImageElement;
      expect(avatarImg.src).toContain('U00007.jpg');
    });

    it('should render the avatar img as hidden initially', () => {
      renderWithProviders(<LogCard log={mockLog} />);

      const avatarImg = document.querySelector(
        'img[src*="trigpointinguk-avatars"]'
      ) as HTMLImageElement;
      expect(avatarImg.classList.contains('hidden')).toBe(true);
    });

    it('should remove hidden class on successful image load', () => {
      renderWithProviders(<LogCard log={mockLog} />);

      const avatarImg = document.querySelector(
        'img[src*="trigpointinguk-avatars"]'
      ) as HTMLImageElement;
      avatarImg.dispatchEvent(new Event('load'));
      expect(avatarImg.classList.contains('hidden')).toBe(false);
    });

    it('should add hidden class back on image load error', () => {
      renderWithProviders(<LogCard log={mockLog} />);

      const avatarImg = document.querySelector(
        'img[src*="trigpointinguk-avatars"]'
      ) as HTMLImageElement;
      // Simulate successful load then error (e.g. re-render with invalid URL)
      avatarImg.dispatchEvent(new Event('load'));
      expect(avatarImg.classList.contains('hidden')).toBe(false);

      avatarImg.dispatchEvent(new Event('error'));
      expect(avatarImg.classList.contains('hidden')).toBe(true);
    });

    it('should have empty alt text for the avatar (decorative)', () => {
      renderWithProviders(<LogCard log={mockLog} />);

      const avatarImg = document.querySelector(
        'img[src*="trigpointinguk-avatars"]'
      ) as HTMLImageElement;
      expect(avatarImg.alt).toBe('');
    });
  });
});

