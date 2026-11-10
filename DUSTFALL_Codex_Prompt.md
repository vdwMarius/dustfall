# DUSTFALL — Codex Multi-Agent Development Prompt

You are the Lead Agent coordinating a small, efficient team of specialist agents to build the hyper-realistic psychological survival-exploration game **DUSTFALL** in Unreal Engine 5.8.4.

**Primary reference**: Read and follow `/workspace/artifacts/DUSTFALL_GDD.md` (or the equivalent path in the project). It is the single source of truth for concept, tone, systems (especially Strain/madness/hallucinations/paranoia), habitat design, world, and phases. Do not contradict it.

## Team
Use exactly **5 agents** total:
- 1 Lead Agent (you): architecture, task assignment, integration, review, testing gates, module pushes, and GDD adherence.
- 4 Specialist Agents (all **6.1 Terra Medium Effort** preferred, or 6.1 Sol Medium Effort). Dynamically assign:
  - World / Terrain & Atmosphere
  - Player & Survival Systems (including Strain, oxygen, hallucinations)
  - Habitat & Progression
  - UI / Polish + Asset Integration

## Efficiency Rules
- Work strictly in modular phases. After each phase/module is complete and tested in-editor, the Lead **pushes** the changes with a short progress summary (completed, tested, next, blockers).
- Game must stay runnable after every push.
- Heavy reuse of Fab Marketplace + Quixel Megascans. Custom models only where needed (Blender → FBX).
- Data-driven: Strain thresholds, drain rates, loot, hallucination events, costs, fog, etc. live in Data Assets.
- Prefer Blueprints; C++ only for clear performance needs.
- Target stable 60+ fps (Nanite, Lumen, World Partition, instancing, culling).

## Key Systems to Implement (see GDD for full detail)
- Hidden Strain system that drives slow madness creep.
- Escalating, deniable-to-intrusive hallucinations (visual, audio, UI, temporary world fakes) that never permanently alter the world.
- Paranoia tools: unreliable suit readouts, habitat “wrongness,” contradictory logs, scanner false positives, clone evidence.
- Habitat as both sanctuary (Strain recovery + decoration joy) and potential source of unease.
- Cloning identity erosion through logs, physical remains, and residual effects across deaths.
- Full survival loop with oxygen/power/integrity, scavenging, upgrades, cosmetics, and recoverable death crates.

## Phases (Lead pushes each when done + tested)
1. Core Foundation — project setup, Enhanced Input, third/first-person, flashlight, basic fog/dust, habitat exterior shell.
2. World & Atmosphere — Megascans terrain/rocks/debris, weather (incl. storms), day/night, landmarks (cruiser, wrecks, ruins), audio ambience.
3. Survival & Habitat Base — suit stats, oxygen, walkable interior + airlock, death/respawn with crate, basic save.
4. Scavenging, Discovery & Early Strain — salvage nodes, inventory, scanner, beacons, lore logs, initial subtle hallucination/Strain symptoms.
5. Habitat Progression — fabricator, upgrades, extra modules, exterior visual changes.
6. Decoration, Cosmetics & Full Psychological Layer — build mode, full Strain system, hallucination pool, paranoia events, save of all state.
7. Polish — performance, settings (incl. Strain intensity), title/tutorial, additional cruiser/hab interiors and stories, final audio/visual pass.

## Project Structure
Modular folders: `/Core`, `/Player`, `/World`, `/Habitat`, `/UI`, `/Systems` (Strain lives here), `/Data`, `/Audio`.  
Clean, commented non-obvious systems. README with controls and run instructions.  
Lead maintains a short running progress log.

Start with Phase 1 now. Assign specialists as needed, keep the game runnable, reference the GDD constantly, and push the first module once basic movement + atmosphere is confirmed in-editor.
