ARG PHP_CLI_IMAGE=php:8.4-cli-bookworm

FROM ${PHP_CLI_IMAGE}

WORKDIR /var/www/html

# 使用国内 Debian HTTPS 源（部分网络对 HTTP InRelease 返回 NOSPLIT）
ARG DEBIAN_MIRROR=https://mirrors.ustc.edu.cn
RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i "s|http://deb.debian.org/debian|${DEBIAN_MIRROR}/debian|g" /etc/apt/sources.list.d/debian.sources; \
        sed -i "s|http://security.debian.org/debian-security|${DEBIAN_MIRROR}/debian-security|g" /etc/apt/sources.list.d/debian.sources; \
        sed -i "s|https://deb.debian.org/debian|${DEBIAN_MIRROR}/debian|g" /etc/apt/sources.list.d/debian.sources; \
        sed -i "s|https://security.debian.org/debian-security|${DEBIAN_MIRROR}/debian-security|g" /etc/apt/sources.list.d/debian.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
        sed -i "s|http://deb.debian.org/debian|${DEBIAN_MIRROR}/debian|g" /etc/apt/sources.list; \
        sed -i "s|http://security.debian.org/debian-security|${DEBIAN_MIRROR}/debian-security|g" /etc/apt/sources.list; \
    fi

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        git \
        libfreetype6-dev \
        libjpeg62-turbo-dev \
        libonig-dev \
        libpng-dev \
        libpq-dev \
        libsqlite3-dev \
        libzip-dev \
        postgresql-client \
        unzip \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install \
        gd \
        mbstring \
        pdo_pgsql \
        pdo_sqlite \
        pcntl \
        zip \
    && mkdir -p /usr/src/php/ext \
    && curl -fsSL https://github.com/phpredis/phpredis/archive/refs/tags/6.2.0.tar.gz \
        | tar xz -C /usr/src/php/ext \
    && mv /usr/src/php/ext/phpredis-6.2.0 /usr/src/php/ext/redis \
    && docker-php-ext-install redis \
    && rm -rf /var/lib/apt/lists/* /usr/src/php/ext/redis

COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

ENV COMPOSER_ALLOW_SUPERUSER=1 \
    COMPOSER_MEMORY_LIMIT=-1 \
    COMPOSER_PROCESS_TIMEOUT=2000

ARG COMPOSER_PACKAGIST_MIRROR=
RUN if [ -n "${COMPOSER_PACKAGIST_MIRROR}" ]; then \
        composer config -g repo.packagist composer "${COMPOSER_PACKAGIST_MIRROR}"; \
    fi

COPY composer.json composer.lock ./
RUN composer install --no-interaction --prefer-dist --no-dev --no-scripts

COPY . .

# 仅刷新 autoload；不调 artisan / composer 脚本（镜像为 --no-dev，构建期无 Boost 等 dev 包）
RUN composer dump-autoload --optimize --no-interaction --no-scripts

COPY docker/php/opcache.ini /usr/local/etc/php/conf.d/99-opcache.ini
COPY docker/php/opcache-dev.ini /usr/local/etc/php/conf.d/zz-opcache-dev.ini
COPY docker/php/php-docker-overrides.ini /usr/local/etc/php/conf.d/99-overrides.ini

RUN cp docker/entrypoint.sh /usr/local/bin/geoflow-entrypoint \
    && chmod +x /usr/local/bin/geoflow-entrypoint

ENTRYPOINT ["/usr/local/bin/geoflow-entrypoint"]
CMD ["php", "artisan", "about"]
