FROM node:22-alpine
WORKDIR /app
COPY package.json ./
COPY swagger.yaml ./
RUN npm install --omit=dev
COPY start.js ./
CMD ["node", "start.js"]
