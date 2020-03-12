FROM nginx:1.12.2-alpine
ADD proxy/nginx.conf /etc/nginx/nginx.conf
RUN mkdir -p /var/www
ADD src/client/dist/ /usr/share/nginx/html/