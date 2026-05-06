# Base stage for dependencies
FROM node:20-alpine as base
WORKDIR /app
COPY package*.json ./
RUN npm install

# Development stage
FROM base as dev
COPY . .
# No need to build, command will be npm run dev in compose
EXPOSE 5173

# Build stage for production
FROM base as build
COPY . .
RUN npm run type-check -- --pretty
RUN npm run build -- --debug

# Production stage
FROM nginx:stable-alpine as prod

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
