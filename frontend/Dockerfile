# Active Recall Monitor - Frontend Dockerfile
# Multi-stage build for production

# Stage 1: Build
FROM node:20-alpine as builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Base path the app is served from (e.g. /active-recall2/) - scopes all
# asset/API URLs so multiple instances can share one hostname without
# colliding on bare /api or /assets routes
ARG VITE_BASE=/
ENV VITE_BASE=$VITE_BASE

# Build the app
RUN npm run build


# Stage 2: Production with nginx
FROM nginx:alpine as production

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
