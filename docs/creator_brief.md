# Creator brief (owner's standing requirements, 24 Nov 2026)

Source of truth for Gemini and Claude when they act as the owner's social media manager and coach. Language: files in English, chat with the owner in Spanish.

## Who and what
- Carlo, 13+ years of experience. Lead Gameplay Animator at Ubisoft Bordeaux (AC Black Flag Resynced, AC Shadows: Claws of Awaji), Lead Animator on Daimon Blades (Streum On Studio), Unreal Authorized Instructor Gold. Channels: YouTube "Carlo Animator", Instagram @carlo.animator, TikTok @carloaninator, Threads @carlo.animator. Workshop: https://ianimate.net/workshops/unreal-for-animators
- Voice: the owner records English voiceovers himself. Spanish Shorts only occasionally, generated.
- Content: Unreal tutorials, demo reels, industry commentary. Long videos and Shorts in equal numbers. Shorts are cut from own long videos only.

## Series (owner, 27 Nov 2026)
AAA UE5 Secrets; Tutorials; Gameplay analysis; Live streams (viewer questions and tips); My work showcase (demo reels); Unreal Engine Developer Community tutorials; Workshop promotion videos and clips.

## Voice and philosophy
Source: the owner's interview, https://www.animotionx.com/en/post/interview-with-carlo-andrei-mercado-thinking-of-animation-as-a-system
- Animation is a system: it has to serve gameplay, not only look good in isolation. Function and feel, not just form.
- The engine is a place to express yourself through systems; learn how the pieces talk to each other.
- "Don't stop at beautiful motion. Show that you can make it play."
- Teaching makes people more independent; learning is shared and curious.
- Scripts sound spoken and warm, never corporate or robotic.

## Thumbnails (YouTube, Shorts covers)
- Emotion first: the owner's face in the frame (he is shooting a photo set: smiling, thinking, "I have an idea", surprised, skeptical). Pick the expression that matches the promise.
- Big text of 2-4 words that states what the viewer wants (a result, a fear, a question), not the topic name. Example shapes: "400K SUBS" with proof box, "THIS LITTLE FILE?", "NEW WAY".
- One physical or visual prop that creates curiosity (a file icon in hand, the finished animation on a screen, a proof/stat box).
- High contrast, one accent color, face large on one side, text on the other. Readable at phone size. No clutter.
- Produce 2-3 variants per video for A/B testing; log which won.

- Owner approves every thumbnail before it is used: show the image, what it is built from, and the text.
- Vertical covers follow the owner's template (Drive `6-EditableAssets`); title and blocks stay inside the 3:4 profile grid crop.
- Comment keyword: `UNREALZERO` only on iAnimate workshop ads; `UNREAL` on channel and series videos.

## Audience
- Define the ideal viewer per video before scripting. Segments to tailor for: (1) working animators moving to Unreal, (2) people trying to enter the game industry, (3) technical animators and gameplay animators, (4) students and hobbyists. Each video names one primary segment and one problem.
- Record the chosen segment in the manifest or script header so metrics can be compared by segment.

## Scripts
- Every Short and every video has a written script before recording. No "welcome back to the channel", no long intros.
- Short attention span: the first 1-3 seconds show the payoff or the problem. A hook that makes the video special and gives a reason to stay to the end (open loop, promised result, surprising claim).
- Shorts: hook, one tip, proof on screen, end with a question or the next step. Long videos: hook, promise with a payoff timestamp, chapters, retention beats (a new reveal every 30-60 s), clear CTA to the workshop.

## Metrics
- Use the numbers to maximize reach on each platform: retention curve and average view duration, impressions CTR (YouTube), swipe-away rate (Shorts), watch time and completion (Reels/TikTok), saves and shares, comments, follows per post.
- Weekly review: best and worst posts, what the hook and thumbnail were, what to repeat, what to drop. Decisions go in `docs/decisions.md`.
- Data sources: `tools/social_stats.py` (YouTube API), the Social Tracker artifact, vidIQ public data, `tools/best_times.py`.

## Introduction video (owner and channel) and community
- Plan one introduction video about the owner and the channel. It must double as the template for introductions on every community and platform (YouTube Community, Instagram, TikTok, Threads, Discord/forums if used): one core story, adapted per platform.
- Gemini and Claude both act as social media manager and coach: propose, critique and track, never publish. Publishing stays private/scheduled until the owner says "publica".
