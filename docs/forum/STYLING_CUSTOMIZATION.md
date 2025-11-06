# Forum Styling Customisation

## Overview

The phpBB forum at forum.trigpointing.uk has been customised to match the legacy forum branding and appearance.

## Customisations Applied

### 1. Custom Logo

The TrigpointingUK logo (`res/tuk_logo.png`) replaces the default phpBB logo.

**Location:** `/var/www/html/styles/prosilver/imageset/site_logo.png`

**Implementation:** The logo is copied during Docker build from `../res/tuk_logo.png` to the phpBB imageset directory.

### 2. Green Colour Theme

A custom green colour scheme replaces the default blue prosilver theme to match the legacy forum appearance.

**Location:** `/var/www/html/styles/prosilver/theme/colours_green.css`

**Colour Palette:**
- Dark Green: `#4A7729` (header, links)
- Medium Green: `#5D9732` (navigation, buttons)
- Light Green: `#6FA83B` (forum backgrounds)
- Lighter Green: `#8BC34A` (accents)

**Implementation:** 
- Custom CSS file created at `forum/assets/colours_green.css`
- Copied to phpBB theme directory during Docker build
- Applied at runtime by appending `@import url("colours_green.css");` to the main `colours.css` file
- The import is added by `docker-entrypoint.sh` on container startup

### 3. Homepage Redirect

The forum homepage redirects to the main discussion board (board ID 4) to simplify navigation.

**Implementation:** Apache rewrite rules in `forum/apache/phpbb-auth0.conf`:
```apache
RewriteRule ^index\.php$ /viewforum.php?f=4 [R=302,L]
RewriteRule ^$ /viewforum.php?f=4 [R=302,L]
```

**Behaviour:**
- Visiting `forum.trigpointing.uk/` → redirects to `forum.trigpointing.uk/viewforum.php?f=4`
- Visiting `forum.trigpointing.uk/index.php` → redirects to `forum.trigpointing.uk/viewforum.php?f=4`

## Files Modified

### Created
- `forum/assets/colours_green.css` - Green theme CSS overrides
- `docs/forum/STYLING_CUSTOMIZATION.md` - This documentation

### Modified
- `forum/Dockerfile` - Added logo and CSS copying steps
- `forum/apache/phpbb-auth0.conf` - Added homepage redirect rules
- `forum/docker-entrypoint.sh` - Added CSS import injection at startup

## Deployment

After making changes to styling:

1. **Rebuild the Docker image:**
   ```bash
   cd /home/ianh/dev/fastapi
   docker-compose build forum
   ```

2. **Restart the container:**
   ```bash
   docker-compose up -d forum
   ```

3. **Clear phpBB cache** (if needed):
   - Via Admin Panel: General > Purge the cache
   - Or via command:
     ```bash
     docker-compose exec forum rm -rf /var/www/html/cache/*
     ```

## Modifying the Theme

To adjust colours:

1. Edit `forum/assets/colours_green.css`
2. Modify the colour values in the `:root` section or specific selectors
3. Rebuild and restart the container (see Deployment section)

## Reverting to Default Theme

To revert to the default blue theme:

1. Comment out or remove the CSS import line in `forum/docker-entrypoint.sh`:
   ```bash
   # echo '@import url("colours_green.css");' >> /var/www/html/styles/prosilver/theme/colours.css
   ```

2. Rebuild and restart the container

## Notes

- The logo is sourced from the repository (`res/tuk_logo.png`) rather than the legacy forum to avoid potential security concerns
- The green theme CSS uses CSS variables for easier colour management
- The homepage redirect uses 302 (temporary) redirects rather than 301 (permanent) for flexibility
- All customisations are applied during the Docker build and container startup, making them reproducible and version-controlled

