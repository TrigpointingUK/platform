FROM mediawiki:1.43

WORKDIR /var/www/html

# tools + build deps (PHP provides $PHPIZE_DEPS)
RUN set -eux; \
apt-get update; \
apt-get install -y --no-install-recommends git unzip $PHPIZE_DEPS; \
pecl install redis; \
docker-php-ext-enable redis; \
    apt-get purge -y --auto-remove -o APT::Autoremove::RecommendsImportant=false $PHPIZE_DEPS; \
    rm -rf /var/lib/apt/lists/*

# Clone MediaWiki extensions
RUN set -eux; \
  cd extensions; \
  git clone -b REL1_43 https://gerrit.wikimedia.org/r/mediawiki/extensions/PluggableAuth; \
  git clone -b REL1_43 https://gerrit.wikimedia.org/r/mediawiki/extensions/OpenIDConnect; \
  git clone -b REL1_43 https://gerrit.wikimedia.org/r/mediawiki/extensions/ChangeAuthor; \
  git clone -b REL1_43 https://gerrit.wikimedia.org/r/mediawiki/extensions/MobileFrontend; \
  git clone https://github.com/edwardspec/mediawiki-aws-s3 AWS

# Install composer and update dependencies for OIDC/AWS extensions
COPY composer.local.json /var/www/html/
RUN php -r "copy('https://getcomposer.org/installer','composer-setup.php');" \
 && php composer-setup.php --install-dir=/usr/local/bin --filename=composer \
 && composer update -n --no-dev --no-security-blocking

RUN a2enmod rewrite
COPY apache-shorturl-root.conf /etc/apache2/conf-available/shorturl-root.conf
RUN a2enconf shorturl-root
 

# Bake parameterised LocalSettings.php into image
COPY LocalSettings.php /var/www/html/LocalSettings.php
COPY trig-assets/ /var/www/html/trig-assets/

EXPOSE 80
