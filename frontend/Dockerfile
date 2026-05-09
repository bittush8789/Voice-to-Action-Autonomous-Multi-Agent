# Use a lightweight official Nginx Alpine image
FROM nginx:alpine

# Remove default Nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy frontend source files to the Nginx serving directory
COPY frontend/ /usr/share/nginx/html/

# Copy custom Nginx configuration for proxy routing and static assets
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]
