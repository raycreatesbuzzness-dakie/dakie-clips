"""Publish finished clips to YouTube, Instagram, Facebook and TikTok through their official APIs.

Nothing is uploaded without approval: `dakie publish plan` writes a plan with an ID, and
`dakie publish run --approve <ID>` uploads exactly that plan. Every upload is logged so a clip is never
posted twice. Account logins live in ~/DakieClips/accounts/ (readable only by you, never in the repo).
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import json
import os
import secrets
import socket
import socketserver
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

from .common import CONFIG_PATH, HOME, load_config, read_json, write_json

ACCOUNTS = HOME / "accounts"
PLATFORMS = ("youtube", "instagram", "facebook", "tiktok")
GRAPH_VERSION = "v21.0"
# Overridable for tests (DAKIE_API_BASES='{"graph": "http://127.0.0.1:9999", ...}')
BASES = {
    "google_oauth": "https://oauth2.googleapis.com",
    "google_auth": "https://accounts.google.com/o/oauth2/v2/auth",
    "youtube": "https://www.googleapis.com",
    "graph": "https://graph.facebook.com",
    "tiktok_api": "https://open.tiktokapis.com",
    "tiktok_auth": "https://www.tiktok.com/v2/auth/authorize/",
}
BASES.update(json.loads(os.environ.get("DAKIE_API_BASES", "{}")))

DEFAULT_PUBLISH = {
    "youtube": {"enabled": False, "privacy": "public", "category_id": "20"},   # 20 = Gaming
    "instagram": {"enabled": False, "share_to_feed": True},
    "facebook": {"enabled": False},
    "tiktok": {"enabled": False, "mode": "inbox"},   # inbox = lands in your TikTok drafts to post from the app
    "offer_after_package": True,                     # Claude proposes an upload plan right after packaging
}


# ------------------------------------------------------------------ small helpers
def publish_config() -> dict:
    cfg = load_config().get("publish") or {}
    out = json.loads(json.dumps(DEFAULT_PUBLISH))
    for k, v in cfg.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        else:
            out[k] = v
    return out


def _set_enabled(platform: str, value: bool = True):
    cfg = json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}
    pub = cfg.setdefault("publish", {})
    pub.setdefault(platform, {})["enabled"] = value
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


def _account(name: str) -> dict:
    f = ACCOUNTS / f"{name}.json"
    if not f.exists():
        raise SystemExit(f"{name} is not connected. Run: dakie publish setup {name} (see references/publishing.md)")
    return json.loads(f.read_text())


def _save_account(name: str, data: dict):
    ACCOUNTS.mkdir(parents=True, exist_ok=True)
    os.chmod(ACCOUNTS, 0o700)
    f = ACCOUNTS / f"{name}.json"
    f.write_text(json.dumps(data, indent=2))
    os.chmod(f, 0o600)


def _http(method: str, url: str, *, params=None, form=None, body=None, headers=None, timeout=600):
    """Returns (status, parsed_json_or_text, response_headers). Never raises on HTTP errors."""
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    data = None
    hdrs = dict(headers or {})
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
    elif isinstance(body, (dict, list)):
        data = json.dumps(body).encode()
        hdrs.setdefault("Content-Type", "application/json; charset=UTF-8")
    elif body is not None:
        data = body
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw, status, rh = r.read(), r.status, dict(r.headers)
    except urllib.error.HTTPError as e:
        raw, status, rh = e.read(), e.code, dict(e.headers or {})
    text = raw.decode("utf-8", "replace")
    try:
        return status, json.loads(text), rh
    except ValueError:
        return status, text, rh


def _check(status, resp, what):
    if status >= 400 or (isinstance(resp, dict) and resp.get("error") and resp["error"] not in ({}, None)
                         and not (isinstance(resp["error"], dict) and resp["error"].get("code") in ("ok", 0))):
        err = resp.get("error") if isinstance(resp, dict) else resp
        msg = err.get("message") if isinstance(err, dict) else str(err)
        if isinstance(resp, dict) and resp.get("error_description"):     # OAuth-style errors (TikTok, Google)
            msg = f"{msg}: {resp['error_description']}"
        if isinstance(resp, dict) and isinstance(resp.get("debug_info"), dict):  # Meta upload servers
            d = resp["debug_info"]
            msg = f"{d.get('type')}: {d.get('message')}"
        if "spam_risk_too_many_pending_share" in str(msg):
            msg = ("TikTok allows only about 5 unposted drafts from an app. Post or delete the Dakie Clips "
                   "drafts in your TikTok inbox, then run the same plan again")
        raise RuntimeError(f"{what} failed (HTTP {status}): {str(msg)[:400]}")
    return resp


def _pkce(hex_challenge=False):
    verifier = secrets.token_urlsafe(64)[:96]
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = digest.hex() if hex_challenge else base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge


def _browser_login(auth_url: str, port: int, path: str = "/") -> dict:
    """Open the provider's sign-in page; catch the redirect on 127.0.0.1:<port>. Falls back to pasting the URL."""
    result: dict = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if "code" in q or "error" in q:
                result.update({k: v[0] for k, v in q.items()})
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write("<h2>Dakie Clips: sign-in received.</h2><p>Go back to the Terminal window: it says whether the account was saved. You can close this tab.</p>".encode())
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *a):
            pass

    H.timeout = 5        # an idle browser pre-connection can't block the listener

    class V4(socketserver.ThreadingTCPServer):
        daemon_threads = True
        allow_reuse_address = True

    class V6(V4):
        address_family = socket.AF_INET6

    servers = [V4(("127.0.0.1", port), H)]
    try:                     # 'localhost' often resolves to ::1 first, so listen there too
        servers.append(V6(("::1", port), H))
    except OSError:
        pass
    for srv in servers:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"\nOpening the sign-in page in your browser. If it doesn't open, visit:\n{auth_url}\n", file=sys.stderr)
    webbrowser.open(auth_url)
    deadline = time.time() + 300
    while not result and time.time() < deadline:
        time.sleep(0.3)
    for srv in servers:
        srv.shutdown()
        srv.server_close()
    if not result:
        raise SystemExit("Timed out waiting for the sign-in redirect (5 minutes). Run the setup command again.")
    if "error" in result:
        raise SystemExit(f"Sign-in was cancelled or refused: {result.get('error_description') or result['error']}")
    return result


# ------------------------------------------------------------------ YouTube
YT_SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"


def setup_youtube(client_secret_file: str, port: int = 8765):
    cs = json.loads(Path(client_secret_file).expanduser().read_text())
    app = cs.get("installed") or cs.get("web")
    if not app:
        raise SystemExit("That file isn't a Google OAuth client. Google Cloud > Google Auth Platform > Clients > "
                         "Create client > Application type: Desktop app > Download JSON.")
    if "web" in cs:   # web clients only work if this exact address is registered on the client
        print(f"Note: this is a 'Web application' client. In Google Cloud > Clients > this client, the "
              f"Authorized redirect URIs must include exactly:  http://127.0.0.1:{port}\n"
              "(If Google shows 'redirect_uri_mismatch', add it there, Save, wait a minute, and run setup again.)",
              file=sys.stderr)
    verifier, challenge = _pkce()
    state = secrets.token_urlsafe(16)
    redirect = f"http://127.0.0.1:{port}"
    url = BASES["google_auth"] + "?" + urllib.parse.urlencode({
        "client_id": app["client_id"], "redirect_uri": redirect, "response_type": "code", "scope": YT_SCOPES,
        "access_type": "offline", "prompt": "consent", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256"})
    got = _browser_login(url, port)
    if got.get("state") != state:
        raise SystemExit("Sign-in response didn't match this request (state mismatch). Run setup again.")
    st, tok, _ = _http("POST", BASES["google_oauth"] + "/token", form={
        "code": got["code"], "client_id": app["client_id"], "client_secret": app.get("client_secret", ""),
        "redirect_uri": redirect, "grant_type": "authorization_code", "code_verifier": verifier})
    _check(st, tok, "Google token exchange")
    if not tok.get("refresh_token"):
        raise SystemExit("Google didn't return a refresh token. Remove the app's access at "
                         "myaccount.google.com/permissions and run setup again.")
    st, ch, _ = _http("GET", BASES["youtube"] + "/youtube/v3/channels", params={"part": "snippet", "mine": "true"},
                      headers={"Authorization": f"Bearer {tok['access_token']}"})
    _check(st, ch, "Reading your YouTube channel")
    items = ch.get("items") or []
    if not items:
        raise SystemExit("This Google account has no YouTube channel.")
    _save_account("youtube", {"client_id": app["client_id"], "client_secret": app.get("client_secret", ""),
                              "refresh_token": tok["refresh_token"], "channel_id": items[0]["id"],
                              "channel_title": items[0]["snippet"]["title"]})
    _set_enabled("youtube")
    print(f"YouTube connected: {items[0]['snippet']['title']}")


def _youtube_access(acc: dict) -> str:
    st, tok, _ = _http("POST", BASES["google_oauth"] + "/token", form={
        "client_id": acc["client_id"], "client_secret": acc["client_secret"],
        "refresh_token": acc["refresh_token"], "grant_type": "refresh_token"})
    _check(st, tok, "Refreshing the YouTube login (run: dakie publish setup youtube)")
    return tok["access_token"]


def upload_youtube(item: dict) -> dict:
    acc = _account("youtube")
    token = _youtube_access(acc)
    video = Path(item["file"]).read_bytes()
    meta = {"snippet": {"title": item["title"][:100], "description": item["description"][:5000],
                        "tags": item.get("tags", [])[:30], "categoryId": str(item.get("category_id", "20"))},
            "status": {"privacyStatus": item["privacy"], "selfDeclaredMadeForKids": False}}
    st, resp, hdrs = _http("POST", BASES["youtube"] + "/upload/youtube/v3/videos",
                           params={"uploadType": "resumable", "part": "snippet,status"}, body=meta,
                           headers={"Authorization": f"Bearer {token}", "X-Upload-Content-Type": "video/mp4",
                                    "X-Upload-Content-Length": str(len(video))})
    _check(st, resp, "Starting the YouTube upload")
    location = hdrs.get("Location") or hdrs.get("location")
    if not location:
        raise RuntimeError("YouTube didn't return an upload address.")
    st, vid, _ = _http("PUT", location, body=video, headers={"Content-Type": "video/mp4"})
    _check(st, vid, "Uploading the video to YouTube")
    return {"id": vid["id"], "url": f"https://www.youtube.com/shorts/{vid['id']}",
            "status": vid.get("status", {}).get("uploadStatus", "uploaded")}


# ------------------------------------------------------------------ Meta (Facebook Page + Instagram)
def _graph(path: str) -> str:
    return f"{BASES['graph']}/{GRAPH_VERSION}/{path.lstrip('/')}"


def setup_meta(app_id: str, app_secret: str, user_token: str, page_id: str | None = None):
    st, ll, _ = _http("GET", _graph("oauth/access_token"), params={
        "grant_type": "fb_exchange_token", "client_id": app_id, "client_secret": app_secret,
        "fb_exchange_token": user_token})
    _check(st, ll, "Exchanging the Meta token for a long-lived one")
    long_user = ll["access_token"]
    st, pages, _ = _http("GET", _graph("me/accounts"), params={
        "fields": "id,name,access_token,instagram_business_account{id,username}", "access_token": long_user})
    _check(st, pages, "Listing your Facebook Pages")
    data = pages.get("data") or []
    if not data:
        raise SystemExit("No Facebook Page found. Instagram and Facebook posting need a Facebook Page "
                         "(with your Instagram Business/Creator account linked to it). See references/publishing.md.")
    if page_id:
        data = [p for p in data if p["id"] == page_id]
    if len(data) > 1:
        names = "\n".join(f"  {p['id']}  {p['name']}" for p in data)
        raise SystemExit(f"You manage several Pages. Run again with --page-id one of:\n{names}")
    page = data[0]
    ig = page.get("instagram_business_account") or {}
    _save_account("meta", {"app_id": app_id, "app_secret": app_secret, "user_token": long_user,
                           "user_token_expires_at": int(time.time()) + int(ll.get("expires_in", 60 * 86400)),
                           "page_id": page["id"], "page_name": page["name"], "page_token": page["access_token"],
                           "ig_user_id": ig.get("id"), "ig_username": ig.get("username")})
    _set_enabled("facebook")
    print(f"Facebook connected: Page '{page['name']}'")
    if ig.get("id"):
        _set_enabled("instagram")
        print(f"Instagram connected: @{ig.get('username')}")
    else:
        print("No Instagram Business/Creator account is linked to this Page, so Instagram stays off.")


def _rupload(upload_url: str, token: str, video: bytes, what: str):
    st, resp, _ = _http("POST", upload_url, body=video, headers={
        "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(len(video)),
        "Content-Type": "application/octet-stream"})
    _check(st, resp, what)
    return resp


def upload_instagram(item: dict) -> dict:
    acc = _account("meta")
    if not acc.get("ig_user_id"):
        raise RuntimeError("No Instagram account linked (run: dakie publish setup meta).")
    if acc.get("user_token_expires_at", 0) < time.time():
        raise RuntimeError("The Meta login expired (they last 60 days). Run: dakie publish setup meta")
    token, ig = acc["user_token"], acc["ig_user_id"]
    video = Path(item["file"]).read_bytes()
    # Instagram's upload server sometimes answers ProcessingFailedError for a good file; a fresh
    # container usually works, so try a few times before giving up.
    for attempt in range(1, 4):
        st, c, _ = _http("POST", _graph(f"{ig}/media"), params={
            "media_type": "REELS", "upload_type": "resumable", "caption": item["caption"][:2200],
            "share_to_feed": str(item.get("share_to_feed", True)).lower(), "access_token": token})
        _check(st, c, "Creating the Instagram Reel")
        try:
            _rupload(c["uri"], token, video, "Uploading the video to Instagram")
            break
        except RuntimeError as e:
            if attempt == 3 or "ProcessingFailedError" not in str(e):
                raise RuntimeError(f"{e} (tried {attempt}x; Instagram's servers rejected the upload. "
                                   "Try again later, or post this clip from the Instagram app)") from None
            print(f"   Instagram rejected the upload (attempt {attempt}/3), retrying in 30 s...", file=sys.stderr)
            time.sleep(30)
    for _ in range(60):                      # processing usually takes 20-90 s
        st, s, _ = _http("GET", _graph(c["id"]), params={"fields": "status_code,status", "access_token": token})
        code = s.get("status_code") if isinstance(s, dict) else None
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram couldn't process the video: {s.get('status')}")
        time.sleep(5)
    else:
        raise RuntimeError("Instagram is still processing after 5 minutes; check the app later.")
    st, p, _ = _http("POST", _graph(f"{ig}/media_publish"), params={"creation_id": c["id"], "access_token": token})
    _check(st, p, "Publishing the Instagram Reel")
    st, m, _ = _http("GET", _graph(p["id"]), params={"fields": "permalink", "access_token": token})
    return {"id": p["id"], "url": (m.get("permalink") if isinstance(m, dict) else None) or ""}


def upload_facebook(item: dict) -> dict:
    acc = _account("meta")
    token, page = acc["page_token"], acc["page_id"]
    video = Path(item["file"]).read_bytes()
    st, s, _ = _http("POST", _graph(f"{page}/video_reels"), params={"upload_phase": "start", "access_token": token})
    _check(st, s, "Starting the Facebook Reel")
    _rupload(s["upload_url"], token, video, "Uploading the video to Facebook")
    st, f, _ = _http("POST", _graph(f"{page}/video_reels"), params={
        "upload_phase": "finish", "video_id": s["video_id"], "video_state": "PUBLISHED",
        "description": item["caption"][:5000], "access_token": token})
    _check(st, f, "Publishing the Facebook Reel")
    return {"id": s["video_id"], "url": f"https://www.facebook.com/reel/{s['video_id']}"}


# ------------------------------------------------------------------ TikTok
def check_tiktok_client(client_key: str, client_secret: str) -> tuple[bool, str]:
    """Ask TikTok whether this key + secret pair is valid (client-credentials grant; no user involved)."""
    st, r, _ = _http("POST", BASES["tiktok_api"] + "/v2/oauth/token/", form={
        "client_key": client_key, "client_secret": client_secret, "grant_type": "client_credentials"})
    if isinstance(r, dict) and r.get("access_token"):
        return True, "ok"
    desc = (r.get("error_description") or r.get("error") or "") if isinstance(r, dict) else str(r)[:200]
    return False, desc


def setup_tiktok(client_key: str, client_secret: str, port: int = 8765):
    verifier, challenge = _pkce(hex_challenge=True)   # TikTok's desktop PKCE uses a hex SHA-256 challenge
    state = secrets.token_urlsafe(16)
    redirect = f"http://localhost:{port}/callback/"
    url = BASES["tiktok_auth"] + "?" + urllib.parse.urlencode({
        "client_key": client_key, "scope": "user.info.basic,video.upload", "response_type": "code",
        "redirect_uri": redirect, "state": state, "code_challenge": challenge, "code_challenge_method": "S256"})
    got = _browser_login(url, port)
    if got.get("state") != state:
        raise SystemExit("Sign-in response didn't match this request (state mismatch). Run setup again.")
    st, tok, _ = _http("POST", BASES["tiktok_api"] + "/v2/oauth/token/", form={
        "client_key": client_key, "client_secret": client_secret, "code": got["code"],
        "grant_type": "authorization_code", "redirect_uri": redirect, "code_verifier": verifier})
    _check(st, tok, "TikTok token exchange")
    acc = {"client_key": client_key, "client_secret": client_secret, "open_id": tok.get("open_id"),
           "access_token": tok["access_token"], "refresh_token": tok["refresh_token"],
           "access_expires_at": int(time.time()) + int(tok.get("expires_in", 86400)) - 60}
    st, me, _ = _http("GET", BASES["tiktok_api"] + "/v2/user/info/", params={"fields": "display_name"},
                      headers={"Authorization": f"Bearer {acc['access_token']}"})
    acc["display_name"] = (me.get("data", {}).get("user", {}).get("display_name") if isinstance(me, dict) else None)
    _save_account("tiktok", acc)
    _set_enabled("tiktok")
    print(f"TikTok connected: {acc['display_name'] or acc['open_id']}")


def _tiktok_access(acc: dict) -> str:
    if acc.get("access_expires_at", 0) > time.time():
        return acc["access_token"]
    st, tok, _ = _http("POST", BASES["tiktok_api"] + "/v2/oauth/token/", form={
        "client_key": acc["client_key"], "client_secret": acc["client_secret"],
        "grant_type": "refresh_token", "refresh_token": acc["refresh_token"]})
    _check(st, tok, "Refreshing the TikTok login (run: dakie publish setup tiktok)")
    acc.update(access_token=tok["access_token"], refresh_token=tok.get("refresh_token", acc["refresh_token"]),
               access_expires_at=int(time.time()) + int(tok.get("expires_in", 86400)) - 60)
    _save_account("tiktok", acc)
    return acc["access_token"]


def upload_tiktok(item: dict) -> dict:
    acc = _account("tiktok")
    token = _tiktok_access(acc)
    video = Path(item["file"]).read_bytes()
    size = len(video)
    chunk = size if size <= 64_000_000 else 10_000_000
    total = 1 if chunk == size else size // chunk
    st, init, _ = _http("POST", BASES["tiktok_api"] + "/v2/post/publish/inbox/video/init/",
                        headers={"Authorization": f"Bearer {token}"},
                        body={"source_info": {"source": "FILE_UPLOAD", "video_size": size,
                                              "chunk_size": chunk, "total_chunk_count": total}})
    _check(st, init, "Starting the TikTok upload")
    data = init["data"]
    for i in range(total):
        a = i * chunk
        b = size if i == total - 1 else a + chunk      # the last chunk takes the remainder
        st, r, _ = _http("PUT", data["upload_url"], body=video[a:b], headers={
            "Content-Type": "video/mp4", "Content-Length": str(b - a), "Content-Range": f"bytes {a}-{b - 1}/{size}"})
        if st >= 400:
            raise RuntimeError(f"TikTok upload of part {i + 1}/{total} failed (HTTP {st}).")
    return {"id": data["publish_id"], "url": "",
            "note": "In your TikTok inbox now: tap the notification, paste the caption below, choose Everyone, Post.",
            "caption_to_paste": item["caption"]}


UPLOADERS = {"youtube": upload_youtube, "instagram": upload_instagram,
             "facebook": upload_facebook, "tiktok": upload_tiktok}


# ------------------------------------------------------------------ plan / approve / run
def status() -> str:
    pc = publish_config()
    rows = []
    for plat in PLATFORMS:
        f = ACCOUNTS / f"{'meta' if plat in ('instagram', 'facebook') else plat}.json"
        acc = json.loads(f.read_text()) if f.exists() else None
        who = None
        if acc:
            who = {"youtube": acc.get("channel_title"), "instagram": acc.get("ig_username") and "@" + acc["ig_username"],
                   "facebook": acc.get("page_name"), "tiktok": acc.get("display_name")}[plat]
            if plat in ("instagram", "facebook") and acc.get("user_token_expires_at", 0) < time.time() + 7 * 86400:
                who = f"{who} (login expires soon: run dakie publish setup meta)"
        on = pc.get(plat, {}).get("enabled")
        rows.append(f"{plat:10} {'ON ' if on and who else 'off'}  {who or 'not connected'}"
                    + (f"  [default: {pc['youtube']['privacy']}]" if plat == "youtube" else "")
                    + ("  [lands in your TikTok drafts]" if plat == "tiktok" else ""))
    return "\n".join(rows)


def _connected(plat: str) -> bool:
    name = "meta" if plat in ("instagram", "facebook") else plat
    f = ACCOUNTS / f"{name}.json"
    if not f.exists():
        return False
    if plat == "instagram":
        return bool(json.loads(f.read_text()).get("ig_user_id"))
    return True


def _texts(meta: dict, plat: str) -> dict:
    m = meta.get(plat, {})
    tags = " ".join(m.get("hashtags", []))
    if plat == "youtube":
        desc = m.get("description", "")
        return {"title": m.get("title", ""), "description": desc, "tags": m.get("tags", [])}
    cap = m.get("caption", "")
    return {"caption": cap + (("\n\n" + tags) if tags and tags not in cap else "")}


def _fingerprint(path: Path) -> str:
    st = path.stat()
    return f"{st.st_size}-{int(st.st_mtime)}"


def make_plan(proj: Path, clips=None, platforms=None, include_red=False) -> dict:
    pc = publish_config()
    final = proj / "final"
    log = read_json(final / "publish_log.json") if (final / "publish_log.json").exists() else []
    done = {(e["clip"], e["platform"]) for e in log if e.get("ok")}
    plats = [p for p in (platforms or PLATFORMS) if pc.get(p, {}).get("enabled") and _connected(p)]
    items, skipped = [], []
    for d in sorted(final.glob("clip_*")):
        n = int(d.name.split("_")[1])
        if clips and n not in clips:
            continue
        vids = sorted(d.glob("*.mp4"))
        if not vids or not (d / "metadata.json").exists():
            skipped.append(f"clip {n}: not packaged")
            continue
        meta = read_json(d / "metadata.json")
        check = (d / "copyright_check.md").read_text() if (d / "copyright_check.md").exists() else ""
        flags = [ln.strip("- ").strip()[:160] for ln in check.splitlines() if "🔴" in ln or "🟡" in ln]
        red = any("🔴" in f for f in flags)
        for plat in plats:
            if (n, plat) in done:
                skipped.append(f"clip {n} → {plat}: already published")
                continue
            if red and not include_red:
                skipped.append(f"clip {n} → {plat}: has a 🔴 copyright item (use --include-red to override)")
                continue
            item = {"clip": n, "platform": plat, "file": str(vids[0]), "fingerprint": _fingerprint(vids[0]),
                    "flags": flags, **_texts(meta, plat)}
            if plat == "youtube":
                item.update(privacy=pc["youtube"]["privacy"], category_id=pc["youtube"]["category_id"])
            if plat == "instagram":
                item["share_to_feed"] = pc["instagram"].get("share_to_feed", True)
            items.append(item)
    body = json.dumps([{k: v for k, v in i.items() if k != "flags"} for i in items], sort_keys=True)
    plan = {"plan_id": hashlib.sha256(body.encode()).hexdigest()[:8], "created": int(time.time()),
            "items": items, "skipped": skipped, "not_connected": [p for p in (platforms or PLATFORMS)
                                                                  if pc.get(p, {}).get("enabled") and not _connected(p)]}
    write_json(final / "publish_plan.json", plan)
    (final / "publish_plan.md").write_text(plan_markdown(plan))
    return plan


def plan_markdown(plan: dict) -> str:
    out = [f"# Upload plan {plan['plan_id']}", ""]
    if not plan["items"]:
        out.append("Nothing to upload.")
    for i in plan["items"]:
        head = i.get("title") or i.get("caption", "").splitlines()[0][:80]
        extra = f" · {i['privacy']}" if i["platform"] == "youtube" else (" · to your drafts" if i["platform"] == "tiktok" else "")
        out.append(f"- **Clip {i['clip']} → {i['platform']}**{extra}: {head}")
        for f in i["flags"]:
            out.append(f"    - {f}")
    if plan["skipped"]:
        out += ["", "Skipped:", *[f"- {s}" for s in plan["skipped"]]]
    if plan["not_connected"]:
        out += ["", "Enabled but not connected: " + ", ".join(plan["not_connected"])]
    out += ["", f"Approve with: dakie publish run <project> --approve {plan['plan_id']}"]
    return "\n".join(out)


def run_plan(proj: Path, approve: str, force=False, only_platforms=None, only_clips=None) -> list[dict]:
    """Run an approved plan. only_platforms / only_clips narrow it to a subset (e.g. a retry);
    they can never add anything that isn't already in the approved plan."""
    final = proj / "final"
    if not (final / "publish_plan.json").exists():
        raise SystemExit("No upload plan yet. Run: dakie publish plan <project>")
    plan = read_json(final / "publish_plan.json")
    if approve != plan["plan_id"]:
        raise SystemExit(f"--approve {approve} doesn't match the current plan ({plan['plan_id']}). "
                         "Review the latest plan and approve that ID.")
    if time.time() - plan["created"] > 24 * 3600:
        raise SystemExit("This plan is more than 24 hours old. Make a new one: dakie publish plan <project>")
    log_f = final / "publish_log.json"
    log = read_json(log_f) if log_f.exists() else []
    done = {(e["clip"], e["platform"]) for e in log if e.get("ok")}
    results = []
    for item in plan["items"]:
        if (only_platforms and item["platform"] not in only_platforms) or \
                (only_clips and str(item["clip"]) not in only_clips):
            continue
        key = (item["clip"], item["platform"])
        if key in done and not force:
            print(f"clip {item['clip']} → {item['platform']}: already published, skipped")
            continue
        if _fingerprint(Path(item["file"])) != item["fingerprint"]:
            print(f"clip {item['clip']} → {item['platform']}: the video changed after approval, skipped")
            continue
        print(f"clip {item['clip']} → {item['platform']}: uploading...", file=sys.stderr)
        entry = {"clip": item["clip"], "platform": item["platform"], "time": int(time.time()), "plan": plan["plan_id"]}
        try:
            entry.update(ok=True, **UPLOADERS[item["platform"]](item))
        except Exception as e:  # keep going with the other uploads
            entry.update(ok=False, error=str(e)[:500])
        log.append(entry)
        write_json(log_f, log)          # written after every upload, so a crash never causes a re-post
        results.append(entry)
        print(f"clip {item['clip']} → {item['platform']}: "
              + (f"✅ {entry.get('url') or entry.get('note', 'done')}" if entry["ok"] else f"❌ {entry['error']}"))
        if entry.get("caption_to_paste"):
            print("   caption to paste in TikTok:\n   " + entry["caption_to_paste"].replace("\n", "\n   "))
    return results
