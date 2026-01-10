# Deploying to Railway (Single Service)

Both backend and frontend are served from one Railway service.

## Quick Deploy

### 1. Push to GitHub
```bash
cd /Users/mattiacostola/claude/prediction-arbitrage
git add .
git commit -m "Prepare for Railway deployment"
git push
```

### 2. Create Railway Project
1. Go to [railway.app](https://railway.app)
2. Click **New Project** → **Deploy from GitHub**
3. Select your repository
4. Set **Root Directory** to: `bot_tracker`

### 3. Add Persistent Volume
1. In your service, go to **Settings** → **Volumes**
2. Click **Add Volume**
3. Set mount path: `/data`

### 4. Add Environment Variables
In **Variables** tab, add:
```
DATA_DIR=/data
```

### 5. Deploy!
Railway will automatically:
- Install Python dependencies
- Install Node.js and build the React dashboard
- Start the server

Your app will be live at: `https://your-project.railway.app`

---

## What Gets Deployed

```
┌─────────────────────────────────────────┐
│  Railway Service                        │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  FastAPI (Python)               │   │
│  │  ├── /api/*  → REST endpoints   │   │
│  │  └── /*      → React Dashboard  │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  Volume: /data                  │   │
│  │  ├── trades.json                │   │
│  │  ├── prices.json                │   │
│  │  └── positions.json             │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| DATA_DIR | Yes | Path for data storage (`/data`) |
| PORT | Auto | Set by Railway automatically |

## Local Development

```bash
# Terminal 1: Backend
cd bot_tracker
python -m bot_tracker.main

# Terminal 2: Frontend (dev mode)
cd bot_tracker/dashboard
npm run dev
```

## Troubleshooting

**Build fails?**
- Check that `dashboard/package.json` exists
- Verify `requirements.txt` has all dependencies

**Data not persisting?**
- Make sure you added a Volume with mount path `/data`
- Check that `DATA_DIR=/data` is set in environment variables
