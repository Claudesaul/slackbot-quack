# Deploy Quack Bot to Railway

## What We're Doing
Railway is a platform that makes deploying web apps easy. We'll deploy your Slack bot there so it runs 24/7 and students can use it.

## Step 1: Prepare Your Code
**Why:** Make sure your bot is ready for Railway deployment.

1. **Push your code to GitHub** (if you haven't already)
2. **Your code is already set up for Railway** - it will automatically detect:
   - `requirements.txt` for Python dependencies
   - `app.py` as the main file
   - Environment variables from Railway

## Step 2: Create Railway Account & Deploy

1. **Go to [railway.app](https://railway.app)**
2. **Sign up with GitHub** (easiest way)
3. **Click "New Project"**
4. **Select "Deploy from GitHub repo"**
5. **Choose your Quack repository**

Railway will automatically:
- Install Python dependencies from `requirements.txt`
- Start your bot with `python app.py`
- Give you a public URL

## Step 3: Add Postgres Database

**Why:** Your bot needs a database to store conversations.

1. **In your Railway project dashboard**
2. **Click "+ New" → "Database" → "Add PostgreSQL"**
3. **Railway automatically connects it** - no configuration needed!

The database will be automatically connected via the `DATABASE_URL` environment variable.

## Step 4: Add Environment Variables

**Why:** Your bot needs your Slack and OpenAI secrets.

1. **In Railway project → "Variables" tab**
2. **Add these variables:**

```
SLACK_BOT_TOKEN=xoxb-your-actual-token
SLACK_SIGNING_SECRET=your-actual-secret
OPENAI_API_KEY=sk-your-actual-key
PORT=3000
```

**Railway automatically provides `DATABASE_URL`** - don't add it manually.

## Step 5: Get Your Bot URL

1. **In Railway → "Settings" tab**
2. **Click "Generate Domain"** or use the provided railway.app URL
3. **Your bot URL will be:** `https://your-app-name.railway.app`

## Step 6: Connect Slack to Your Bot

**Why:** Tell Slack where your bot lives.

1. **Go to your Slack app settings** at [api.slack.com](https://api.slack.com/apps)
2. **Event Subscriptions → Enable Events**
3. **Set Request URL:** `https://your-app-name.railway.app/slack/events`
4. **Subscribe to bot events:** `app_mention` and `message.im`
5. **Save Changes**

## Step 7: Test Your Bot

- **Send a message to your bot in Slack**
- **Check Railway logs** in the "Deployments" tab to see if it's working

## Updating Your Bot

When you make code changes:

1. **Commit and push to GitHub**
2. **Railway automatically redeploys** - no manual steps needed!

## Viewing Logs & Database

**Check logs:**
- Go to Railway project → "Deployments" tab → Click latest deployment

**Access database:**
- Railway project → Click PostgreSQL service → "Data" tab
- Or use the provided connection details with any Postgres client

## If Something Goes Wrong

**Bot not responding:**
- Check Railway logs for errors
- Verify environment variables are set
- Make sure Slack webhook URL is correct

**Database issues:**
- Railway handles Postgres automatically
- Your code will create tables on first run

## Cost

- **Railway free tier:** Perfect for class use
- **Database included:** Free Postgres database
- **No credit card required** for basic usage

That's it! Your bot should now be running 24/7 on Railway with a persistent Postgres database.