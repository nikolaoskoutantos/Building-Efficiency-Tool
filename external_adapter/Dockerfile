FROM node:18-alpine

# Create app directory and set permissions
RUN mkdir -p /home/node/app/node_modules && chown -R node:node /home/node/app
RUN apt-get update && apt-get install -y curl
WORKDIR /home/node/app

# Copy package files as the node user
COPY --chown=node:node package.json package-lock.json ./

USER node

# Install dependencies
RUN npm install

# Copy the rest of your app
COPY --chown=node:node . .

# Optional: expose port 8080
ENV PORT=8080

# Run the app
CMD ["node", "app.js"]
