# Phase 1 habitat blockout

This is a temporary exterior landmark made from Unreal Engine primitives, not a finished habitat asset. Replace it later with custom Blender models imported as FBX. Phase 1 does not implement a walkable interior, airlock, oxygen, or interaction.

## Placement and construction

Use centimetres, Z up, and a habitat-local origin at the centre of the ground footprint. Place the origin on level ground; all offsets below are relative to it. Positive X is the future entrance direction. The standard engine cube is 100 cm on each side, centred on its pivot; scale values below assume that cube. Zero rotation unless stated otherwise.

| Piece | Centre (X, Y, Z) | Scale (X, Y, Z) | Purpose |
| --- | --- | --- | --- |
| Main pod | (0, 0, 150) | (6, 4, 2.8) | 600 × 400 × 280 cm closed shell, bottom at Z 10 |
| Base | (0, 0, 10) | (6.4, 4.4, 0.2) | 20 cm thick footing, bottom at ground |
| Entrance placeholder | (320, 0, 130) | (0.4, 1.6, 2.4) | Sealed panel on +X face; visual marker only |
| Roof strip | (0, 0, 295) | (5.2, 0.35, 0.1) | Small raised silhouette detail |
| Beacon housing | (0, 0, 315) | (0.35, 0.35, 0.3) | Marks the home light |

Give the shell a muted, dusty metal appearance and the entrance panel a darker contrasting finish. Add a warm amber point light at (0, 0, 345), with a modest radius initially around 1200 cm; tune intensity and radius in the actual fog and exposure so it reads as a welcoming landmark without washing out the scene. The light and housing are visual only, not a powered system. Keep geometry and light grouped or attached under a clearly named habitat root for relocation.

## Collision and spawn

Use simple blocking collision for the main pod and base. The entrance is sealed in this phase; avoid collision gaps or an apparent usable opening. Decorative roof and beacon pieces can have collision disabled. Place Player Start on tested, level terrain outside the entrance, for example local (550, 0, 100), facing toward the pod (yaw 180°). Its final Z must be adjusted to the terrain and actual player capsule: the capsule must clear the ground and all habitat collision. Test Play from the start and walk around the shell to verify no initial overlap, trapping, or inaccessible terrain. Do not place the start inside the solid cube.

## Phase 3 extension

Reserve a clear approach along +X, at least 300 cm wide and 500 cm beyond the pod face, for a future airlock. Replace the solid main cube and entrance placeholder with a hollow, collidable shell and an operable airlock; retain a clear doorway and walkable floor. The intended interior accommodates a bed, broken fabricator, and damaged lighting. Validate player capsule clearance, door transitions, and a safe interior respawn then. No survival or sanctuary behaviour is implied by this blockout.
