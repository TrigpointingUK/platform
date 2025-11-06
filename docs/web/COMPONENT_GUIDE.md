# Component Usage Guide

## Tailwind Color System

The project uses a custom green color palette matching the legacy TrigpointingUK branding:

```css
/* Primary brand color */
bg-trig-green-600  /* Backgrounds */
text-trig-green-600  /* Text */
border-trig-green-600  /* Borders */

/* Other shades available */
trig-green-50   /* Lightest */
trig-green-100
trig-green-200
trig-green-300
trig-green-400
trig-green-500
trig-green-600  /* Primary - use this as default */
trig-green-700  /* Darker for hover states */
trig-green-800
trig-green-900
trig-green-950  /* Darkest */
```

## Responsive Breakpoints

```css
/* Mobile-first approach */
className="w-full md:w-1/2 lg:w-1/3"

/* Breakpoints */
sm:   640px  /* Small tablets */
md:   768px  /* Tablets */
lg:   1024px /* Desktop */
xl:   1280px /* Large desktop */
2xl:  1536px /* Extra large */
```

## Common Patterns

### Creating a New Page

```tsx
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";

export default function MyPage() {
  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <Card>
          <h1 className="text-3xl font-bold text-trig-green-600 mb-4">
            My Page Title
          </h1>
          <p className="text-gray-700">Page content...</p>
        </Card>
      </div>
    </Layout>
  );
}
```

### Using Data Fetching Hooks

```tsx
import { useQuery } from "@tanstack/react-query";

function MyComponent() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["myData"],
    queryFn: async () => {
      const res = await fetch("/api/endpoint");
      return res.json();
    },
  });

  if (isLoading) return <Spinner />;
  if (error) return <div>Error loading data</div>;
  
  return <div>{data.value}</div>;
}
```

### Infinite Scrolling

```tsx
import { useInfiniteQuery } from "@tanstack/react-query";
import { useInView } from "react-intersection-observer";
import { useEffect } from "react";

function MyInfiniteList() {
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery({
    queryKey: ["items"],
    queryFn: ({ pageParam = 0 }) => fetchItems(pageParam),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => lastPage.nextOffset,
  });

  const { ref, inView } = useInView();

  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  const allItems = data?.pages.flatMap(page => page.items) || [];

  return (
    <div>
      {allItems.map(item => <ItemCard key={item.id} item={item} />)}
      <div ref={ref}>{isFetchingNextPage && <Spinner />}</div>
    </div>
  );
}
```

## Component Reference

### Layout Components

#### Layout
Wraps all pages with header and footer.

```tsx
<Layout>
  <YourPageContent />
</Layout>
```

#### Header
Automatically included in Layout. No need to import separately.

Features:
- Logo and site name
- Search bar (desktop)
- Navigation links
- User menu with avatar
- Mobile hamburger menu

#### Sidebar
Use on pages that need sidebar content.

```tsx
<Layout>
  <div className="flex flex-col lg:flex-row gap-6">
    <Sidebar />
    <main className="flex-1">Content</main>
  </div>
</Layout>
```

### UI Components

#### Button

```tsx
<Button variant="primary" onClick={() => alert('Clicked')}>
  Click Me
</Button>

<Button variant="secondary">Secondary</Button>
<Button variant="ghost">Ghost Style</Button>
```

#### Card

```tsx
<Card className="mb-4">
  <h2>Card Title</h2>
  <p>Card content...</p>
</Card>
```

#### Badge

```tsx
<Badge variant="good">Good Condition</Badge>
<Badge variant="damaged">Damaged</Badge>
<Badge variant="missing">Missing</Badge>
<Badge variant="unknown">Unknown</Badge>
```

#### StarRating

```tsx
<StarRating rating={4} maxRating={5} size="md" />
<StarRating rating={3} size="sm" />
```

#### Spinner

```tsx
<Spinner size="sm" />
<Spinner size="md" />
<Spinner size="lg" />
```

### Log Components

#### LogCard

```tsx
<LogCard 
  log={logData}
  userName="John Smith"
  trigName="Cleeve Cloud"
/>
```

#### LogList

```tsx
<LogList 
  logs={logsArray}
  isLoading={false}
  emptyMessage="No logs found"
/>
```

### Photo Components

#### PhotoThumbnail

```tsx
<PhotoThumbnail
  id={photo.id}
  iconUrl={photo.icon_url}
  photoUrl={photo.photo_url}
  caption={photo.caption}
  onClick={() => console.log('clicked')}
/>
```

#### PhotoGrid

```tsx
<PhotoGrid 
  photos={photosArray}
  onPhotoClick={(photo) => openLightbox(photo)}
/>
```

## Styling Tips

### Spacing

```tsx
/* Padding */
p-4   /* 1rem all sides */
px-4  /* horizontal */
py-4  /* vertical */
pt-4  /* top only */

/* Margin */
m-4, mx-4, my-4, mt-4 /* same pattern */

/* Gap (for flex/grid) */
gap-4  /* 1rem gap */
```

### Typography

```tsx
/* Size */
text-xs text-sm text-base text-lg text-xl text-2xl text-3xl text-4xl

/* Weight */
font-normal font-medium font-semibold font-bold

/* Color */
text-gray-600 text-gray-800 text-trig-green-600
```

### Flexbox

```tsx
flex flex-col    /* Column direction */
flex flex-row    /* Row direction (default) */
justify-between  /* Space between items */
items-center     /* Vertical center */
gap-4            /* Space between children */
```

### Grid

```tsx
/* Responsive grid */
grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4

/* 2 cols mobile, 3 tablet, 4 desktop */
grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4
```

### Hover & Transitions

```tsx
/* Hover states */
hover:bg-trig-green-700
hover:text-white
hover:underline

/* Transitions */
transition-colors duration-200
transition-all duration-300
```

## Best Practices

1. **Always wrap pages in Layout**
   - Ensures consistent header/footer
   - Maintains proper spacing

2. **Use semantic HTML**
   - `<main>`, `<aside>`, `<section>`, `<article>`
   - Improves accessibility

3. **Mobile-first styling**
   - Default styles for mobile
   - Add `md:` and `lg:` prefixes for larger screens

4. **Loading states**
   - Always show Spinner while loading
   - Provide empty states

5. **Error handling**
   - Graceful error messages
   - Offer retry options

6. **Accessibility**
   - Touch targets 44px+ on mobile
   - Proper alt text for images
   - Keyboard navigation support

## Common Issues

### Tailwind classes not working

Make sure you've imported app.css:
```tsx
import "./app.css";
```

### Build fails

Run type check first:
```bash
npm run type-check
```

### Colors don't match

Use `trig-green-600` (not just `green-600`) for brand colors.

### Infinite scroll not triggering

Check that:
1. `useInView` ref is attached to element
2. `useEffect` dependencies are correct
3. `hasNextPage` is true

