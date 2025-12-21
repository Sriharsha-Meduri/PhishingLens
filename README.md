# PhishingLens Frontend

## Quick Start

```bash
npm install
npm run dev
```

## Environment

- `VITE_API_BASE_URL` → Base URL of the deployed backend (for example `https://phishinglens-api.serveo.net`).
- `VITE_RADAR_API_TOKEN` → Cloudflare Radar bearer token for the live globe feature.

Create an `.env.local` file (or edit the existing one) with the values above before running `npm run dev`, `npm run build`, or `npm run preview`.

## Production Build

```bash
npm run build
npm run preview
```
