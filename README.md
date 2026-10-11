# Musk Wire

A personal news app for everything Elon Musk: Tesla, SpaceX, Starlink, Neuralink, Terafab, xAI/X, The Boring Company and Musk himself.

- Installs on your iPhone home screen and on your computer like a regular app
- Checks Google News every 15 minutes and keeps the last 45 days of headlines
- Flags big stories (deliveries, earnings, launches, recalls, deals, lawsuits) as **Major**
- Optional phone alerts for Major stories through the free ntfy app
- Works offline with the last headlines it saved
- Runs entirely on a free GitHub account; no servers, no API keys, no Claude needed

## One-time setup (about 10 minutes)

### 1. Put it on GitHub
1. Sign in at github.com (or create a free account).
2. Create a new repository named `musk-wire`. Make it **Public** (free GitHub Pages hosting needs a public repo).
3. On the new repo page, choose **uploading an existing file**, then drag in everything from this folder.
   - The `.github` folder is hidden on Mac. In Finder press **Cmd + Shift + .** to show it, and make sure it gets uploaded.
4. Click **Commit changes**.

### 2. Turn on the website
1. In the repo, go to **Settings → Pages**.
2. Under **Build and deployment → Source**, choose **GitHub Actions**.
3. Go to the **Actions** tab. If asked, click **I understand my workflows, go ahead and enable them**.
4. Click **Update headlines → Run workflow**. After a minute or two it turns green.
5. Your app is now live at `https://YOUR-GITHUB-NAME.github.io/musk-wire/`

### 3. Install it on your iPhone
1. Open that link in **Safari**.
2. Tap **Share**, then **Add to Home Screen**, then **Add**.

It opens full-screen with its own icon, like any other app.

### 4. Install it on your computer
Open the link in **Chrome** or **Edge** and click the install icon at the right end of the address bar. On a Mac with Safari: **File → Add to Dock**.

### 5. Optional: phone alerts for Major news
1. Install **ntfy** from the App Store.
2. In ntfy, tap **+** and subscribe to a topic name only you would guess, like `muskwire-7f3k9q2x`. Anyone who knows the name can read the alerts, so make it random.
3. In your GitHub repo go to **Settings → Secrets and variables → Actions → New repository secret**.
   Name: `NTFY_TOPIC`. Value: your topic name.

You'll get at most 5 alerts per check, only for headlines marked Major. Tapping one opens the article.

## Changing what it follows
Edit `FEEDS` in `scripts/fetch_news.py`. Each line is a Google News search. The words that make a story Major are in `MAJOR` in the same file.

## Adding upcoming events
The "Coming up" countdowns come from the `events` list at the bottom of `data/news.json`. Add entries like:

```json
{"company": "spacex", "title": "Starship Flight 15", "date": "2026-11-05", "note": "launch window", "url": "https://..."}
```

Companies: `tesla`, `spacex`, `starlink`, `neuralink`, `terafab`, `ai`, `boring`, `musk`. Past events drop off on their own.

## Good to know
- GitHub sometimes delays scheduled runs by 5–15 minutes during busy hours.
- GitHub pauses scheduled workflows on repos with no activity for 60 days. The app's own updates count as activity, but if updates ever stop, open **Actions** and re-enable the workflow.
- Headlines link to the original publisher. Some sites (Bloomberg, WSJ) have paywalls.
