# Build stage
FROM node:20-alpine as build

WORKDIR /app

# Copy package files
COPY ./frontend/admin-panel/package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY ./frontend/admin-panel .

# Build app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx config
COPY ./frontend/admin-panel/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
