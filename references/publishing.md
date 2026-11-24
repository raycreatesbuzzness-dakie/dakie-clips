# Uploading clips automatically (YouTube, Instagram, Facebook, TikTok)

Dakie Clips can upload your finished clips with their titles, descriptions and hashtags, using each
platform's **official API**. Everything here is **free**: you create your own free developer "app" on
each platform once, and your Mac talks to the platforms directly. No third-party service is involved.

**Nothing is ever uploaded without your approval.** After packaging, Claude shows an upload plan
(every clip × platform, with its title and copyright notes) and waits until you reply with that plan's
ID. Every upload is logged, so the same clip is never posted twice.

| Platform | What happens | One-time setup |
|---|---|---|
| YouTube Shorts | Uploaded with title, description, tags; public, unlisted or private (your choice) | ~10 min (Google Cloud) |
| Instagram Reels | Posted with caption and hashtags | ~15 min (Meta app, shared with Facebook) |
| Facebook Reels | Posted to your Facebook Page with caption | same Meta app |
| TikTok | **Direct Post** to your profile with caption and hashtags once TikTok approves your app; until then your drafts (or "Only me" posts if your TikTok account is private) | ~15 min (TikTok developer app) + TikTok's app review for public posts |

Logins are saved in `~/DakieClips/accounts/` (readable only by your Mac user, never uploaded to GitHub).
**Run the setup commands yourself in Terminal.** They ask for secrets at a hidden prompt; never paste
secrets or tokens into a chat.

Check what's connected at any time:

```bash
dakie publish status
```

---

## YouTube (free, up to 100 uploads a day)

1. Go to **console.cloud.google.com** and create a project (e.g. "Dakie Clips").
2. **APIs & Services → Library** → search **YouTube Data API v3** → **Enable**.
3. **Google Auth Platform → Branding**: app name "Dakie Clips", your email as support and developer
   contact. **Audience**: User type **External**, then **Publish app** (set it to *In production*).
   - Why production: in *Testing* mode Google expires your login every 7 days.
   - You'll see a "Google hasn't verified this app" screen when you sign in. That's expected for a
     personal app: click **Advanced → Go to Dakie Clips (unsafe)**. It's your own app.
4. **Clients → Create client → Application type: Desktop app** → **Create** → **Download JSON**.
   - If you made a **Web application** client instead, that works too: open it, add the
     **Authorized redirect URI** `http://127.0.0.1:8765` (exactly, no slash at the end), and **Save**.
   - Don't reuse a client made for another service (e.g. Composio). Its redirect addresses point elsewhere,
     and Google shows `redirect_uri_mismatch`.
   - **No domain needed for step 3:** Google wants a homepage and privacy-policy link before you can
     publish the app. You can use this project's free pages:
     `https://raycreatesbuzzness-dakie.github.io/dakie-clips/` and `.../dakie-clips/privacy/`, with
     authorized domain `raycreatesbuzzness-dakie.github.io`, or turn on GitHub Pages for your own fork
     (Settings → Pages → Branch `main`, folder `/docs`).
5. In Terminal:
   ```bash
   dakie publish setup youtube --client-secret-file ~/Downloads/client_secret_XXXX.json
   ```
   Your browser opens; sign in with the Google account that owns your channel and allow access.
   Terminal then prints `YouTube connected: <your channel>`.
6. Default privacy is **public**. Change it with `dakie publish privacy unlisted` (or `private`).

## Instagram + Facebook (one free Meta app for both)

**Before you start:** your Instagram must be a **Business or Creator** account (Instagram app →
Settings → Account type and tools) and **linked to a Facebook Page** you manage (Facebook Page →
Settings → Linked accounts → Instagram).

1. Go to **developers.facebook.com** → **My Apps → Create App**. Pick the use case for managing a
   Page and Instagram content (or **Other → Business**). Leave the app in **Development** mode: that's
   enough to post to accounts you own.
2. **App settings → Basic**: note the **App ID**, click **Show** next to **App Secret**.
3. Open **Graph API Explorer** (Tools menu). Select your app, choose **User Token**, and add these
   permissions: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`,
   `instagram_content_publish`, `business_management`. Click **Generate Access Token** and approve
   your Page and Instagram account.
4. In Terminal:
   ```bash
   dakie publish setup meta
   ```
   Paste the App ID, the App Secret and the token when asked (they're hidden). If you manage several
   Pages, it lists them; run again with `--page-id <id>`.
5. The Instagram login lasts about **60 days**. `dakie publish status` warns a week before it expires;
   then repeat steps 3–4.

## TikTok (free; Direct Post)

1. Go to **developers.tiktok.com**, log in, **Manage apps → Connect an app**.
2. Add the products **Login Kit** and **Content Posting API**. Inside Content Posting API, turn on
   **Direct Post**. Request the scopes `user.info.basic`, `video.upload` and `video.publish`.
3. Platform **Desktop**; redirect URI: `http://localhost:8765/callback/`
4. Until TikTok reviews your app, use **Sandbox** (set it up the same way, including Direct Post and
   `video.publish`), add your own TikTok account under **Sandbox → Target users**, and click
   **Apply changes**.
5. Note the **Client Key** and **Client Secret**, then in Terminal:
   ```bash
   dakie publish setup tiktok
   ```
   Sign in to TikTok in the browser window that opens and allow access (it now also asks to post videos).
   Already connected before? Run it again once so the login gets the new `video.publish` permission.

**What happens on upload:** each approved clip is posted straight to your profile with its full
caption, hashtags and SEO text. Before posting, Dakie Clips checks your TikTok account (name, which
privacy options TikTok offers you, whether you turned off comments/Duet/Stitch) and shows it all in
the upload plan, together with TikTok's Music Usage Confirmation, which you accept by approving the plan.

**Until TikTok approves your app**, TikTok only allows Direct Post when your whole TikTok **account is
private**, and posts arrive as "Only me". With a public account, Dakie Clips automatically sends each
approved clip to your TikTok **drafts** instead (open the notification, paste the caption it shows,
choose Everyone, Post). To get fully automatic public posting:
1. In the developer portal, switch to **Production** and submit the app for review (the answers are in
   `references/tiktok-audit.md`; TikTok wants a short screen recording of the upload plan and a post).
2. When TikTok approves it, run:
   ```bash
   dakie publish tiktok audited yes
   dakie publish privacy tiktok public        # or friends | followers | private
   ```

Other settings:
```bash
dakie publish tiktok comments off            # or on; also: duet on|off, stitch on|off
dakie publish tiktok mode inbox              # old flow: send to your TikTok drafts instead
```

TikTok's developer site changes often. If a menu name differs, look for the same product names.

---

## Using it

After `dakie package`, Claude offers the upload plan automatically
(`"publish": {"offer_after_package": true}` in `~/DakieClips/config.json`). You can also ask any time,
e.g. "upload clips 1–5 to YouTube and TikTok". Under the hood:

```bash
dakie publish plan <project> [--clips 1,2,3] [--platforms youtube,instagram,facebook,tiktok]
dakie publish run <project> --approve <plan id>      # only after you approved that ID
dakie publish run <project> --approve <plan id> --platforms tiktok   # retry just part of an approved plan
```

- Turn a platform off or on: `dakie publish disable tiktok` / `dakie publish enable tiktok`
- Results and links: `<project>/final/publish_log.json`
- Clips with a 🔴 copyright item are never put in a plan unless you explicitly ask for it.
- A plan is valid for 24 hours, and a clip that changes after approval is skipped until you approve again.

**Copyright still applies.** Uploading is easy now, so the rule matters more: only publish clips of
streamers who allow it (a clipping program, Discord rule or written OK). Repeated claims or strikes can
restrict or remove your accounts.
