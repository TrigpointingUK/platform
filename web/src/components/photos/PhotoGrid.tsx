import { useNavigate } from "react-router-dom";
import PhotoThumbnail from "./PhotoThumbnail";
import { Photo } from "../../lib/api";

interface PhotoGridProps {
  photos: Photo[];
  onPhotoClick?: (photo: Photo) => void;
  onPhotoRotated?: (updatedPhoto: Photo) => void;
}

export default function PhotoGrid({ photos, onPhotoClick, onPhotoRotated }: PhotoGridProps) {
  const navigate = useNavigate();

  if (!photos || photos.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>No photos found</p>
      </div>
    );
  }

  const handlePhotoClick = (photo: Photo) => {
    if (onPhotoClick) {
      onPhotoClick(photo);
    } else {
      // Default behavior: navigate to photo detail page
      navigate(`/photos/${photo.id}`);
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {photos.map((photo) => (
        <PhotoThumbnail
          key={photo.id}
          photo={photo}
          onClick={() => handlePhotoClick(photo)}
          onPhotoRotated={onPhotoRotated}
        />
      ))}
    </div>
  );
}

