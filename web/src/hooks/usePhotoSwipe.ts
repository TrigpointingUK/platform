import { useEffect, useRef } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import toast from 'react-hot-toast';
import PhotoSwipe from 'photoswipe';
import type { Photo } from '../lib/api';
import { authenticatedPost, authenticatedPut, authenticatedDelete } from '../lib/api';

const API_BASE = import.meta.env.VITE_API_BASE as string;

export interface PhotoSwipeOptions {
  photos: Photo[];
  initialIndex?: number;
  onClose?: () => void;
  onPhotoRotated?: (updatedPhoto: Photo) => void;
}

function isEmptyOrNone(value: string | null | undefined): boolean {
  if (!value) return true;
  const trimmed = value.trim().toLowerCase();
  return trimmed === '' || trimmed === 'none';
}

const STAR_SVG_PATH =
  'M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z';

function createMetadataOverlay(photo: Photo, authenticated: boolean): string {
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
  const filesize = (photo.filesize / 1024).toFixed(0);

  const waypoint = photo.trig_id != null ? `TP${String(photo.trig_id).padStart(4, '0')}` : null;

  const formattedDate = photo.log_date ? new Date(photo.log_date).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  }) : null;

  const hasCaption = !isEmptyOrNone(photo.caption);
  const hasDescription = !isEmptyOrNone(photo.text_desc);

  const starHtml = buildStarsHtml(0, null, !authenticated);
  const ratingLabel = authenticated ? 'Rate this photo' : '';
  const loginHint = !authenticated ? '<span class="pswp__rating-login">Log in to rate</span>' : '';

  return `
    <div class="pswp__custom-caption">
      <div class="pswp__caption-content">
        ${hasCaption ? `<h3 class="pswp__caption-title">${photo.caption}</h3>` : ''}
        ${hasDescription ? `<p class="pswp__caption-desc">${photo.text_desc}</p>` : ''}
        ${waypoint && photo.trig_name ? `<div class="pswp__caption-location">${waypoint} · ${photo.trig_name}</div>` : ''}
        ${photo.user_name ? `<div class="pswp__caption-user">By ${photo.user_name}</div>` : ''}
        ${formattedDate ? `<div class="pswp__caption-date">${formattedDate}</div>` : ''}
        <div class="pswp__caption-rating" data-photo-id="${photo.id}">
          <div class="pswp__rating-stars" data-readonly="${!authenticated}" data-score="0" data-user-score="0">
            ${starHtml}
          </div>
          <span class="pswp__rating-label">${ratingLabel}</span>
          <span class="pswp__rating-aggregate"></span>
          ${loginHint}
        </div>
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

function buildStarsHtml(displayScore: number, _hoverScore: number | null, readonly: boolean): string {
  const effectiveScore = _hoverScore ?? displayScore;
  const rating = effectiveScore / 2;
  let html = '';
  for (let i = 0; i < 5; i++) {
    let fill: 'full' | 'half' | 'empty' = 'empty';
    if (i < Math.floor(rating)) fill = 'full';
    else if (i < rating && rating % 1 >= 0.5) fill = 'half';

    const clipStyle = fill === 'half' ? ' style="clip-path: inset(0 50% 0 0)"' : '';
    const filledSvg = fill !== 'empty'
      ? `<svg class="star-filled" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"${clipStyle}><path d="${STAR_SVG_PATH}"/></svg>`
      : '';

    html += `<div class="pswp__rating-star" data-star-index="${i}" ${readonly ? '' : 'role="button"'}>` +
      `<svg class="star-empty" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path d="${STAR_SVG_PATH}"/></svg>` +
      filledSvg +
      `</div>`;
  }
  return html;
}

function updateStarsDisplay(container: HTMLElement, displayScore: number, hoverScore: number | null) {
  const readonly = container.dataset.readonly === 'true';
  container.innerHTML = buildStarsHtml(displayScore, hoverScore, readonly);
}

interface RatingData {
  average_score: number | null;
  vote_count: number;
  user_score: number | null;
}

export function usePhotoSwipe({ photos, initialIndex = 0, onClose, onPhotoRotated }: PhotoSwipeOptions) {
  const pswpRef = useRef<PhotoSwipe | null>(null);
  const isClosingRef = useRef(false);
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();
  // Cache of fetched ratings keyed by photo ID
  const ratingCacheRef = useRef<Map<number, RatingData>>(new Map());

  useEffect(() => {
    if (photos.length === 0) return;

    const dataSource = photos.map((photo) => ({
      src: photo.photo_url,
      width: photo.width,
      height: photo.height,
      alt: photo.caption,
      photo: photo,
    }));

    const options = {
      dataSource,
      index: initialIndex,
      maxZoomLevel: 4,
      initialZoomLevel: 'fit' as const,
      secondaryZoomLevel: 1,
      padding: { top: 50, bottom: 120, left: 20, right: 20 },
      bgOpacity: 0.9,
      zoom: true,
      close: true,
      counter: photos.length > 1,
      arrowPrev: photos.length > 1,
      arrowNext: photos.length > 1,
      clickToCloseNonZoomable: true,
      tapAction: 'close' as const,
      doubleTapAction: 'zoom' as const,
      wheelToZoom: true,
      keyboard: true,
      pinchToClose: false,
      showHideAnimationType: 'zoom' as const,
      allowPanToNext: photos.length > 1,
      closeOnVerticalDrag: true,
    };

    const pswp = new PhotoSwipe(options);
    pswpRef.current = pswp;

    // ---- Rating helpers ----

    async function fetchRating(photoId: number): Promise<RatingData | null> {
      try {
        const headers: Record<string, string> = { Accept: 'application/json' };
        if (isAuthenticated) {
          try {
            const token = await getAccessTokenSilently();
            headers['Authorization'] = `Bearer ${token}`;
          } catch {
            // Proceed without auth
          }
        }
        const resp = await fetch(`${API_BASE}/v1/photos/${photoId}/rating`, { headers });
        if (!resp.ok) return null;
        return resp.json();
      } catch {
        return null;
      }
    }

    function applyRatingToCaption(captionEl: HTMLElement, photoId: number, data: RatingData) {
      const ratingDiv = captionEl.querySelector(`.pswp__caption-rating[data-photo-id="${photoId}"]`);
      if (!ratingDiv) return;

      const starsContainer = ratingDiv.querySelector('.pswp__rating-stars') as HTMLElement | null;
      const labelEl = ratingDiv.querySelector('.pswp__rating-label') as HTMLElement | null;
      const aggEl = ratingDiv.querySelector('.pswp__rating-aggregate') as HTMLElement | null;

      if (starsContainer) {
        const displayScore = data.user_score ?? (data.average_score ? Math.round(data.average_score) : 0);
        starsContainer.dataset.score = String(displayScore);
        starsContainer.dataset.userScore = String(data.user_score ?? 0);
        updateStarsDisplay(starsContainer, displayScore, null);
      }

      if (labelEl) {
        if (data.user_score != null && data.user_score > 0) {
          labelEl.textContent = `Your rating: ${data.user_score}/10`;
        } else if (isAuthenticated) {
          labelEl.textContent = 'Rate this photo';
        }
      }

      if (aggEl) {
        if (data.vote_count > 0 && data.average_score != null) {
          aggEl.textContent = `Average: ${data.average_score}/10 (${data.vote_count} vote${data.vote_count !== 1 ? 's' : ''})`;
        } else {
          aggEl.textContent = '';
        }
      }
    }

    async function submitRating(photoId: number, score: number, captionEl: HTMLElement) {
      try {
        let result: RatingData;
        if (score === 0) {
          result = await authenticatedDelete<RatingData>(
            `${API_BASE}/v1/photos/${photoId}/rating`,
            getAccessTokenSilently
          );
        } else {
          result = await authenticatedPut<RatingData>(
            `${API_BASE}/v1/photos/${photoId}/rating`,
            { score },
            getAccessTokenSilently
          );
        }
        ratingCacheRef.current.set(photoId, result);
        applyRatingToCaption(captionEl, photoId, result);
      } catch {
        toast.error('Failed to save rating');
      }
    }

    // ---- PhotoSwipe UI registration ----

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
              const photo = currSlideElement.photo as Photo;
              el.innerHTML = createMetadataOverlay(photo, isAuthenticated);

              // Fetch and apply rating
              const cached = ratingCacheRef.current.get(photo.id);
              if (cached) {
                applyRatingToCaption(el, photo.id, cached);
              }
              fetchRating(photo.id).then((data) => {
                if (data) {
                  ratingCacheRef.current.set(photo.id, data);
                  applyRatingToCaption(el, photo.id, data);
                }
              });

              // Wire up star interaction via event delegation
              if (isAuthenticated) {
                const starsContainer = el.querySelector('.pswp__rating-stars') as HTMLElement | null;
                if (starsContainer) {
                  starsContainer.addEventListener('mousemove', (e: MouseEvent) => {
                    const target = (e.target as HTMLElement).closest('.pswp__rating-star') as HTMLElement | null;
                    if (!target) return;
                    const idx = parseInt(target.dataset.starIndex ?? '0', 10);
                    const rect = target.getBoundingClientRect();
                    const x = e.clientX - rect.left;
                    const isLeft = x < rect.width / 2;
                    const hoverScore = idx * 2 + (isLeft ? 1 : 2);
                    const currentScore = parseInt(starsContainer.dataset.score ?? '0', 10);
                    updateStarsDisplay(starsContainer, currentScore, hoverScore);
                  });

                  starsContainer.addEventListener('mouseleave', () => {
                    const currentScore = parseInt(starsContainer.dataset.score ?? '0', 10);
                    updateStarsDisplay(starsContainer, currentScore, null);
                  });

                  starsContainer.addEventListener('click', (e: MouseEvent) => {
                    e.stopPropagation();
                    e.preventDefault();
                    const target = (e.target as HTMLElement).closest('.pswp__rating-star') as HTMLElement | null;
                    if (!target) return;
                    const idx = parseInt(target.dataset.starIndex ?? '0', 10);
                    const rect = target.getBoundingClientRect();
                    const x = e.clientX - rect.left;
                    const isLeft = x < rect.width / 2;
                    const clickScore = idx * 2 + (isLeft ? 1 : 2);
                    const userScore = parseInt(starsContainer.dataset.userScore ?? '0', 10);
                    const newScore = clickScore === userScore ? 0 : clickScore;

                    // Optimistic update
                    starsContainer.dataset.score = String(newScore);
                    starsContainer.dataset.userScore = String(newScore);
                    updateStarsDisplay(starsContainer, newScore, null);
                    const labelEl = el.querySelector('.pswp__rating-label') as HTMLElement | null;
                    if (labelEl) {
                      labelEl.textContent = newScore > 0 ? `Your rating: ${newScore}/10` : 'Rate this photo';
                    }

                    submitRating(photo.id, newScore, el);
                  });
                }
              }
            }
          });
        },
      });

      // Rotation buttons (only if user is logged in)
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
                  const updatedPhoto = await authenticatedPost<Photo>(
                    `${API_BASE}/v1/photos/${photo.id}/rotate`,
                    { angle: 270 },
                    getAccessTokenSilently
                  );
                  toast.success('Photo rotated successfully');
                  if (pswp.currSlide) {
                    pswp.currSlide.data.src = updatedPhoto.photo_url;
                    pswp.currSlide.data.width = updatedPhoto.width;
                    pswp.currSlide.data.height = updatedPhoto.height;
                    (pswp.currSlide.data as { photo: Photo }).photo = updatedPhoto;
                    pswp.refreshSlideContent(pswp.currSlide.index);
                  }
                  if (onPhotoRotated) onPhotoRotated(updatedPhoto);
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
                  const updatedPhoto = await authenticatedPost<Photo>(
                    `${API_BASE}/v1/photos/${photo.id}/rotate`,
                    { angle: 90 },
                    getAccessTokenSilently
                  );
                  toast.success('Photo rotated successfully');
                  if (pswp.currSlide) {
                    pswp.currSlide.data.src = updatedPhoto.photo_url;
                    pswp.currSlide.data.width = updatedPhoto.width;
                    pswp.currSlide.data.height = updatedPhoto.height;
                    (pswp.currSlide.data as { photo: Photo }).photo = updatedPhoto;
                    pswp.refreshSlideContent(pswp.currSlide.index);
                  }
                  if (onPhotoRotated) onPhotoRotated(updatedPhoto);
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

    // Keyboard zoom
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!pswp.currSlide) return;

      if (e.key === '+' || e.key === '=') {
        e.preventDefault();
        const currZoom = pswp.currSlide.currZoomLevel || 1;
        const newZoom = Math.min(currZoom * 1.2, 4);
        pswp.currSlide.zoomTo(newZoom, { x: pswp.currSlide.bounds.center.x, y: pswp.currSlide.bounds.center.y }, 300);
      } else if (e.key === '-' || e.key === '_') {
        e.preventDefault();
        const currZoom = pswp.currSlide.currZoomLevel || 1;
        const initialZoom = pswp.currSlide.zoomLevels.initial || 1;
        const newZoom = Math.max(currZoom / 1.2, initialZoom);
        pswp.currSlide.zoomTo(newZoom, { x: pswp.currSlide.bounds.center.x, y: pswp.currSlide.bounds.center.y }, 300);
      }
    };

    pswp.on('bindEvents', () => {
      document.addEventListener('keydown', handleKeyDown);
    });

    pswp.on('close', () => {
      document.removeEventListener('keydown', handleKeyDown);
      isClosingRef.current = true;
    });

    pswp.on('destroy', () => {
      if (isClosingRef.current && onClose) {
        requestAnimationFrame(() => {
          onClose();
        });
      }
    });

    pswp.init();

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      if (pswpRef.current) {
        if (!isClosingRef.current) {
          const pswpElement = document.querySelector('.pswp');
          if (pswpElement) {
            pswpElement.remove();
          }
        }
        pswpRef.current = null;
      }
    };
  }, [photos, initialIndex, onClose, getAccessTokenSilently, isAuthenticated, onPhotoRotated]);

  return pswpRef;
}
