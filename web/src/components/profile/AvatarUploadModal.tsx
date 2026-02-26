import { useState, useCallback, useRef } from "react";
import Cropper from "react-easy-crop";
import type { Area } from "react-easy-crop";
import toast from "react-hot-toast";
import { Camera } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "../ui/Dialog";
import Button from "../ui/Button";
import Spinner from "../ui/Spinner";
import { getCroppedImg } from "../../lib/cropImage";
import { useAvatarUpload } from "../../hooks/useAvatarUpload";

interface AvatarUploadModalProps {
  currentPictureUrl?: string;
  onUploaded: (newUrl: string) => void;
}

export default function AvatarUploadModal({
  currentPictureUrl,
  onUploaded,
}: AvatarUploadModalProps) {
  const [open, setOpen] = useState(false);
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState<Area | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { mutateAsync: uploadAvatar, isPending } = useAvatarUpload();

  const onCropComplete = useCallback(
    (_croppedArea: Area, croppedPixels: Area) => {
      setCroppedAreaPixels(croppedPixels);
    },
    []
  );

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      toast.error("Please select an image file");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      toast.error("Image must be under 10MB");
      return;
    }

    const reader = new FileReader();
    reader.addEventListener("load", () => {
      setImageSrc(reader.result as string);
    });
    reader.readAsDataURL(file);
  };

  const handleUpload = async () => {
    if (!imageSrc || !croppedAreaPixels) return;

    try {
      const croppedBlob = await getCroppedImg(imageSrc, croppedAreaPixels, 200);
      const result = await uploadAvatar(croppedBlob);
      toast.success("Avatar updated!");
      onUploaded(result.avatar_url);
      handleClose();
    } catch (error) {
      console.error("Avatar upload failed:", error);
      toast.error(
        error instanceof Error ? error.message : "Failed to upload avatar"
      );
    }
  };

  const handleClose = () => {
    setOpen(false);
    setImageSrc(null);
    setCrop({ x: 0, y: 0 });
    setZoom(1);
    setCroppedAreaPixels(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <>
      {/* Trigger: clickable avatar */}
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="group relative rounded-full overflow-hidden w-20 h-20 flex-shrink-0 focus:outline-none focus:ring-2 focus:ring-trig-green-500 focus:ring-offset-2"
        title="Change avatar"
      >
        {currentPictureUrl ? (
          <img
            src={currentPictureUrl}
            alt="User avatar"
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full bg-trig-green-100 dark:bg-trig-green-900 flex items-center justify-center">
            <Camera className="w-8 h-8 text-trig-green-600 dark:text-trig-green-400" />
          </div>
        )}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center">
          <Camera className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
      </button>

      <Dialog open={open} onOpenChange={(v) => (v ? setOpen(true) : handleClose())}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Update Avatar</DialogTitle>
            <DialogDescription>
              Choose an image and adjust the crop area.
            </DialogDescription>
          </DialogHeader>

          {!imageSrc ? (
            <div className="flex flex-col items-center gap-4 py-8">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleFileSelect}
                className="hidden"
              />
              <Button
                variant="primary"
                onClick={() => fileInputRef.current?.click()}
              >
                Choose Image
              </Button>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                JPEG, PNG, or WebP up to 10MB
              </p>
            </div>
          ) : (
            <>
              <div className="relative w-full" style={{ height: 300 }}>
                <Cropper
                  image={imageSrc}
                  crop={crop}
                  zoom={zoom}
                  aspect={1}
                  cropShape="round"
                  showGrid={false}
                  onCropChange={setCrop}
                  onZoomChange={setZoom}
                  onCropComplete={onCropComplete}
                />
              </div>
              <div className="flex items-center gap-3 mt-3">
                <label className="text-sm text-gray-600 dark:text-gray-400 flex-shrink-0">
                  Zoom
                </label>
                <input
                  type="range"
                  min={1}
                  max={3}
                  step={0.05}
                  value={zoom}
                  onChange={(e) => setZoom(Number(e.target.value))}
                  className="flex-1 accent-trig-green-600"
                />
              </div>
            </>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={handleClose} disabled={isPending}>
              Cancel
            </Button>
            {imageSrc && (
              <Button
                variant="primary"
                onClick={handleUpload}
                disabled={isPending || !croppedAreaPixels}
              >
                {isPending ? (
                  <span className="flex items-center gap-2">
                    <Spinner size="sm" /> Uploading…
                  </span>
                ) : (
                  "Update Avatar"
                )}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
