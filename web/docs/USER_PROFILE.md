# User Profile Page Implementation

## Overview
A user profile page with inline editing capabilities for authenticated users viewing their own profile.

## Features

### 1. Three-Section Layout
- **Top**: User information (name, firstname, surname, homepage, about) with member_since date and key stats
- **Middle**: Prominent display of total trigs logged and total logs
- **Bottom**: Four-column breakdown of statistics (responsive: 4→2→1 columns)

### 2. Inline Editing (Own Profile Only)
- **Pencil icon** appears on hover for editable fields
- Click pencil to enter edit mode
- **Auto-save on blur** - saves when user clicks away or tabs out
- ESC key cancels editing
- Enter key saves (single-line fields only)
- Visual feedback with "Saving..." indicator

### 3. Routes
- `/profile` - View your own profile with editing enabled
- `/profile/:userId` - View any user's profile by ID

### 4. Data Fetching
- Fetches from `GET /v1/users/:userId?include=stats,breakdown`
- Updates via `PATCH /v1/users/me`
- Automatic cache invalidation after updates

## Files Created

### Components
- **`EditableField.tsx`** - Reusable inline editing component with pencil icon
  - Supports single-line and multiline (textarea) fields
  - Handles async save with error recovery
  - Shows saving state
  - Keyboard shortcuts (Enter to save, ESC to cancel)

### Hooks
- **`useUserProfile.ts`** - React Query hook for fetching user data
  - Fetches user with stats and breakdown
  - Type-safe user profile interface
  - Separate `updateUserProfile` function for PATCH requests

### Routes
- **`UserProfile.tsx`** - Main profile page component
  - Responsive grid layout
  - Conditional editing based on `isOwnProfile`
  - Four breakdown cards with sorted statistics
  - Empty states for missing data

## UX Decisions

### Why Pencil Icon + Auto-Save?
1. **Clean UI**: No ugly text boxes when just viewing
2. **Discoverable**: Pencil appears on hover making editing obvious
3. **Efficient**: Auto-save on blur means no "Save" button needed
4. **Familiar**: Common pattern in modern web apps (Notion, Trello, etc.)

### Responsive Breakdowns
- **Desktop (lg)**: 4 columns
- **Tablet (sm)**: 2 columns
- **Mobile**: 1 column

Each breakdown card shows:
- Current Use (Triangulation, Navigation, etc.)
- Historic Use (Primary, Secondary, etc.)
- Type (grouped by category: Pillar, FBM, Survey Mark, etc.)
- Condition (Good, Damaged, Missing, etc.)

## API Integration

### GET /v1/users/:userId
```typescript
{
  id: number;
  name: string;
  firstname: string;
  surname: string;
  homepage: string | null;
  about: string;
  member_since: string | null;
  stats?: {
    total_logs: number;
    total_trigs_logged: number;
  };
  breakdown?: {
    by_current_use: Record<string, number>;
    by_historic_use: Record<string, number>;
    by_type: Array<{
      category_code: string;
      category_name: string;
      sort_order: number;
      types: Array<{
        type_code: string;
        type_name: string;
        count: number;
      }>;
    }>;
    by_condition: Record<string, number>;
  };
}
```

### PATCH /v1/users/me
Accepts partial updates:
```typescript
{
  name?: string;          // max 30 chars
  firstname?: string;     // max 30 chars
  surname?: string;       // max 30 chars
  homepage?: string;      // max 255 chars
  about?: string;         // unlimited
}
```

## Future Enhancements
- Add photo upload for profile picture
- Add email change with verification
- Add preferences editing
- Add activity timeline/recent logs
- Add badges/achievements display
- Add "View public profile" link for own profile

