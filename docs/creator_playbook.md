# Creator Playbook: Carlo Animator

## 1. Thumbnail System

### Checklist
- [ ] Face: High-emotion shot (well-lit, eyes sharp).
- [ ] Text: 2-4 words, large font, high contrast.
- [ ] Visual Proof: One prop or inset screen showing result/data.
- [ ] Branding: Consistent accent color (e.g., Unreal Engine orange).
- [ ] Mobile Test: Squint test (is text readable at 50px wide?).

### Photo Shot List (10 Expressions)
1. **The "Fixer" (Frustrated/Skeptical):** For "Stop doing this" / "Common errors."
2. **The "Lightbulb" (Excited):** For "New feature" / "Game-changing trick."
3. **The "Pro" (Confident/Smiling):** For general tutorials/authority building.
4. **The "Shock" (Mouth open, brow raised):** For "I can't believe this worked" / "Viral reveal."
5. **The "Thinker" (Chin on hand):** For complex workflow explanations.
6. **The "Pointer" (Pointing at screen/text):** For directional CTA.
7. **The "Concentrated" (Serious):** For deep dives/technical masterclasses.
8. **The "Challenge" (Folded arms):** For industry commentary/bold claims.
9. **The "Relieved" (Exhale):** For time-saving hacks.
10. **The "Questioning" (Brow furrowed):** For "Why is X not working?"

### Text Formulas & Examples
*   **The "Secret" Formula:** [Result] + [Prop/Label]
    *   *Example:* "ANIMATION LAG? FIXED."
    *   *Example:* "UNREAL BROKE MY CURVES?"
    *   *Example:* "ONE CURVE FIXES IT."
*   **The "Gap" Formula:** [Fear] + [Solution]
    *   *Example:* "STOP KEYFRAMING MANUALLY."
    *   *Example:* "ANIMATE 5X FASTER."
    *   *Example:* "UNREAL FOR PROS."
*   **The "Curiosity" Formula:** [Metric/Result] + [Question]
    *   *Example:* "THIS LITTLE FILE?"
    *   *Example:* "BEST COMBO SYSTEM?"
    *   *Example:* "KILL YOUR RIG?"
    *   *Example:* "HIDDEN UE5 SETTINGS."

### A/B Template
*   **ID:** `vid_001_title`
*   **Var A:** Face (Expression) + Text (Formula 1)
*   **Var B:** Face (Expression) + Text (Formula 2)
*   **Winner:** [Date] + [CTR%]

---

## 2. Ideal Viewer Profiles
1. **Working Animators:** Pain: Too slow, struggling with engine quirks. Search: "UE5 animation optimization". Tone: Professional/Peer. *Title: "Animation Curves: The Fix."*
2. **Industry Aspirants:** Pain: Can't get a job, bad reels. Search: "Gameplay animation reel critique". Tone: Mentorship. *Title: "How to get hired."*
3. **Technical Animators:** Pain: Scripting/Blueprints are complex. Search: "Lyra combo system". Tone: Technical. *Title: "Lyra Combat Deep Dive."*
4. **Students/Hobbyists:** Pain: Overwhelmed by Unreal. Search: "Unreal Engine animation for beginners". Tone: Encouraging. *Title: "Unreal for Beginners."*
*   **Tagging:** Add `{SegmentName}` to the manifest file for every video.

---

## 3. Script Templates

### Short (30-50s)
*   **0-3s (Hook):** The payoff or the "before" vs "after" jump cut.
*   **3-40s (Tip/Proof):** One concrete step. Show the proof.
*   **40-50s (CTA):** "Which topic next?" OR "Full tutorial link in bio."

### Long Video
*   **0-15s (Hook):** State the transformation.
*   **15s (Payoff):** "I'll show you exactly how at [timestamp]."
*   **Retention Beats:** A new visual or "unlocked" information every 45 seconds.
*   **CTA:** Pivot to workshop link at the midpoint and end.

### Hook Bank (15 Openers)
1. "Stop animating your [X] this way."
2. "A trick I use on a AAA game, now in Unreal." (check the claim is true for each video)
3. "This simple file change saved me 5 hours."
4. "Is your animation rig broken? Do this."
5. "Stop struggling with [X], try this."
6. "The biggest lie in [Animation Topic]."
7. "How I handled [Complex Task] in AC Shadows."
8. "My #1 Unreal tip for 2026."
9. "If you're using [Tool], stop."
10. "Here's the secret to [Result]."
11. "Why your [X] looks unnatural."
12. "Don't ignore this setting in UE5."
13. "Steal my workflow for [Task]."
14. "What the studio doesn't teach you."
15. "Can [Feature] fix your animation?"

### Pre-Record Checklist
- [ ] Script printed/on second monitor.
- [ ] Demo files open and ready.
- [ ] Mic levels checked with a test sentence.
- [ ] Camera focus locked.

---

## 4. Metrics Loop
*   Thresholds below are rules of thumb, not measured for this channel (about 1 subscriber). Replace them with the channel's own medians after 10+ posts.
*   **YouTube:** Impressions CTR (>6% good), AVD (>50% good).
*   **Shorts:** Swipe-away rate (<40% good).
*   **Weekly Template:** 
    *   *Top/Bottom 2 videos by AVD.* 
    *   *Hook Effectiveness:* Did people stay past 3s? 
    *   *CTA Conversion:* Workshop link clicks.
*   **Next Steps:** If AVD drops, trim the hook. If CTR is low, iterate the thumbnail.

---

## 5. Introduction Video
Current scripts, including the short and long credibility intros: `docs/script_intro.md`.

---

## 6. Workflow Routine
*   **Gemini (Manager):** Data crunching, tracking stats in `social_stats.py`, suggesting best posting times, maintaining the manifest.
*   **Claude (Coach):** Script review, thumbnail critique, coaching the owner on tone and brevity.
*   **Routine:**
    *   **Mon:** Review stats, plan next 2 videos.
    *   **Wed:** Script review, final polish.
    *   **Fri:** Content review, documentation update.
