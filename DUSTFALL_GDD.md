# DUSTFALL
**Game Design Document**  
*Working Title*  
**Version:** 1.1 (2026-11-11 visual direction update)
**Engine:** Unreal Engine 5.8.4  
**Genre:** Hyper-realistic Survival Exploration / Psychological Atmospheric  
**Target:** Mid-range hardware, stable 60+ fps  

---

## 1. High Concept
The player is a clone who wakes inside a small damaged habitat module on a vast, barren, dead planet. They are briefed that their previous body died. The world is a low-visibility dust wasteland filled with debris, hazardous rock, crashed starships, a giant derelict space cruiser, and ruined habitat modules.  

The only safe place is the habitat. Players explore, scavenge, discover tools and cosmetics, read logs left by previous versions of themselves and other failed occupants, then return to repair, expand, upgrade, and decorate the habitat until it slowly becomes a home.  

Tone is lonely, atmospheric, and quietly hopeful on the surface — but underneath runs a slow psychological erosion. Isolation, contradictory evidence, and a creeping madness make the player increasingly unsure of their suit, their memories, their logs, and eventually the habitat itself.

---

## 2. Core Fantasy & Pillars
- **Fragile Sanctuary**: The habitat is the emotional and mechanical center. Expanding and decorating it should feel meaningful and comforting.
- **Oppressive Isolation**: The planet is vast, empty, and hostile. Visibility is low. Sound is dominated by wind and suit systems.
- **Identity Erosion**: The cloning premise is used to undermine certainty. Logs, physical evidence, and hallucinations make the player question whether they are the first, the last, or simply the latest.
- **Quiet Psychological Pressure**: Madness and paranoia arrive slowly through systems rather than jump scares.
- **Risk vs Reward Exploration**: Better loot, tools, cosmetics, and lore sit further out or deeper in wrecks, costing oxygen, power, and mental strain.

---

## 3. Story & Lore
The player is informed they are a clone created after their previous body died. Early logs from “previous self” are coherent and helpful. Later logs become fragmented, paranoid, or describe events the current player has not yet experienced.  

Environmental storytelling includes:
- Abandoned suits identical to the player’s
- Partial habitat expansions left unfinished
- Body containment canisters with matching serial numbers
- Ruined hab modules and the giant cruiser containing records of other groups or solitary survivors who also failed

Some logs are written in a voice that matches the current player’s actions or reference rooms/beacons the player has not yet created. The cloning program and the fate of the planet are revealed gradually and contradictorily.

---

## 4. Psychological Design (Madness, Hallucinations, Paranoia)

### 4.1 Strain / Cognitive Strain System
A hidden **Strain** value increases from:
- Time spent outside the habitat
- Low oxygen or suit integrity
- Dust storms
- Reading high-strain lore
- Consecutive clone cycles / deaths

Strain decays slowly only while resting in a powered, lit, relatively quiet habitat. The player never sees the exact number — only symptoms. High Strain unlocks escalating hallucination tiers and small persistent effects.

### 4.2 Hallucination Escalation
**Early (deniable):**
- Dust briefly forms distant humanoid or suit-like shapes
- Second set of breathing on the suit mic
- Scanner/compass highlights non-existent salvage
- Data log plays in the player’s own voice saying something unremembered

**Mid (intermittent but clear):**
- Flashlight catches a figure that vanishes when fully looked at
- Habitat doors or furniture slightly shifted on return
- False oxygen warnings or HUD showing a different serial/callsign
- Logs describing the exact route or decorations the player just created

**Late (intrusive):**
- Brief visual overlays of the habitat in a previous damaged or bloodied state
- Suit AI using a prior clone designation and mentioning “the others”
- Phantom beacons leading to empty ground or previous death sites
- Footsteps on the exterior hull that stop when the airlock is opened

Hallucinations are short-lived, leave no permanent world state changes, and can be interrupted by returning to the habitat or using rare stabilizer items.

### 4.3 Paranoia & Unsafe Systems
- Suit readouts lag, conflict, or briefly fail at high Strain
- Habitat power flickers, exterior camera feeds (if built) show movement, airlock cycles alone
- Decorations or greenhouse plants appear slightly wrong after long trips
- Evidence of “your” previous actions you do not remember
- Scanner false positives on life signs or intact tech; occasional missed real threats
- Some salvage degrades or increases Strain when used

### 4.4 Integration with Loop
Long-range trips (especially to the cruiser or deep ruins) raise Strain fastest. Returning home and decorating reduces it but never fully resets it. Later clone lives can start with residual Strain or unlocked hallucination types. Optional late upgrades can suppress symptoms at a cost or amplify them for temporary mechanical benefits.

---

## 5. Gameplay Loop
1. Wake / rest in habitat  
2. Prepare (check oxygen, power, suit, optional beacons)  
3. Explore the haze (scavenge, discover tools/cosmetics, read lore)  
4. Manage oxygen, power, integrity, and rising Strain  
5. Return before critical failure  
6. Craft upgrades, expand modules, decorate, reduce Strain  
7. Push further next cycle  

**Fail State**: Oxygen or Suit Integrity reaches zero → player dies, wakes as a new clone in the habitat. Carried inventory is left in a recoverable crate at the death location. Some Strain or hallucination unlocks may carry over.

---

## 6. Player & Suit
- Third-person camera with first-person toggle
- Enhanced Input: WASD move, mouse look, Shift sprint, Space jump, E interact, F flashlight, Tab inventory, Q scanner
- Suit stats: Oxygen, Power, Suit Integrity, Stamina, (hidden) Strain
- Oxygen drains outside, refills inside habitat
- Low oxygen: audio warnings, heavy breathing, vignette, increased Strain gain
- Scanner pulses and briefly highlights salvage through haze (reliability degrades with Strain)
- Cosmetics found in the world can be equipped and visibly change the suit

---

## 7. Habitat (Emotional & Mechanical Core)
Starts as a small damaged pod with flickering light, bed, and broken fabricator. Interior is fully walkable with airlock transition.

User art direction (2026-11-13): the existing square/basic functional prototype
is not the final habitat. Finish a rounded damaged industrial pod and convincing
interior toward the supplied references, preserving the tested sanctuary/airlock.

**Upgrades** (crafted at fabricator):
- Repair power, oxygen recycler, airlock
- Larger oxygen capacity, better suit, stronger flashlight, longer-range scanner
- Additional modules: storage, workshop, greenhouse, observation dome
- Exterior: floodlights, solar panels, wind turbine, comms antenna

**Decoration / Build Mode**:
- Grid snapping, rotation, color tinting
- Furniture, lights, rugs, plants (greenhouse), shelves, posters, alien trophies
- Player cosmetics
- Changes are visible from outside (more modules, more lights) so home looks more welcoming on return

The habitat remains the primary place Strain decreases, but high-Strain events can make it feel temporarily unsafe.

---

## 8. World & Exploration
- Vast barren wasteland: dunes, craters, rocky ridges, dry canyons, hazardous stones, debris fields, twisted metal
- Low visibility core mood: dense exponential fog, wind-blown dust particles, dim reddish-brown sky, faint distant sun
- Dynamic weather: relative calm, haze and dust storms, all retaining persistent airborne dust. Daylight must read clearly through the dust rather than feel excessively dark. Recognizable silhouettes should remain readable at 40+ metres, including settled storms; stronger gusts can briefly obscure more. Storms increase suit damage and Strain when those systems are implemented.
- Use seeded Unreal PCG for suitable environment elements and scattering, with clustered natural distribution, varied sizes/heights, terrain-aware seating and clear traversal routes. Assemble open-backed rock scans into complete-looking boulders/cliffs using overlapping rotated copies; hide unfinished faces.
- Day/night cycle; night is near pitch black — reliance on flashlight and placed beacons
- Points of interest: crashed starships, giant space cruiser (major multi-room exploration site), ruined hab modules with occupant stories, alien-style ruins (monoliths, arches, partially enterable structures)
- Seeded / consistent layout so the world remains the same across sessions
- User terrain direction (2026-11-13): actual hills, mounds, jagged rocky zones,
  ridges, depressions/ravines and pitfalls must create hostile otherworldly
  geography. Dense small scatter on flat ground is insufficient. Preserve
  deliberate traversal/home access and test readable hazards and recovery in fog.
- Habitat appears as a glowing landmark with compass home marker

---

## 9. Scavenging & Progression
Salvage types: scrap metal, wiring, glass, polymer, power cells, rare alien fragments, tools, cosmetics, lore items.  

Rarer and better items are found further from home or deeper inside wrecks and the cruiser, creating oxygen/Strain risk-reward.  

Lore fragments (data logs, notes, glyph tablets) reveal the planet’s fate and the cloning program while feeding the psychological systems.

---

## 10. UI & Presentation
- Minimal diegetic HUD: oxygen, power, integrity, stamina, compass with home marker
- Inventory grid, crafting menu (fabricator), build/decorate menu (habitat)
- Pause menu: save/load, graphics, sensitivity, Strain symptom intensity (accessibility)
- Clean sci-fi aesthetic: thin lines, monospace elements, amber on dark
- Visual and audio feedback scales with Strain (subtle post-process, audio layering)

---

## 11. Technical Direction (UE 5.8.4)
- Nanite, Lumen, World Partition, Virtual Shadow Maps, Enhanced Input
- Use appropriate Unreal rendering/generation tools, PCG, instancing and culling to improve visual quality within measured frame-time budgets. Verify Nanite suitability and profile Lumen, volumetrics and dust effects; tool enablement alone does not establish a performance improvement.
- Heavy use of Fab Marketplace + Quixel Megascans for rocks, terrain, debris, surfaces
- Custom assets (habitat modules, ships, tools, cosmetics, key props) modeled in Blender and imported via FBX
- C++ is enabled for shared core gameplay rules and future systems work, with Blueprint-callable interfaces and data-driven tuning. Keep presentation and iteration-friendly orchestration in Blueprints where appropriate. This follows the user's 2026-11-12 direction.
- MetaSounds for dynamic wind, breathing, heartbeat, suit warnings, and hallucination audio
- Data Assets for all tunable values (drain rates, costs, loot tables, Strain thresholds, fog, hallucination pools)
- SaveGame system covering inventory, habitat state (modules + decorations), player progression, Strain-related unlocks, and world flags
- Performance target: stable 60+ fps on mid-range hardware via instancing, HISM, LOD, culling, and World Partition streaming

---

## 12. Development Structure (for Agents)
**Team**: 1 Lead Agent + 4 Specialist Agents (all 6.1 Terra Medium Effort preferred, or Sol Medium).  

Roles assigned dynamically by Lead:
- World / Terrain & Atmosphere
- Player & Survival Systems (including Strain)
- Habitat & Progression
- UI / Polish + Asset Integration

**Rules**:
- Work in modular phases. Game must remain runnable after each phase.
- Lead reviews, integrates, and **pushes** each completed module with a short progress note (what was done, what was tested, what’s next).
- Prefer data-driven design and heavy asset reuse.
- Reference this GDD as the single source of truth for tone, systems, and scope.

**Phases** (high-level):
1. Core Foundation (movement, camera, basic atmosphere, habitat shell)
2. World & Atmosphere (Megascans scattering, weather, landmarks including cruiser)
3. Survival & Habitat Base (stats, oxygen, interior, death/respawn)
4. Scavenging, Discovery & early Strain symptoms
5. Habitat Progression (crafting, modules, exterior changes)
6. Decoration, Cosmetics & full Strain/hallucination system
7. Polish, performance, tutorial, additional interior stories

---

## 13. Accessibility & Tone Controls
- Option to reduce hallucination intensity or disable certain audio/visual symptoms
- Clear tutorial prompts in the first minutes
- Strain effects remain readable; critical suit warnings stay reliable even at high Strain

---

Version 1.1 records the user's 2026-11-11 tested-build feedback and replaces the
earlier metre-scale storm visibility target with readable 40+ metre silhouettes.
See `Docs/Phase3_Plan.md` and `Docs/References/Phase3/` for implementation order
and the supplied habitat/interior, explorable wreck and suit visual references.

*End of GDD v1.1 — Living document.*
