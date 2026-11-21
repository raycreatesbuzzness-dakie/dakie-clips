---
title: Privacy policy · Dakie Clips
permalink: /privacy/
---

# Privacy policy

_Last updated: 21 November 2026_

Dakie Clips is a free, open-source tool that runs on your own computer. There is no Dakie Clips
server, account system, analytics or advertising. This policy explains what the tool does with your
data when you connect your social media accounts.

## What the tool accesses

Only when **you** run a setup command and approve access in the platform's own sign-in page, the tool
receives a login (an access token) for that account, limited to these permissions:

| Platform | Permissions | Used for |
|---|---|---|
| YouTube (Google) | `youtube.upload`, `youtube.readonly` | Uploading clips you approve; showing your channel name so you can confirm the right account is connected |
| Facebook / Instagram (Meta) | Page and Instagram content-publishing permissions | Posting clips you approve to your own Facebook Page and Instagram professional account |
| TikTok | `user.info.basic`, `video.upload` | Sending clips you approve to your own TikTok drafts; showing your display name |

The tool does **not** read, collect or analyse your other videos, comments, messages, viewers,
analytics or any other account data.

## How your data is used, stored and shared

- Logins are stored **only on your computer**, in `~/DakieClips/accounts/`, readable only by your
  user account. They are never sent to the developer of Dakie Clips or to anyone else.
- Videos and their titles, descriptions and hashtags are sent **only** to the platform you chose,
  **only** after you approve that specific upload plan.
- A local log of what was uploaded (video IDs and links) is kept on your computer so nothing is posted twice.
- No data is sold, shared, transferred to third parties, or used for advertising, profiling or AI training.

Dakie Clips' use and transfer of information received from Google APIs adheres to the
[Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy),
including the Limited Use requirements. Use of YouTube features is subject to the
[YouTube Terms of Service](https://www.youtube.com/t/terms) and the
[Google Privacy Policy](https://policies.google.com/privacy).

## Removing access and deleting data

- Delete the files in `~/DakieClips/accounts/` to remove all stored logins from your computer.
- Revoke access at any time: [Google account permissions](https://myaccount.google.com/permissions),
  Facebook **Settings → Business integrations**, TikTok **Settings → Security → Manage app permissions**.

## Contact

Questions about this policy: [open an issue on GitHub](https://github.com/raycreatesbuzzness-dakie/dakie-clips/issues).
