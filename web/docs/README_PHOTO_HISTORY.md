# Photo Viewing History Feature

## Overview
This feature helps users discover fresh content by tracking which photos they've already seen using localStorage. It defaults to showing "unseen photos" but allows toggling to "all photos" mode.

## How It Works

### 1. Storage Mechanism
- **Storage**: Browser localStorage (device-specific)
- **Key**: `triguk_photo_viewing_history`
- **Data Structure**: Array of photo ID ranges `[{min: number, max: number}, ...]`
- **Size**: Typically <1KB for hundreds of viewing sessions

### 2. Range-Based Tracking
Instead of storing individual photo IDs, we track contiguous ranges:
- Example: Photos 1000-1024 and 500-524 → stored as `[{min: 1000, max: 1024}, {min: 500, max: 524}]`
- Overlapping/adjacent ranges are automatically merged for efficiency
- Uses photo IDs as the tracking metric (IDs are auto-incrementing and correlate with time)

### 3. Filtering Logic
- **Unseen Mode** (default): Filters out photos whose IDs fall within any viewed range
- **All Photos Mode**: Shows everything, no filtering applied
- Photos are marked as "viewed" 2 seconds after they load (giving user time to see them)

### 4. User Interface
- **Toggle**: "Unseen Photos" / "All Photos" button in the header
- **Reset History**: Button to clear viewing history (only shown when history exists)
- **Stats**: Shows count of previously viewed photos when in unseen mode

## API Integration
- No backend changes required
- Works entirely client-side with existing photo API
- Each device maintains its own viewing history

## Files
- **`photoHistory.ts`**: localStorage utility functions
- **`useInfinitePhotos.ts`**: Photo fetching hook with filtering support
- **`PhotoAlbum.tsx`**: UI component with toggle controls

## Usage Example
```typescript
// In a component
import { useInfinitePhotos } from '../hooks/useInfinitePhotos';
import { clearHistory } from '../lib/photoHistory';

const { data } = useInfinitePhotos({ mode: 'unseen' });
// Or mode: 'all' to show everything

// Clear history
clearHistory();
```

## Limitations
- Device-specific (doesn't sync across devices)
- ~5-10MB localStorage limit (more than enough for this use case)
- Uses photo IDs rather than timestamps (close enough for intended purpose)
- Browser clearing data will reset viewing history

## Future Enhancements
If you want cross-device sync:
1. Add API endpoint to store viewing history
2. Associate with user account
3. Sync on login/page load

