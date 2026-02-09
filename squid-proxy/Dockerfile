ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:latest
FROM ${BUILD_FROM}

# Install Squid, OpenSSL (certs), apache2-utils (auth), and certbot
# Install Squid, OpenSSL, Auth, Certbot, Python3, Flask, and Gunicorn
RUN apk add --no-cache squid openssl apache2-utils certbot python3 py3-flask py3-gunicorn

# Copy data for add-on
# Copy data for add-on
COPY run.sh /
COPY monitoring /monitoring

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
