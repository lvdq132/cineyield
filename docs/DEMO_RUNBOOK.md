# CineYield Final Demo Runbook

**One-line story:** Upload a finished scene, understand its commercial context, find a compatible sponsor, approve the terms, preview the placement, and generate the branded replacement shot.

- App: `https://cineyield-web-pg7lg7ldma-uc.a.run.app`
- API: `https://cineyield-api-pg7lg7ldma-uc.a.run.app`
- Proven live scene: `scene_b2aee2273df6`
- Proven live proposal: `prop_316889227e39`

## Before recording

1. Run the credentialed gates:

   ```bash
   bash scripts/smoke-contest.sh https://cineyield-api-pg7lg7ldma-uc.a.run.app
   bash scripts/e2e-prod-smoke.sh https://cineyield-api-pg7lg7ldma-uc.a.run.app
   ```

2. Open the Library, Scene, Marketplace, Deal, and Analytics pages once to warm the services.
3. Keep the rooftop MP4 ready for upload. It must be a real MP4—not the old synthetic black fixture.
4. Start from a fresh proposal when recording the approval controls. Generation can take longer than the edit; record the real progress state, then cut forward to the completed result.

## Three-minute shot list

| Time | Screen and action | Voiceover |
|---|---|---|
| 0:00–0:12 | Library → **Analyze a Cut** → choose the rooftop MP4 | “Finished film contains valuable, unmonetized sponsor inventory. CineYield turns the scene itself into a commercial workflow.” |
| 0:12–0:35 | Real upload progress and pipeline stages | “The cut is stored in Google Cloud, segmented into an exact source clip and frame, then Gemini reads the video. An ADK agent coordinates scene intelligence, sponsor discovery, rights, creative safety, and proposal creation.” |
| 0:35–0:58 | Scene Analysis with the extracted frame, three detected props, safety/mood/narrative scores, and placement zones | “This is the frame extracted from that upload—not a stock placeholder. Gemini found the headphones, mug, and phone, understood the scene, and qualified where a placement could belong.” |
| 0:58–1:18 | Open the top opportunity / Marketplace match | “The Market Agent queries live campaign inventory through the official ClickHouse MCP server. Deterministic scoring ranks the sponsor; Gemini never invents the commercial score.” |
| 1:18–1:38 | Open proposal and approve it | “The producer reviews the sponsor brief, terms, rights, and guardrails. Approval persists in ClickHouse and unlocks production—no front-end-only state.” |
| 1:38–2:05 | Generation Studio: exact Original / Nano Banana proposal comparison, then approve | “Nano Banana receives the source frame, selected sponsor, product, placement direction, and non-negotiable guardrails. It returns a clean, scene-preserving reference—not a box, cutout, or overlay.” |
| 2:05–2:35 | Veo Original / Branded playable comparison | “Gemini re-reads the exact source segment for camera continuity. Veo animates the approved plate into the replacement shot, with regenerate, approve, and reject controls.” |
| 2:35–2:50 | Approve the clip; show audit status and Analytics | “Every decision and generation revision is recorded. Approved revenue and agent traces update from ClickHouse.” |
| 2:50–3:00 | Hold on final comparison | “CineYield is the revenue layer between a finished cut and a production-ready sponsor deal.” |

## Non-negotiable proof in frame

- The upload progress must be shown at least once.
- The Scene Analysis image must visibly match the uploaded rooftop cut.
- Show `Gemini`, `mcp-clickhouse`, `Nano Banana`, and `Veo` labels in their respective UI states.
- Show the exact Original / Branded comparisons for both image and video.
- Show one real producer decision persisting after refresh.
- Never imply that Veo performs arbitrary source-video inpainting. Gemini reads the source segment for continuity; Veo 3.1 generates from the approved branded first frame under that continuity brief.

## Recovery

- Gemini/ADK analysis normally takes roughly one minute on a cold run. Leave the genuine progress state in the recording and edit out idle time.
- Nano Banana normally takes 15–30 seconds. A failed aesthetic result is an opportunity to show **Regenerate placement**.
- Veo is asynchronous and may take several minutes. Record the real rendering state, then cut to the completed job.
- If a generation job fails, its error is persisted. Regenerate creates a new auditable revision rather than overwriting history.

## Final verbal close

“ChatGPT can describe a scene. CineYield closes the loop: it understands the actual cut, queries live sponsor demand, enforces rights and creative constraints, records the commercial approval, and generates production-ready branded media under producer control.”
