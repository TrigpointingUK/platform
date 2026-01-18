#!/bin/sh
set -e
# let official script init PHP ext, etc.
[ -x /usr/local/bin/docker-php-entrypoint ] && docker-php-entrypoint php-fpm >/dev/null 2>&1 || true

# Replace phpBB directories with symlinks to EFS (support two layouts)
# Note: Symlinks must be owned by www-data due to Linux's protected_symlinks
# security feature. /var/www/html has the sticky bit set, and symlinks owned
# by root cannot be followed by www-data in sticky directories.
link_dir() {
    target_name="$1"    # e.g. files | store | images/avatars/upload
    dest="/var/www/html/${target_name}"
    src_a="/mnt/phpbb/phpbb/${target_name}"
    src_b="/mnt/phpbb/${target_name}"

    if [ -d "$src_a" ]; then
        echo "Linking ${dest} -> ${src_a}"
        rm -rf "$dest"
        ln -sf "$src_a" "$dest"
        chown -h www-data:www-data "$dest"
    elif [ -d "$src_b" ]; then
        echo "Linking ${dest} -> ${src_b}"
        rm -rf "$dest"
        ln -sf "$src_b" "$dest"
        chown -h www-data:www-data "$dest"
    else
        echo "EFS path not found for ${target_name} (checked ${src_a} and ${src_b})"
    fi
}

echo "Setting up EFS symlinks (files, store, avatars)..."
link_dir files
link_dir store
link_dir images/avatars/upload

# Attempt to create compatibility symlinks for legacy avatar filenames
if [ -n "${PHPBB_DB_HOST}" ] && [ -n "${PHPBB_DB_NAME}" ] && [ -n "${PHPBB_DB_USER}" ]; then
    echo "Reconciling legacy avatar filenames with uploaded files..."
    cat > /tmp/fix_avatars.php <<'PHP'
<?php
error_reporting(E_ALL);
ini_set('display_errors', '1');

$host = getenv('PHPBB_DB_HOST');
$db = getenv('PHPBB_DB_NAME');
$user = getenv('PHPBB_DB_USER');
$pass = getenv('PHPBB_DB_PASS');
$prefix = getenv('PHPBB_TABLE_PREFIX') ?: 'phpbb_';
$uploadDir = '/var/www/html/images/avatars/upload';

$mysqli = @new mysqli($host, $user, $pass, $db);
if ($mysqli->connect_errno) {
    fwrite(STDERR, "DB connect failed: {$mysqli->connect_error}\n");
    exit(0);
}

$sql = "SELECT user_id, user_avatar FROM `{$prefix}users` WHERE user_avatar IS NOT NULL AND user_avatar != ''";
$res = $mysqli->query($sql);
if (!$res) { exit(0); }

function pick_best_candidate(array $files, int $userId, ?string $wantExt): ?string {
    if (empty($files)) return null;
    $scored = [];
    foreach ($files as $path) {
        $base = basename($path);
        // prefer desired extension
        $ext = strtolower(pathinfo($base, PATHINFO_EXTENSION));
        $extScore = ($wantExt && $ext === strtolower($wantExt)) ? 10 : 0;
        // prefer largest size number before extension like *_200.jpg or *_448.jpg
        $sizeScore = 0;
        if (preg_match('/_(\\d+)\\.[^.]+$/', $base, $m)) {
            $sizeScore = (int)$m[1];
        }
        $scored[] = [$extScore + $sizeScore, $path];
    }
    usort($scored, function($a, $b) { return $b[0] <=> $a[0]; });
    return $scored[0][1] ?? null;
}

while ($row = $res->fetch_assoc()) {
    $userId = (int)$row['user_id'];
    $avatar = $row['user_avatar'];
    if (!$userId || !$avatar) continue;

    $expected = $uploadDir . '/' . $avatar;
    if (file_exists($expected)) continue;

    $wantExt = pathinfo($avatar, PATHINFO_EXTENSION);
    $pattern = $uploadDir . '/*_' . $userId . '.*';
    $candidates = glob($pattern) ?: [];
    if (empty($candidates)) continue;

    $best = pick_best_candidate($candidates, $userId, $wantExt);
    if ($best) {
        $target = basename($best);
        // create symlink with expected legacy name pointing to actual file
        @symlink($target, $expected);
        echo "Linked {$avatar} -> {$target}\n";
    }
}

$res->free();
$mysqli->close();
PHP
    php /tmp/fix_avatars.php || true
fi

#if [ ! -f /var/www/html/config.php ]; then
cat > /var/www/html/config.php <<PHP
<?php
\$dbms = 'phpbb\\db\\driver\\mysqli';
\$dbhost = '${PHPBB_DB_HOST}';
\$dbport = '';
\$dbname = '${PHPBB_DB_NAME}';
\$dbuser = '${PHPBB_DB_USER}';
\$dbpasswd = '${PHPBB_DB_PASS}';
\$table_prefix = '${PHPBB_TABLE_PREFIX}';
\$phpbb_adm_relative_path = 'adm/';
\$acm_type = 'phpbb\\cache\\driver\\file';
\$load_extensions = '';

@define('PHPBB_INSTALLED', true);
@define('PHPBB_ENVIRONMENT', 'production');
PHP
chown www-data:www-data /var/www/html/config.php
#fi


ls -al /var/www/html
ls -alR /var/www/html/files
ls -alR /var/www/html/store
ls -alR /var/www/html/images/avatars/upload
cat /var/www/html/config.php

find /mnt/phpbb -type d -print

# Apply custom green theme by appending import to colours.css
if [ -f /var/www/html/styles/prosilver/theme/colours.css ]; then
    echo "Applying custom green theme..."
    # Check if import already exists to avoid duplicates
    if ! grep -q "colours_green.css" /var/www/html/styles/prosilver/theme/colours.css; then
        if [ -n "${ASSET_VERSION}" ]; then
            echo "@import url(\"colours_green.css?v=${ASSET_VERSION}\");" >> /var/www/html/styles/prosilver/theme/colours.css
        else
            echo '@import url("colours_green.css");' >> /var/www/html/styles/prosilver/theme/colours.css
        fi
    fi
fi

# Remove installer if present to prevent install wizard
if [ -d /var/www/html/install ]; then
    rm -rf /var/www/html/install
fi

# php-fpm not used in apache image; start apache
exec apache2-foreground
