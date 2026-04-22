# Build stage
FROM node:20-alpine as build

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./
COPY package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the application with verbose output
RUN npm run type-check -- --pretty
RUN npm run build -- --debug

# Production stage
FROM nginx:stable-alpine

# Delete old static files before copying new ones
RUN rm -rf /usr/share/nginx/html/*
# Copy built assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Nginx config is mounted via docker-compose volume

# Ensure the directory structure exists for Django static files
RUN mkdir -p /usr/src/app/xadras/staticfiles/admin/

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
