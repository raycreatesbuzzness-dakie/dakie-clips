# TikTok app review (for public Direct Posts)

Until TikTok reviews a developer app, every Direct Post is private ("Only me"). The review is free.
TikTok's form and wording change, so map these answers to whatever fields it shows. Answer in your own
words where it asks about you; never claim anything that isn't true.

**Be aware:** TikTok sometimes rejects apps it considers "for personal use only". Dakie Clips is a
public, open-source tool (anyone can install it and connect their own account), which is the honest
answer to that question. Approval is still TikTok's decision.

## App details
- **App name:** Dakie Clips
- **Category:** Video / Content creation tools
- **Description:** Dakie Clips is an open-source desktop tool for gaming creators. It turns a livestream
  into short vertical clips with captions and titles, then, only after the creator reviews and approves
  an upload plan, posts the clips to the creator's own TikTok account with their captions and hashtags.
- **Website / homepage:** https://raycreatesbuzzness-dakie.github.io/dakie-clips/
- **Terms of Service URL:** https://raycreatesbuzzness-dakie.github.io/dakie-clips/terms/
- **Privacy Policy URL:** https://raycreatesbuzzness-dakie.github.io/dakie-clips/privacy/
- **Platform:** Desktop
- **Redirect URI:** http://localhost:8765/callback/

## Products and scopes, and why each is needed
| Product / scope | Why |
|---|---|
| Login Kit, `user.info.basic` | Shows the creator which TikTok account they connected (display name) |
| Content Posting API, `video.upload` | Optional mode that sends a clip to the creator's TikTok drafts |
| Content Posting API → Direct Post, `video.publish` | Posts a clip the creator approved to their own profile with its caption |

## How the app follows TikTok's Content Sharing Guidelines
- **Creator info before every post:** the app calls `creator_info/query` when it builds the upload plan
  and again right before each post, and shows the creator's TikTok nickname in the plan.
- **Privacy:** the creator chooses who can see posts (`dakie publish privacy tiktok public|friends|followers|private`);
  there is no silent default, and only the options TikTok returns for that account are allowed. The
  chosen setting is shown for every clip in the plan.
- **Interactions:** comments, Duet and Stitch settings are shown per clip; anything the creator turned off
  in TikTok stays off, and the creator can turn each one off in the app.
- **Explicit consent:** nothing is posted until the creator reads the plan (every clip, its full caption,
  privacy and interaction settings) and replies with that plan's ID. A changed plan needs a new approval.
- **Music Usage Confirmation:** shown in every plan with a link; approving the plan is the agreement.
- **Commercial content:** clips are not marked as branded or promotional content.
- **No modifications by TikTok-side automation:** the app uploads the finished video file; captions are
  written for each clip and shown in full before approval.
- **Max duration:** clips longer than the account's `max_video_post_duration_sec` are left out of the plan.
- **Status:** after posting, the app checks `status/fetch` and reports the post link or the failure reason.

## Demo video (TikTok asks for one)
Record a 1–2 minute screen recording (QuickTime → New Screen Recording) showing, in order:
1. Running `dakie publish setup tiktok`: the TikTok sign-in and consent page, then "TikTok connected".
2. `dakie publish privacy tiktok public` (choosing who can see posts).
3. `dakie publish plan <project> --platforms tiktok`: the plan with account name, privacy,
   comments/Duet/Stitch, the full caption and the Music Usage Confirmation.
4. Approving the plan ID and `dakie publish run …`, then the post appearing on the TikTok profile.
Use the Sandbox app for the recording; posts will be "Only me" there, which is expected. Before
approval TikTok only accepts Direct Post to a **private account**: switch the TikTok account to private
(Settings and privacy → Privacy → Private account) just for the recording, then switch it back.
