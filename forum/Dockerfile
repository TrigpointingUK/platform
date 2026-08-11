# Build phpBB container image
# Includes custom TUK branding (logo, green theme) and Auth0 SSO integration
FROM php:8.2-apache
ARG PHPBB_VERSION=3.3.15

WORKDIR /var/www/html

# Requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    unzip libpng-dev libjpeg-dev libfreetype6-dev libzip-dev ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN docker-php-ext-configure gd --with-freetype --with-jpeg \
 && docker-php-ext-install -j"$(nproc)" mysqli pdo pdo_mysql gd zip opcache


# Install phpBB
RUN set -eux; \
base="https://download.phpbb.com/pub/release/3.3/${PHPBB_VERSION}"; \
mkdir -p /tmp/phpBB3; \
curl -fSL "$base/phpBB-${PHPBB_VERSION}.tar.bz2" -o /tmp/phpbb.tar.bz2; \
tar -xjf /tmp/phpbb.tar.bz2 -C /tmp; \
mv /tmp/phpBB3/* /var/www/html/; \
rm -rf /tmp/phpbb.zip /tmp/phpbb.tar.bz2 /tmp/phpBB3; \
chown -R www-data:www-data /var/www/html


# Copy the Auth0 extension and enable rewrite/conf
COPY ext/ /var/www/html/ext/
COPY apache/phpbb-auth0.conf /etc/apache2/conf-available/phpbb-auth0.conf
COPY apache/mpm-tuning.conf /etc/apache2/conf-available/mpm-tuning.conf

# Copy custom branding and styling (PNG logo, favicon, and green theme CSS)
COPY assets/tuk_logo.png /var/www/html/styles/prosilver/theme/images/site_logo.png
COPY assets/tuk_logo.png /var/www/html/styles/prosilver/imageset/site_logo.png
COPY assets/colours_green.css /var/www/html/styles/prosilver/theme/colours_green.css
COPY assets/favicon.ico /var/www/html/favicon.ico

RUN a2enmod rewrite \
&& a2enconf phpbb-auth0 \
&& a2enconf mpm-tuning \
&& chown -R www-data:www-data /var/www/html/ext \
&& chown www-data:www-data /var/www/html/styles/prosilver/theme/images/site_logo.png \
&& chown www-data:www-data /var/www/html/styles/prosilver/imageset/site_logo.png \
&& chown www-data:www-data /var/www/html/styles/prosilver/theme/colours_green.css \
&& chown www-data:www-data /var/www/html/favicon.ico


COPY ext_diag.php /var/www/html/ext_diag.php
COPY ext_auth0_diag.php /var/www/html/ext_auth0_diag.php
COPY clear_container_cache.php /var/www/html/clear_container_cache.php
COPY debug_oauth.php /var/www/html/debug_oauth.php
RUN chmod +x /var/www/html/ext_diag.php /var/www/html/ext_auth0_diag.php /var/www/html/clear_container_cache.php /var/www/html/debug_oauth.php

# Add entrypoint to create config.php and link EFS directories
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
