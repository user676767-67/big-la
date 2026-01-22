# UCLA Gym Activity Tracker

Collects gym zone occupancy data from UCLA Recreation every 15 minutes and generates hourly averages.

## Tracked Zones

**John Wooden Center (JWC):**
- Free Weight Zone
- Advanced Circuit Zone
- Novice Circuit Zone

**Bruin Fitness Center (BFIT):**
- Free Weight & Squat Zones
- Cable, Synergy Zones
- Selectorized Zone

## Deploy to Railway (Easy Steps)

### Step 1: Upload to GitHub
1. Go to [github.com](https://github.com) and sign in
2. Click the **+** button → **New repository**
3. Name it `ucla-gym-tracker`
4. Keep it **Public** or **Private** (your choice)
5. Click **Create repository**
6. Open Terminal and run these commands:
   ```bash
   cd ~/Documents/ucla-gym-tracker
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/ucla-gym-tracker.git
   git push -u origin main
   ```

### Step 2: Deploy on Railway
1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Select your `ucla-gym-tracker` repository
4. Railway will automatically detect the settings and start deploying
5. Wait for the green **Success** status

### Step 3: Check It's Working
1. In Railway, click on your project
2. Go to the **Logs** tab
3. You should see messages like:
   ```
   Collected 6 zone readings
   Next collection in 15 minutes
   ```

## Get Your Data

To download your collected data, you'll need to connect to the Railway service. 
The data is stored in a SQLite database (`gym_data.db`) and can be exported to CSV.

**Note:** Railway's free tier may have limitations. Consider upgrading if needed for 24/7 operation.

## Operating Hours

| Gym | Mon-Thu | Friday | Sat-Sun |
|-----|---------|--------|---------|
| JWC | 5:15 AM - 1:00 AM | 5:15 AM - 10:00 PM | Closed |
| BFIT | 6:00 AM - 12:00 AM | 6:00 AM - 9:00 PM | Closed |
