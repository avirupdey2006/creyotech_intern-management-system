FROM nginx:1.27-alpine

RUN apk add --no-cache curl openssl

COPY nginx.conf /etc/nginx/nginx.conf
COPY certs/ims.crt /etc/nginx/certs/ims.crt
COPY certs/ims.key /etc/nginx/certs/ims.key

RUN chmod 600 /etc/nginx/certs/ims.key && \
    chmod 644 /etc/nginx/certs/ims.crt

EXPOSE 80 443

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1/nginx-health || exit 1