# QoE Application — UI (Vue.js + Vite)

This is the frontend for the QoE Application, built with Vue.js and Vite, styled with CoreUI. It connects to the FastAPI backend and provides a modern dashboard and user interface for all QoE features.

The UI enables users to interact with and manage various aspects of the QoE platform, including:
- HVAC scheduling and optimization (view, schedule, and adjust heating/cooling)
- Monitoring sensor data and building conditions
- Accessing analytics, reports, and system status
- Managing user preferences and application settings

It is designed to make complex energy and environment management tasks simple and accessible for all users.

## Features

- Modern Vue 3 SPA with Vite for fast development
- Connects to the backend API (FastAPI, see `VITE_API_BASE_URL`)
- Environment-based configuration via `.env`
- Docker Compose support for easy local development
- CoreUI components and layout

## Getting Started

### 1. Development (with Docker Compose)

```sh
docker compose up -d --build
```

The app will be available at http://localhost:5173

### 2. Development (local Node.js)

```sh
npm install
npm run dev
```

### 3. Environment Variables

All public config is set in `.env` (see `.env.example`). Key variables:

- `VITE_API_BASE_URL` — URL of the backend API (default: http://localhost:8000)
- `VITE_APP_NAME` — Application name
- `VITE_APP_ENV` — Environment (development/production)
- `VITE_API_TIMEOUT` — API request timeout (ms)
- `VITE_DEBUG_MODE` — Enable debug mode (true/false)

**Note:** All `VITE_` variables are public and bundled into the client.

## API Integration

The UI expects the backend API to be running and accessible at the URL set in `VITE_API_BASE_URL`. For local development, ensure the API is running and port 8000 is published.

## Project Structure

- `src/` — Main source code (components, views, stores, router, etc.)
- `public/` — Static assets
- `.env` — Environment variables
- `docker-compose.yml` — Docker Compose for local dev
- Clone the repo: `git clone https://github.com/coreui/coreui-free-vue-admin-template.git`

### Instalation

```bash
$ npm install
```

or

```bash
$ yarn install
```

### Basic usage

```bash
# dev server with hot reload at http://localhost:3000
$ npm run dev
```

or

```bash
# dev server with hot reload at http://localhost:3000
$ yarn dev
```

Navigate to [http://localhost:3000](http://localhost:3000). The app will automatically reload if you change any of the source files.

#### Build

Run `build` to build the project. The build artifacts will be stored in the `dist/` directory.

```bash
# build for production with minification
$ npm run build
```

or

```bash
# build for production with minification
$ yarn build
```
