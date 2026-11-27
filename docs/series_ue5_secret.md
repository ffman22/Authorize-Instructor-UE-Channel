# Series "AAA UE5 Secrets" — State Machines, episodes 1-3 (draft, owner approval pending)

Based on Gemini's `08_AAA_UE5_SECRET_STATE_MACHINES_SERIES_DRAFT` (Drive). Format: `docs/script_format.md` (result first). Rules: `docs/research_rules.md`. Manifests and specs: `videos/ue5-secret-0*/`.

## Changed from Gemini's draft
- Shortened: episode 2 ran well over 35 s when spoken. Each script is now 65-80 words, about 27-33 s.
- State Alias: the checked states are the ones the alias stands for, so a transition leaving the alias applies from any of them. The draft said "states you want to enter through it".
- "Linked video below" removed: no long State Machines video exists yet. Add it back when one is published.
- "Beginners and indie devs" removed from the hooks (it talks down to the viewer).
- Comment CTA `UNREAL` added to every episode and platform.

## Common structure
| Time | Content |
|---|---|
| 0:00-0:03 | **Result first:** the finished graph with the character moving; "AAA UE5 secret..." names that result; banner `AAA UE5 SECRET` |
| 0:03-0:06 | Short credibility intro over the same picture (`docs/script_intro.md`) |
| 0:06-0:09 | The problem: the "before", 2-3 s |
| 0:09-0:27 | The fix, zoomed on one node (2 s at most), back to the character every few seconds |
| 0:27-end | Result again and CTA, then the end splash (cut plus splash at most 60 s) |

The lines are a guide: say them like you would to a teammate, keeping the facts and the order.

## Episode 1: State Aliases (`ue5-secret-01-state-aliases`)
> AAA UE5 secret: all of this? Just one transition.
> I lead animation at Ubisoft, and I'm an Unreal Authorized Instructor.
> State machine looking like a spider web? Right-click, add a State Alias, and in its details, check every state that should use this exit. Drag one transition to your target, set the rule once, and you're done.
> Way cleaner, right? Comment UNREAL. Next up: conduits.

- Titles: "AAA UE5 Secret: Stop State Machine Spider Webs" / "AAA UE5 Secret: One Transition, Many States" / "AAA UE5 Secret: Clean Up Your State Machine"
- Overlays: `SPIDER WEB?` / `ONE TRANSITION` / `STATE ALIAS`

## Episode 2: Conduits (`ue5-secret-02-conduits`)
> AAA UE5 secret: all these branches share one rule.
> I lead animation at Ubisoft, and I'm an Unreal Authorized Instructor.
> Still copying the same condition everywhere? Right-click, add a Conduit, and open it. Here's the catch: set its rule to true, or to the condition every branch shares. Then plug your state into it, and give each way out its own rule.
> Write it once. Comment UNREAL. Next up: cached poses.

- Titles: "AAA UE5 Secret: Why Your Conduit Never Fires" / "AAA UE5 Secret: Conduits Without the Confusion" / "AAA UE5 Secret: Stop Repeating Transition Rules"
- Overlays: `NEVER FIRES?` / `FIX YOUR CONDUIT` / `ONE SHARED RULE`

## Episode 3: Cached Pose (`ue5-secret-03-cached-pose`)
> AAA UE5 secret: this jump reuses all my ground locomotion.
> I lead animation at Ubisoft, and I'm an Unreal Authorized Instructor.
> No need to wire it twice. Save your ground locomotion as a cached pose. Then, inside your air state machine, use that pose as your grounded state. The ground logic stays in one place.
> Aliases, conduits, cached poses. Nice and clean. Comment UNREAL!

- Titles: "AAA UE5 Secret: Clean Ground-to-Air with Cached Poses" / "AAA UE5 Secret: Reuse Locomotion in the Air" / "AAA UE5 Secret: Stop Duplicating Ground Logic"
- Overlays: `GROUND TO AIR` / `CACHE IT` / `NO MORE DUPLICATES`

## What the owner records (before any edit)
General: Unreal editor capture 1920x1080 or higher (2560x1440 gives room to crop to 9:16), 60 fps, large graph zoom, cursor visible, no notifications, no employer project or assets. Voice on a separate track if possible. Name files `data/clips/<id>-raw.mp4` and copy them to Drive `1-source-videos`.

| Episode | Shots |
|---|---|
| All, first | The finished result: clean graph plus the character moving, 5 s or more (this opens the Short) |
| 1 | Messy state machine (2-3 s); add the alias; details panel with checked states; one transition and its rule; clean graph; character in viewport doing the transitions |
| 2 | Conduit that never fires; open it and set the rule; into-conduit and exit rules; character in viewport |
| 3 | Duplicated ground transitions; New Save Cached Pose; Use Cached Pose inside the air machine; jump and land in viewport |
| All | State the exact engine version on camera or in a note for `spec.json` |

Extra takes, once: the short and the long credibility intro, and the spoken "AAA UE5 secret".

## Approval gates
0. Confirm each `spec.json` against the recording (engine version, timestamps) and set `owner_checked`.
1. Pick title and overlay.
2. Pick the thumbnail frame from the contact sheet.
3. Approve the cut in stages: hook, lesson, ending.
4. Approval sheet (`tools/approval.py sheet`), then upload private or scheduled.

## Per platform
- YouTube: title without hashtags, 3 hashtags at the end of the description, workshop link in the first 2 lines, comment `UNREAL`.
- Instagram and TikTok: max 5 hashtags, comment `UNREAL`, watch and subscribe on YouTube; add ffman22 as collaborator on Instagram.
- Threads and Community: short text with the comment CTA.
- Nothing sends the `UNREAL` information automatically: the owner replies by hand.
