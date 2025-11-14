import { useState, useEffect, useCallback } from "react";
import Card from "../ui/Card";
import Spinner from "../ui/Spinner";
import { useAdverts, AdvertItem } from "../../hooks/useAdverts";

interface AdvertCardProps {
  advert: AdvertItem;
  isBlurred?: boolean;
}

function AdvertCard({ advert, isBlurred = false }: AdvertCardProps) {
  const hasPhoto = advert.photo;
  const hasLink = advert.link;
  const hasTitle = advert.title;
  const hasText = advert.text;

  const content = (
    <div className={`h-full flex flex-col p-4 bg-white rounded-lg ${isBlurred ? "blur-sm opacity-60" : ""} ${hasLink && !isBlurred ? "cursor-pointer hover:shadow-lg transition-shadow" : ""}`}>
      {hasPhoto && (
        <div className="w-full flex-1 bg-gray-100 rounded overflow-hidden mb-3">
          <img
            src={advert.photo!}
            alt={advert.title || "Advertisement"}
            className="w-full h-full object-cover"
          />
        </div>
      )}
      <div className={`flex flex-col ${!hasPhoto ? "justify-center text-center flex-1" : ""}`}>
        {hasTitle && (
          <h3
            className={`font-bold text-gray-800 mb-2 ${
              !hasPhoto ? "text-xl" : "text-base"
            }`}
          >
            {advert.title}
          </h3>
        )}
        {hasText && (
          <p
            className={`text-gray-600 ${
              !hasPhoto ? "text-base" : "text-sm"
            } line-clamp-3`}
          >
            {advert.text}
          </p>
        )}
      </div>
    </div>
  );

  if (hasLink && !isBlurred) {
    return (
      <a
        href={advert.link!}
        target="_blank"
        rel="noopener noreferrer"
        className="block h-full"
        onClick={(e) => e.stopPropagation()}
      >
        {content}
      </a>
    );
  }

  return content;
}

export default function AdvertCarousel() {
  const { data: adverts, isLoading, error } = useAdverts();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);

  const handleNext = useCallback(() => {
    if (!adverts || adverts.length === 0 || isTransitioning) return;
    setIsTransitioning(true);
    setTimeout(() => {
      setCurrentIndex((prev) => (prev + 1) % adverts.length);
      setIsTransitioning(false);
    }, 700); // Match transition duration
  }, [adverts, isTransitioning]);

  const handlePrev = useCallback(() => {
    if (!adverts || adverts.length === 0 || isTransitioning) return;
    setIsTransitioning(true);
    setTimeout(() => {
      setCurrentIndex((prev) => (prev - 1 + adverts.length) % adverts.length);
      setIsTransitioning(false);
    }, 700); // Match transition duration
  }, [adverts, isTransitioning]);

  const handleDotClick = useCallback((index: number) => {
    if (isTransitioning) return;
    setIsTransitioning(true);
    setTimeout(() => {
      setCurrentIndex(index);
      setIsTransitioning(false);
    }, 700);
  }, [isTransitioning]);

  // Auto-advance every 10 seconds
  useEffect(() => {
    if (!adverts || adverts.length <= 1 || isPaused) return;

    const interval = setInterval(() => {
      handleNext();
    }, 10000);

    return () => clearInterval(interval);
  }, [adverts, isPaused, handleNext]);

  // Ensure current index is valid when adverts change
  const validIndex = adverts && currentIndex >= adverts.length ? 0 : currentIndex;
  const currentAdvert = adverts?.[validIndex];

  if (error) {
    return null; // Silently fail
  }

  if (isLoading) {
    return (
      <Card>
        <div className="h-[438px] flex items-center justify-center">
          <Spinner size="sm" />
        </div>
      </Card>
    );
  }

  if (!adverts || adverts.length === 0) {
    return null; // Hide if no active adverts
  }

  const showControls = adverts.length > 1;
  
  // Get previous and next adverts for side display
  const prevIndex = (validIndex - 1 + adverts.length) % adverts.length;
  const nextIndex = (validIndex + 1) % adverts.length;
  const prevAdvert = adverts[prevIndex];
  const nextAdvert = adverts[nextIndex];
  const hasMultipleAds = adverts.length > 1;

  // Ensure we have a valid current advert
  if (!currentAdvert) {
    return null;
  }

  return (
    <Card
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      onClick={() => setIsPaused(true)}
      className="overflow-hidden"
    >
      {/* Responsive container - fixed height, flexible width */}
      <div className="relative w-full h-[438px] flex items-center justify-center">
        {/* Carousel track with side cards visible */}
        <div className="absolute inset-0 flex items-center justify-center overflow-hidden">
          {/* Previous ad (blurred, partial) - animated */}
          {hasMultipleAds && (
            <div 
              className={`absolute left-0 w-40 h-[438px] -translate-x-1/2 pointer-events-none z-0 transition-opacity duration-700 ease-in-out ${
                isTransitioning ? 'opacity-0' : 'opacity-100'
              }`}
            >
              <div className="w-80 h-[438px]">
                <AdvertCard advert={prevAdvert} isBlurred={true} />
              </div>
            </div>
          )}
          
          {/* Current ad (center, full visibility) - Fixed 320px width with animation */}
          <div 
            className={`absolute inset-0 flex items-center justify-center z-10 transition-opacity duration-700 ease-in-out ${
              isTransitioning ? 'opacity-0' : 'opacity-100'
            }`}
          >
            <div className="w-80 h-[438px] flex-shrink-0">
              <AdvertCard advert={currentAdvert} />
            </div>
          </div>
          
          {/* Next ad (blurred, partial) - animated */}
          {hasMultipleAds && (
            <div 
              className={`absolute right-0 w-40 h-[438px] translate-x-1/2 pointer-events-none z-0 transition-opacity duration-700 ease-in-out ${
                isTransitioning ? 'opacity-0' : 'opacity-100'
              }`}
            >
              <div className="w-80 h-[438px]">
                <AdvertCard advert={nextAdvert} isBlurred={true} />
              </div>
            </div>
          )}
        </div>

        {/* Navigation buttons */}
        {showControls && (
          <>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handlePrev();
              }}
              disabled={isTransitioning}
              className="absolute left-2 top-1/2 -translate-y-1/2 bg-white/90 hover:bg-white shadow-md rounded-full w-8 h-8 flex items-center justify-center text-gray-700 hover:text-gray-900 transition-colors z-20 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Previous advertisement"
            >
              <span className="text-lg leading-none">‹</span>
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleNext();
              }}
              disabled={isTransitioning}
              className="absolute right-2 top-1/2 -translate-y-1/2 bg-white/90 hover:bg-white shadow-md rounded-full w-8 h-8 flex items-center justify-center text-gray-700 hover:text-gray-900 transition-colors z-20 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Next advertisement"
            >
              <span className="text-lg leading-none">›</span>
            </button>
          </>
        )}
      </div>

      {/* Dot indicators below the carousel */}
      {showControls && (
        <div className="flex justify-center gap-2 py-3">
          {adverts.map((_, index) => (
            <button
              key={index}
              onClick={(e) => {
                e.stopPropagation();
                handleDotClick(index);
              }}
              disabled={isTransitioning}
              className={`w-2 h-2 rounded-full transition-all disabled:cursor-not-allowed ${
                index === currentIndex
                  ? "bg-trig-green-600 w-6"
                  : "bg-gray-300 hover:bg-gray-400"
              }`}
              aria-label={`Go to advertisement ${index + 1}`}
            />
          ))}
        </div>
      )}
    </Card>
  );
}

