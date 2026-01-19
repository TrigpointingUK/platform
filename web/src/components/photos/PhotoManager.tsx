import { useState, useRef, useEffect } from "react";
import { Photo } from "../../lib/api";
import { useUploadPhoto, useUpdatePhoto, useDeletePhoto, useRotatePhoto } from "../../hooks/useLogPhotos";
import { useUserProfile } from "../../hooks/useUserProfile";
import Button from "../ui/Button";
import Spinner from "../ui/Spinner";
import { Trash2, RotateCw, Edit2, X, Check, Upload } from "lucide-react";

interface PhotoManagerProps {
  logId: number | undefined;
  photos: Photo[];
  isEditing: boolean;
}

export default function PhotoManager({ logId, photos, isEditing }: PhotoManagerProps) {
  // Fetch user's default license preference
  const { data: userProfile } = useUserProfile("me");
  const defaultLicense = userProfile?.prefs?.public_ind || "N";

  const [editingPhotoId, setEditingPhotoId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState({
    caption: "",
    text_desc: "",
    type: "O",
    license: "Y",
  });
  const [uploadForm, setUploadForm] = useState({
    caption: "",
    text_desc: "",
    type: "T",
    license: defaultLicense, // Initialize with current default
  });
  
  // Track previous defaultLicense to update form when it changes
  const prevDefaultLicenseRef = useRef(defaultLicense);
  
  // Update form when defaultLicense changes from async user profile load
  // This is responding to external data (user profile query), not derived state
  useEffect(() => {
    if (prevDefaultLicenseRef.current !== defaultLicense) {
      prevDefaultLicenseRef.current = defaultLicense;
      // eslint-disable-next-line react-hooks/set-state-in-effect -- Responding to async user profile load
      setUploadForm((prev) => ({ ...prev, license: defaultLicense }));
    }
  }, [defaultLicense]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [showUploadForm, setShowUploadForm] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const uploadMutation = useUploadPhoto(logId!);
  const updateMutation = useUpdatePhoto();
  const deleteMutation = useDeletePhoto();
  const rotateMutation = useRotatePhoto();

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setShowUploadForm(true);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !logId) return;

    try {
      await uploadMutation.mutateAsync({
        file: selectedFile,
        caption: uploadForm.caption,
        text_desc: uploadForm.text_desc,
        type: uploadForm.type,
        license: uploadForm.license,
      });

      // Reset form
      setSelectedFile(null);
      setShowUploadForm(false);
      setUploadForm({
        caption: "",
        text_desc: "",
        type: "T",
        license: defaultLicense,
      });
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (error) {
      console.error("Failed to upload photo:", error);
      alert("Failed to upload photo. Please try again.");
    }
  };

  const handleCancelUpload = () => {
    setSelectedFile(null);
    setShowUploadForm(false);
    setUploadForm({
      caption: "",
      text_desc: "",
      type: "T",
      license: defaultLicense,
    });
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleEdit = (photo: Photo) => {
    setEditingPhotoId(photo.id);
    setEditForm({
      caption: photo.caption,
      text_desc: photo.text_desc,
      type: photo.type,
      license: photo.license,
    });
  };

  const handleSaveEdit = async (photoId: number) => {
    try {
      await updateMutation.mutateAsync({
        photoId,
        updates: editForm,
      });
      setEditingPhotoId(null);
    } catch (error) {
      console.error("Failed to update photo:", error);
      alert("Failed to update photo. Please try again.");
    }
  };

  const handleCancelEdit = () => {
    setEditingPhotoId(null);
  };

  const handleDelete = async (photoId: number) => {
    if (!confirm("Are you sure you want to delete this photo?")) return;

    try {
      await deleteMutation.mutateAsync(photoId);
    } catch (error) {
      console.error("Failed to delete photo:", error);
      alert("Failed to delete photo. Please try again.");
    }
  };

  const handleRotate = async (photoId: number, angle: number) => {
    try {
      await rotateMutation.mutateAsync({ photoId, angle });
    } catch (error) {
      console.error("Failed to rotate photo:", error);
      alert("Failed to rotate photo. Please try again.");
    }
  };

  const photoTypeOptions = [
    { value: "T", label: "Trigpoint" },
    { value: "F", label: "Flush Bracket" },
    { value: "L", label: "Landscape" },
    { value: "P", label: "People" },
    { value: "O", label: "Other" },
  ];

  const licenseOptions = [
    { value: "Y", label: "Public Domain" },
    { value: "C", label: "Creative Commons" },
    { value: "N", label: "Private" },
  ];

  if (!isEditing && (!photos || photos.length === 0)) {
    return null;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
          Photos {photos && photos.length > 0 && `(${photos.length})`}
        </h3>
        {isEditing && logId && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
            disabled={showUploadForm || uploadMutation.isPending}
          >
            <Upload size={16} className="mr-2" />
            Add Photo
          </Button>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/jpg"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Upload Form */}
      {showUploadForm && selectedFile && (
        <div className="border border-trig-green-600 dark:border-trig-green-700 bg-trig-green-100 dark:bg-trig-green-950 rounded-lg p-4 space-y-3">
          <div className="flex items-start justify-between">
            <h4 className="font-semibold text-gray-800 dark:text-gray-100">Upload New Photo</h4>
            <button
              type="button"
              onClick={handleCancelUpload}
              className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
            >
              <X size={18} />
            </button>
          </div>
          
          <div className="text-sm text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-800 rounded px-3 py-2">
            <strong>File:</strong> {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Caption *
            </label>
            <input
              type="text"
              value={uploadForm.caption}
              onChange={(e) =>
                setUploadForm((prev) => ({ ...prev, caption: e.target.value }))
              }
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-trig-green-500"
              placeholder="Brief caption"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description
            </label>
            <textarea
              value={uploadForm.text_desc}
              onChange={(e) =>
                setUploadForm((prev) => ({ ...prev, text_desc: e.target.value }))
              }
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-trig-green-500"
              rows={2}
              placeholder="Detailed description (optional)"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Type *
              </label>
              <select
                value={uploadForm.type}
                onChange={(e) =>
                  setUploadForm((prev) => ({ ...prev, type: e.target.value }))
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-trig-green-500"
                required
              >
                {photoTypeOptions.map((opt) => (
                  <option key={opt.value} value={opt.value} className="bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100">
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                License *
              </label>
              <select
                value={uploadForm.license}
                onChange={(e) =>
                  setUploadForm((prev) => ({ ...prev, license: e.target.value }))
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-trig-green-500"
                required
              >
                {licenseOptions.map((opt) => (
                  <option key={opt.value} value={opt.value} className="bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100">
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              type="button"
              onClick={handleUpload}
              disabled={!uploadForm.caption || uploadMutation.isPending}
              size="sm"
            >
              {uploadMutation.isPending ? (
                <>
                  <Spinner size="sm" />
                  <span className="ml-2">Uploading...</span>
                </>
              ) : (
                <>
                  <Upload size={16} className="mr-2" />
                  Upload
                </>
              )}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleCancelUpload}
              disabled={uploadMutation.isPending}
              size="sm"
            >
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Photos Grid */}
      {photos && photos.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {photos.map((photo) => (
            <div
              key={photo.id}
              className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-gray-800"
            >
              <div className="relative">
                <img
                  src={photo.icon_url}
                  alt={photo.caption}
                  className="w-full h-48 object-cover"
                  loading="lazy"
                />
                {isEditing && (
                  <div className="absolute top-2 right-2 flex gap-1">
                    <button
                      type="button"
                      onClick={() => handleRotate(photo.id, 90)}
                      disabled={rotateMutation.isPending}
                      className="p-1.5 bg-white/90 dark:bg-gray-800/90 hover:bg-white dark:hover:bg-gray-800 rounded shadow-sm"
                      title="Rotate 90° clockwise"
                    >
                      <RotateCw size={16} className="text-gray-700 dark:text-gray-300" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(photo.id)}
                      disabled={deleteMutation.isPending}
                      className="p-1.5 bg-white/90 dark:bg-gray-800/90 hover:bg-white dark:hover:bg-gray-800 rounded shadow-sm"
                      title="Delete photo"
                    >
                      <Trash2 size={16} className="text-red-600 dark:text-red-400" />
                    </button>
                  </div>
                )}
              </div>

              <div className="p-3 space-y-2">
                {editingPhotoId === photo.id ? (
                  <>
                    <input
                      type="text"
                      value={editForm.caption}
                      onChange={(e) =>
                        setEditForm((prev) => ({ ...prev, caption: e.target.value }))
                      }
                      className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 dark:placeholder-gray-400"
                      placeholder="Caption"
                    />
                    <textarea
                      value={editForm.text_desc}
                      onChange={(e) =>
                        setEditForm((prev) => ({ ...prev, text_desc: e.target.value }))
                      }
                      className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 dark:placeholder-gray-400"
                      rows={2}
                      placeholder="Description"
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <select
                        value={editForm.type}
                        onChange={(e) =>
                          setEditForm((prev) => ({ ...prev, type: e.target.value }))
                        }
                        className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                      >
                        {photoTypeOptions.map((opt) => (
                          <option key={opt.value} value={opt.value} className="bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100">
                            {opt.label}
                          </option>
                        ))}
                      </select>
                      <select
                        value={editForm.license}
                        onChange={(e) =>
                          setEditForm((prev) => ({ ...prev, license: e.target.value }))
                        }
                        className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                      >
                        {licenseOptions.map((opt) => (
                          <option key={opt.value} value={opt.value} className="bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100">
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="flex gap-1">
                      <button
                        type="button"
                        onClick={() => handleSaveEdit(photo.id)}
                        disabled={updateMutation.isPending}
                        className="flex-1 px-2 py-1 text-xs bg-trig-green-600 text-white rounded hover:bg-trig-green-700 flex items-center justify-center"
                      >
                        {updateMutation.isPending ? (
                          <Spinner size="sm" />
                        ) : (
                          <>
                            <Check size={14} className="mr-1" />
                            Save
                          </>
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={handleCancelEdit}
                        className="flex-1 px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
                      >
                        <X size={14} className="inline mr-1" />
                        Cancel
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h4 className="font-medium text-sm text-gray-800 dark:text-gray-100">
                          {photo.caption}
                        </h4>
                        {photo.text_desc && (
                          <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                            {photo.text_desc}
                          </p>
                        )}
                      </div>
                      {isEditing && (
                        <button
                          type="button"
                          onClick={() => handleEdit(photo)}
                          className="ml-2 p-1 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
                          title="Edit metadata"
                        >
                          <Edit2 size={14} />
                        </button>
                      )}
                    </div>
                    <div className="flex gap-2 text-xs text-gray-500 dark:text-gray-400">
                      <span>
                        {photoTypeOptions.find((t) => t.value === photo.type)?.label || photo.type}
                      </span>
                      <span>•</span>
                      <span>
                        {licenseOptions.find((l) => l.value === photo.license)?.label || photo.license}
                      </span>
                    </div>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

