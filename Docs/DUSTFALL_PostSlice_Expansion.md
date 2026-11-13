# DUSTFALL — Post-Slice Expansion Document
**Version:** 1.0 (After 2 km × 2 km Playable Slice)  
**Purpose:** Guide for deepening the world, systems, fauna, crafting, and psychological layers once the initial slice is stable.  
**Engine:** Unreal Engine 5.8.4  
**Tone:** Lonely, atmospheric, quietly hopeful on the surface — slow psychological erosion underneath. Strong Soma-style identity and existential horror.

Reference images (generated for art direction):
- Habitat exterior (dusty, lit modules, haze)
- Player suit (third-person, flashlight, worn)
- Crashed ship / cruiser landmark
- Habitat interior (cramped becoming home)
- Example alien scavenger creature

---

## 1. World Scale & Layout

### Recommended Final World Size
- **Core playable area:** 6–8 km radius from the starting habitat (roughly 110–200 km²).  
  Large enough to feel vast and isolating, small enough to remain performant with World Partition + Nanite + instancing.
- **Outer hazard zone:** Additional 2–4 km beyond the core where conditions degrade sharply (see Boundary below).
- **Total streamed world:** ~10–12 km across. Use World Partition so only nearby cells are loaded.

### Current Slice Context
The 2 km × 2 km slice is the **safe starting zone**. Once stable, expand outward in rings.

### Landmark & Content Scattering (Risk vs Reward)
| Distance from Habitat | Content Density & Type | Oxygen / Strain Cost | Notes |
|-----------------------|------------------------|----------------------|-------|
| 0–400 m              | Tutorial salvage, basic debris, first beacons, minor rocks | Very low | Teach loop |
| 400 m – 1.2 km       | Common salvage, small wrecks, ruined hab fragments, early lore | Low–Medium | First real risk |
| 1.2 – 3 km           | Medium wrecks, tool/cosmetic caches, greenhouse seeds, alien fragments | Medium | Requires better suit/oxygen |
| 3 – 6 km             | Major landmarks (giant cruiser sections, large ruined complexes), rare tools, high-value lore | High | Strain rises faster |
| 6 km+                | Outer hazard zone, unique late-game sites, extreme conditions | Very High | Boundary pressure |

**Scattering rules:**
- Seeded procedural placement + hand-placed hero landmarks.
- Paths and flatter traversable corridors between major sites.
- Hazardous stone fields and debris clusters that force detours.
- Previous-clone evidence (abandoned beacons, half-built structures, death crates) appears more frequently farther out.

---

## 2. World Boundary (No Hard Wall)

Do **not** use an invisible wall or hard collision barrier.

### Soft Environmental + Psychological Boundary
1. **Dust Density Ramp** (starts ~6 km out)  
   Exponential fog increase. Visibility drops to <10 m. Wind damage to suit rises. Flashlight becomes nearly useless.

2. **Suit & Strain Collapse**  
   Oxygen drain multiplies. Power systems glitch. Strain gain becomes extreme. Hallucinations intensify (phantom walls, previous clones walking the edge, suit AI warning “boundary protocol active”).

3. **Navigation Failure**  
   Compass spins or points backward. Beacons flicker and disappear. Scanner returns only static.

4. **Physical Soft Repulsion**  
   Strong wind currents push the player back. Footing becomes unstable (slippery dust dunes). Optional late-game: temporary “anchor” item that lets you push a short distance further at great cost.

5. **Narrative Framing**  
   Logs and suit messages imply the playable zone is a monitored crater, a failed terraforming basin, or the edge of a cloning simulation. Crossing feels like leaving the only place the system still recognizes you.

This keeps the world feeling infinite and hostile while giving clear, escalating feedback that turning back is the sane choice.

---

## 3. Refined Habitat Modules & Buildings

Expand the modular system beyond the basic pod.

**Core Modules (craftable / found):**
- Storage Bay
- Workshop (advanced fabricator)
- Greenhouse (see Cooking)
- Observation Dome
- Medical / Stabilizer Bay (reduces Strain decay time)
- Comms Array (lore + distant scanner boosts)
- Power Hub (better solar/wind integration)

**Exterior Refinements:**
- Floodlight arrays
- Reinforced airlock
- Debris shielding
- Landing pad / beacon tower (visible from farther away)

**Visual Progression:**  
Each added module and light should be clearly visible from outside through the haze so returning home feels progressively warmer.

---

## 4. Crafting, Recipes & Cooking

### Material Tiers
- Scrap, Wiring, Polymer, Glass, Power Cells (common)
- Refined Alloys, Circuit Boards, Bio-Gel (mid)
- Alien Fragments, Stabilizer Crystals (rare)

### Key Recipes (examples)
- Suit upgrades (oxygen capacity, integrity plating, scanner range)
- Beacons, floodlights, solar panels
- Habitat modules
- Stabilizer injectors (temporary Strain reduction)
- Tool upgrades found in ruins then crafted/repaired

### Cooking & Greenhouse
Plausible on a dead world via:
- Hydroponic greenhouse module
- Salvaged seeds / spores
- Processed alien biomass (from creatures) or recycled organic matter

**Simple cooking loop:**
- Grow basic nutrient plants or culture fungal mats
- Combine with purified water + scrap seasonings → meals
- Meals restore stamina, slightly reduce Strain, or give short buffs (better cold resistance, slower oxygen use)
- Failed or contaminated meals can increase Strain or cause temporary hallucinations

Keeps the habitat feeling like a home while tying into survival and psychology.

---

## 5. Alien Fauna (Sparse & Plausible)

Life is rare, hardy, and adapted to dust, low light, and extreme conditions. No dense ecosystems.

**Examples:**
- **Dust Crawlers** — Small, multi-legged, chitinous or crystalline scavengers. Burrow, avoid light, drop biomass and chitin when killed. Can nibble unattended salvage.
- **Filter Feeders** — Sessile or slow-moving organisms that strain nutrients from dust. Found near old wrecks. Harvestable for bio-gel.
- **Lurkers** — Larger, rare ambush predators that use dust storms for cover. High risk, high reward (rare materials). Mostly audio and silhouette threats.
- **Spore Drifters** — Airborne or wind-carried organisms. Inhaling them (low suit integrity) raises Strain or causes short hallucinations.

Fauna should feel alien and slightly wrong, reinforcing isolation rather than turning the game into a creature shooter. Most encounters are avoidable.

---

## 6. Engaging Mechanics That Preserve Psychological Horror

**Fun without breaking tone:**
- **Beacon Networks** — Place and chain beacons. Later upgrades let them share power or act as mini-scanners. Losing a chain in a storm feels bad in a good way.
- **Habitat Automation** — Late upgrades (auto-sort storage, timed lights, plant care). Makes home cozier but also gives the suit AI more lines that can glitch under high Strain.
- **Photo / Log Mode** — Players can snapshot views or record short audio logs. These can later be played back with subtle alterations (Soma-style).
- **Risk Tools** — Scanner boosts, temporary shield bursts, or “lean into madness” injectors that improve perception at the cost of stronger hallucinations.
- **Clone Residue** — Finding and interacting with previous-death crates or unfinished builds gives small permanent unlocks or lore, but also raises baseline Strain.

**Soma-Style Additions:**
- Suit AI that occasionally uses old clone designations or references events you haven’t done.
- Optional “continuity” items that let you carry a single personal object (photo, trinket) between deaths — or watch it change.
- Environmental logs that describe the current player’s actions in the past tense.
- Late-game question of whether the habitat itself is “yours” or just the latest shell.

---

## 7. Art & Reference Direction

Use the generated images as primary mood and proportion references:
- Habitat should feel small, damaged, but increasingly lived-in and lit.
- Suit is practical, worn, with visible backpack and tool mounts.
- Landmarks (especially the cruiser) dominate through haze and feel ancient/wrong.
- Creatures stay low-profile and dust-colored.
- Interiors mix warm practical lights with cold emergency lighting and personal clutter.

All new assets should pass through Blender only when Megascans/Fab cannot cover them, then be Nanite-ready.

---

## 8. Implementation Priority After Slice

1. Lock performance and streaming on the 2 km slice.
2. Implement soft boundary prototype (dust + Strain ramp).
3. Add 2–3 new habitat modules + basic greenhouse/cooking.
4. Introduce 1–2 fauna types with simple behaviors.
5. Expand Strain hallucination pool with Soma-flavored events.
6. Place next ring of landmarks and test oxygen/Strain economy.
7. Polish exterior visual progression of the habitat.

---

*This document is a living expansion guide. Update version notes as systems are implemented. Lead Agent should treat it as authoritative for post-slice work alongside the original GDD.*
