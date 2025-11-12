import { useEffect, useRef } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import toast from 'react-hot-toast';
import PhotoSwipe from 'photoswipe';
import type { Photo } from '../lib/api';
import { rotatePhoto } from '../lib/api';

export interface PhotoSwipeOptions {
  photos: Photo[];
  initialIndex?: number;
  onClose?: () => void;
  onPhotoRotated?: (updatedPhoto: Photo) => void;
}

// Helper function to create metadata overlay HTML
function createMetadataOverlay(photo: Photo): string {
  const photoTypes: Record<string, string> = {
    'T': 'Trigpoint',
    'F': 'Flush Bracket',
    'L': 'Landscape',
    'P': 'People',
    'O': 'Other',
  };

  const licenses: Record<string, string> = {
    'Y': 'Public Domain',
    'C': 'Creative Commons',
    'N': 'Private',
  };

  const typeLabel = photoTypes[photo.type] || photo.type;
  const licenseLabel = licenses[photo.license] || photo.license;
  const filesize = (photo.filesize / 1024).toFixed(0); // Convert to KB
  
  // Format waypoint as TPxxxx with minimum 4 digits
  // Check for null/undefined, not falsy (to allow trig_id = 0)
  const waypoint = photo.trig_id != null ? `TP${String(photo.trig_id).padStart(4, '0')}` : null;
  
  // Format date if available
  const formattedDate = photo.log_date ? new Date(photo.log_date).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  }) : null;

  return `
    <div class="pswp__custom-caption">
      <div class="pswp__caption-content">
        <h3 class="pswp__caption-title">${photo.caption || 'Untitled'}</h3>
        ${photo.text_desc ? `<p class="pswp__caption-desc">${photo.text_desc}</p>` : ''}
        ${waypoint && photo.trig_name ? `<div class="pswp__caption-location">${waypoint} · ${photo.trig_name}</div>` : ''}
        ${photo.user_name ? `<div class="pswp__caption-user">By ${photo.user_name}</div>` : ''}
        ${formattedDate ? `<div class="pswp__caption-date">${formattedDate}</div>` : ''}
        <div class="pswp__caption-meta">
          ${photo.type !== 'X' ? '<span class="pswp__caption-meta-item">Type: ' + typeLabel + '</span>' : ''}
          ${licenseLabel !== undefined ? '<span class="pswp__caption-meta-item">License: ' + licenseLabel + '</span>' : ''}
          <span class="pswp__caption-meta-item">${photo.width}×${photo.height}px</span>
          <span class="pswp__caption-meta-item">${filesize} KB</span>
        </div>
        <div class="pswp__caption-links">
          <a href="/logs/${photo.log_id}" class="pswp__caption-link">View Log</a>
          <a href="/profile/${photo.user_id}" class="pswp__caption-link">View User</a>
          ${photo.trig_id != null ? '<a href="/trigs/' + photo.trig_id + '" class="pswp__caption-link">View Trig</a>' : ''}
        </div>
      </div>
    </div>
  `;
}

export function usePhotoSwipe({ photos, initialIndex = 0, onClose, onPhotoRotated }: PhotoSwipeOptions) {
  const pswpRef = useRef<PhotoSwipe | null>(null);
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();

  useEffect(() => {
    if (photos.length === 0) return;

    // Convert Photo objects to PhotoSwipe data source format
    const dataSource = photos.map((photo) => ({
      src: photo.photo_url,
      width: photo.width,
      height: photo.height,
      alt: photo.caption,
      // Store the full photo object for metadata display
      photo: photo,
    }));

    // PhotoSwipe options
    const options = {
      dataSource,
      index: initialIndex,
      
      // Zoom configuration
      maxZoomLevel: 4, // 400% max zoom
      initialZoomLevel: 'fit' as const, // Start with image fitted to screen (shows full image)
      secondaryZoomLevel: 1, // Double-click zooms to 1:1 (actual pixels)
      
      // UI configuration
      padding: { top: 50, bottom: 120, left: 20, right: 20 }, // Extra bottom padding for metadata
      bgOpacity: 0.9,
      
      // Show navigation UI only when there are multiple photos
      zoom: true,
      close: true,
      counter: photos.length > 1, // Show counter only with multiple photos
      arrowPrev: photos.length > 1, // Show prev arrow only with multiple photos
      arrowNext: photos.length > 1, // Show next arrow only with multiple photos
      
      // Click/tap behavior
      clickToCloseNonZoomable: true,
      tapAction: 'close' as const, // Single tap/click closes the viewer when not zoomed
      doubleTapAction: 'zoom' as const, // Double-click/tap to zoom
      
      // Mouse wheel zoom
      wheelToZoom: true,
      
      // Keyboard shortcuts
      keyboard: true,
      
      // Pinch to zoom on mobile
      pinchToClose: false,
      
      // Animation
      showHideAnimationType: 'zoom' as const, // Zoom animation on open/close
      
      // Allow panning/swiping to next photo only when there are multiple photos
      allowPanToNext: photos.length > 1,
      
      // Prevent closing when clicking outside if zoomed
      closeOnVerticalDrag: true,
    };

    // Create and open PhotoSwipe
    const pswp = new PhotoSwipe(options);
    pswpRef.current = pswp;

    // Add custom metadata overlay
    pswp.on('uiRegister', () => {
      pswp.ui?.registerElement({
        name: 'custom-caption',
        order: 9,
        isButton: false,
        appendTo: 'root',
        html: '',
        onInit: (el: HTMLElement) => {
          pswp.on('change', () => {
            const currSlideElement = pswp.currSlide?.data;
            if (currSlideElement && 'photo' in currSlideElement) {
              el.innerHTML = createMetadataOverlay(currSlideElement.photo as Photo);
            }
          });
        },
      });

      // Add rotation buttons (only if user is logged in)
      if (isAuthenticated) {
        pswp.ui?.registerElement({
          name: 'rotate-left-button',
          order: 8,
          isButton: true,
          appendTo: 'bar',
          html: `
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="pswp__icn"
              width="32"
              height="32"
              viewBox="0 0 32 32"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                fill="none"
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M4 13.33h13.33a10.67 10.67 0 0110.67 10.67v2.67M4 13.33l8 8m-8-8l8-8"
              />
            </svg>
          `,
          onInit: (el: HTMLElement, pswp: PhotoSwipe) => {
            el.setAttribute('title', 'Rotate left 90°');
            el.onclick = async () => {
              const currSlideData = pswp.currSlide?.data;
              if (currSlideData && 'photo' in currSlideData) {
                const photo = currSlideData.photo as Photo;
                try {
                  const token = await getAccessTokenSilently();
                  const updatedPhoto = await rotatePhoto(photo.id, 270, token);
                  
                  toast.success('Photo rotated successfully');
                  
                  // Update the current slide with the new photo URL
                  if (pswp.currSlide) {
                    pswp.currSlide.data.src = updatedPhoto.photo_url;
                    pswp.currSlide.data.width = updatedPhoto.width;
                    pswp.currSlide.data.height = updatedPhoto.height;
                    (pswp.currSlide.data as { photo: Photo }).photo = updatedPhoto;
                    
                    // Force PhotoSwipe to reload the image
                    pswp.refreshSlideContent(pswp.currSlide.index);
                  }
                  
                  // Call the callback if provided
                  if (onPhotoRotated) {
                    onPhotoRotated(updatedPhoto);
                  }
                } catch (error) {
                  console.error('Failed to rotate photo:', error);
                  toast.error('Failed to rotate photo. Please try again.');
                }
              }
            };
          },
        });

        pswp.ui?.registerElement({
          name: 'rotate-right-button',
          order: 9,
          isButton: true,
          appendTo: 'bar',
          html: `
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="pswp__icn"
              width="32"
              height="32"
              viewBox="0 0 32 32"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                fill="none"
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M28 13.33H14.67a10.67 10.67 0 00-10.67 10.67v2.67M28 13.33l-8 8m8-8l-8-8"
              />
            </svg>
          `,
          onInit: (el: HTMLElement, pswp: PhotoSwipe) => {
            el.setAttribute('title', 'Rotate right 90°');
            el.onclick = async () => {
              const currSlideData = pswp.currSlide?.data;
              if (currSlideData && 'photo' in currSlideData) {
                const photo = currSlideData.photo as Photo;
                try {
                  const token = await getAccessTokenSilently();
                  const updatedPhoto = await rotatePhoto(photo.id, 90, token);
                  
                  toast.success('Photo rotated successfully');
                  
                  // Update the current slide with the new photo URL
                  if (pswp.currSlide) {
                    pswp.currSlide.data.src = updatedPhoto.photo_url;
                    pswp.currSlide.data.width = updatedPhoto.width;
                    pswp.currSlide.data.height = updatedPhoto.height;
                    (pswp.currSlide.data as { photo: Photo }).photo = updatedPhoto;
                    
                    // Force PhotoSwipe to reload the image
                    pswp.refreshSlideContent(pswp.currSlide.index);
                  }
                  
                  // Call the callback if provided
                  if (onPhotoRotated) {
                    onPhotoRotated(updatedPhoto);
                  }
                } catch (error) {
                  console.error('Failed to rotate photo:', error);
                  toast.error('Failed to rotate photo. Please try again.');
                }
              }
            };
          },
        });
      }
    });

    // Add keyboard event listeners for +/- zoom (PhotoSwipe handles ESC by default)
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!pswp.currSlide) return;
      
      if (e.key === '+' || e.key === '=') {
        e.preventDefault();
        const currZoom = pswp.currSlide.currZoomLevel || 1;
        const newZoom = Math.min(currZoom * 1.2, 4); // Increase by 20%, max 4x
        pswp.currSlide.zoomTo(newZoom, { x: pswp.currSlide.bounds.center.x, y: pswp.currSlide.bounds.center.y }, 300);
      } else if (e.key === '-' || e.key === '_') {
        e.preventDefault();
        const currZoom = pswp.currSlide.currZoomLevel || 1;
        const initialZoom = pswp.currSlide.zoomLevels.initial || 1;
        const newZoom = Math.max(currZoom / 1.2, initialZoom); // Decrease by 20%, min initial zoom
        pswp.currSlide.zoomTo(newZoom, { x: pswp.currSlide.bounds.center.x, y: pswp.currSlide.bounds.center.y }, 300);
      }
    };

    pswp.on('bindEvents', () => {
      document.addEventListener('keydown', handleKeyDown);
    });

    // Handle close event
    pswp.on('close', () => {
      document.removeEventListener('keydown', handleKeyDown);
      if (onClose) {
        onClose();
      }
    });

    // Open PhotoSwipe
    pswp.init();

    // Cleanup on unmount
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      if (pswpRef.current) {
        pswpRef.current.close();
        pswpRef.current = null;
      }
    };
  }, [photos, initialIndex, onClose, getAccessTokenSilently, isAuthenticated, onPhotoRotated]);

  return pswpRef;
}

