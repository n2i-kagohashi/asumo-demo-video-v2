FROM node:22-alpine

WORKDIR /app
COPY server.mjs ./server.mjs
COPY index.html narration-bookends.wav robots.txt ./public/
COPY deck/ ./public/deck/

ENV NODE_ENV=production PORT=8080
EXPOSE 8080
USER node
CMD ["node", "server.mjs"]
