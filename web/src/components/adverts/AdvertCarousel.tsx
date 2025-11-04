import { useState, useEffect, useCallback } from "react";
import Card from "../ui/Card";
import Button from "../ui/Button";
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
    <div className={`h-full flex flex-col p-4 bg-white rounded-lg ${isBlurred ? "blur-sm opacity-60" : ""}`}>
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
        {hasLink && !isBlurred && (
          <div className="mt-3">
            <Button
              variant="primary"
              className="w-full text-sm py-2"
              onClick={(e: React.MouseEvent) => {
                e.stopPropagation();
                window.open(advert.link!, "_blank", "noopener,noreferrer");
              }}
            >
              Learn More →
            </Button>
          </div>
        )}
      </div>
    </div>
  );

  return content;
}

export default function AdvertCarousel() {
  const { data: adverts, isLoading, error } = useAdverts();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);

  const handleNext = useCallback(() => {
    if (!adverts || adverts.length === 0) return;
    setCurrentIndex((prev) => (prev + 1) % adverts.length);
  }, [adverts]);

  const handlePrev = useCallback(() => {
    if (!adverts || adverts.length === 0) return;
    setCurrentIndex((prev) => (prev - 1 + adverts.length) % adverts.length);
  }, [adverts]);

  const handleDotClick = useCallback((index: number) => {
    setCurrentIndex(index);
  }, []);

  // Auto-advance every 15 seconds
  useEffect(() => {
    if (!adverts || adverts.length <= 1 || isPaused) return;

    const interval = setInterval(() => {
      handleNext();
    }, 15000);

    return () => clearInterval(interval);
  }, [adverts, isPaused, handleNext]);

  // Reset index if adverts change and current index is out of bounds
  useEffect(() => {
    if (adverts && currentIndex >= adverts.length) {
      setCurrentIndex(0);
    }
  }, [adverts, currentIndex]);

  if (error) {
    return null; // Silently fail
  }

  if (isLoading) {
    return (
      <Card>
        <div className="aspect-[16/9] flex items-center justify-center">
          <Spinner size="sm" />
        </div>
      </Card>
    );
  }

  if (!adverts || adverts.length === 0) {
    return null; // Hide if no active adverts
  }

  const currentAdvert = adverts[currentIndex];
  const showControls = adverts.length > 1;
  
  // Get previous and next adverts for side display
  const prevIndex = (currentIndex - 1 + adverts.length) % adverts.length;
  const nextIndex = (currentIndex + 1) % adverts.length;
  const prevAdvert = adverts[prevIndex];
  const nextAdvert = adverts[nextIndex];
  const hasMultipleAds = adverts.length > 1;

  return (
    <Card
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      onClick={() => setIsPaused(true)}
      className="overflow-hidden"
    >
      {/* Fixed 16:9 aspect ratio container */}
      <div className="relative w-full aspect-[16/9]">
        {/* Carousel track with side cards visible */}
        <div className="absolute inset-0 flex items-center overflow-hidden">
          {/* Previous ad (blurred, partial) */}
          {hasMultipleAds && (
            <div className="absolute left-0 w-1/4 h-full -translate-x-1/2 pointer-events-none z-0">
              <AdvertCard advert={prevAdvert} isBlurred={true} />
            </div>
          )}
          
          {/* Current ad (center, full visibility) */}
          <div className="absolute inset-0 flex items-center justify-center z-10 px-8">
            <div className="w-full h-full">
              <AdvertCard advert={currentAdvert} />
            </div>
          </div>
          
          {/* Next ad (blurred, partial) */}
          {hasMultipleAds && (
            <div className="absolute right-0 w-1/4 h-full translate-x-1/2 pointer-events-none z-0">
              <AdvertCard advert={nextAdvert} isBlurred={true} />
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
              className="absolute left-2 top-1/2 -translate-y-1/2 bg-white/90 hover:bg-white shadow-md rounded-full w-8 h-8 flex items-center justify-center text-gray-700 hover:text-gray-900 transition-colors z-20"
              aria-label="Previous advertisement"
            >
              <span className="text-lg leading-none">‹</span>
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleNext();
              }}
              className="absolute right-2 top-1/2 -translate-y-1/2 bg-white/90 hover:bg-white shadow-md rounded-full w-8 h-8 flex items-center justify-center text-gray-700 hover:text-gray-900 transition-colors z-20"
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
              className={`w-2 h-2 rounded-full transition-all ${
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

