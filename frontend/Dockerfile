# --- Build stage ---
FROM node:22-alpine AS builder

LABEL maintainer="info@lukas-bisdorf.de" \
      org.opencontainers.image.description="JF Manager Frontend" \
      org.opencontainers.image.source="https://github.com/Jugendfeuerwehr-Manager/JF-Manager"

WORKDIR /app

# Copy dependency files
COPY package*.json ./

# Install ALL dependencies (including devDependencies needed for build)
RUN npm ci && \
    npm cache clean --force

# Copy application source
COPY . .

# Build the application
RUN npm run build

# --- Nginx stage ---
FROM nginx:1.27-alpine AS production

# Add build arguments for labels
ARG BUILD_DATE
ARG VCS_REF

LABEL maintainer="info@lukas-bisdorf.de" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.description="JF Manager Frontend - Production" \
      org.opencontainers.image.source="https://github.com/Jugendfeuerwehr-Manager/JF-Manager"

# Remove default nginx configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Create non-root user for nginx
RUN addgroup -g 101 -S nginx && \
    adduser -S -D -H -u 101 -h /var/cache/nginx -s /sbin/nologin -G nginx -g nginx nginx 2>/dev/null || true && \
    chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chmod -R 755 /usr/share/nginx/html

# Create directories for static and uploads
RUN mkdir -p /static /uploads && \
    chown -R nginx:nginx /static /uploads

# Create PID directory
RUN mkdir -p /var/run && \
    chown -R nginx:nginx /var/run

# Switch to non-root user
USER nginx

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/health || exit 1

EXPOSE 80 443

STOPSIGNAL SIGTERM

CMD ["nginx", "-g", "daemon off;"]
