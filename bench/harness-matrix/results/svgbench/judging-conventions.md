# Judging conventions — one threshold across every artifact

All 84 artifacts in `scores.json` were judged by `claude-opus-5` from
headless-Chrome PNG renders, strictly and per requirement. Score is requirements
met ÷ total, the SVGBench metric. The judge is itself a contestant on this board:
21 of the 84 artifacts are `claude/claude-opus-5`'s own, so that row is
self-judged and is marked as such wherever it is cited.

The judging ran as seven passes, one per question (q0, q4, q5, q6, q7, q12, q13),
each in its own agent session. This document is why the seven passes share one
threshold instead of drifting into seven. It is kept next to the verdicts so a
reader can see *why* a requirement was failed, not just that it was. Every rule
below decided real pass/fail calls in `verdicts/`.

## The rule

- Judge the PNG render. The SVG source is never opened to help decide.
- A requirement with several conditions fails if ANY one condition fails.
- Colour words are binding: "grey dolphin" fails for a blue one.
- Counts are binding: "two small clouds" fails for four, "exactly four fruits"
  fails for five, "at least three furrows" fails for two.
- Named placement is binding: "on the left side of the counter" fails when the
  object sits on the right.
- Any detail that cannot be resolved in the full render is cropped at 2x before
  it is decided. No squinting and guessing.
- Every `false` carries the failing condition in its `note`. A pass leaves `note`
  empty.

## Binding calls

These accumulated across the seven passes. The first block came out of the q0/q7
calibration on `claude/claude-opus-4-8/dolphin-hoop.svg`; each later pass
inherited the table and appended to it. A row applies to every artifact on the
board, not only the question it arose on.

| Situation | Ruling | Rationale |
|---|---|---|
| A trainer's arm ends in a rounded, fingerless shape | Counts as a "hand" | The requirement asks for an arm and hand extending into frame, not for articulated fingers. |
| The fish sits at the tip of an open jaw rather than inside the gape | Requirement still passes | The requirement is "about to bite", which a jaw closing on the fish satisfies. |
| Mouth drawn as a wide-open V | Counts as "wide open" | Shape reads unambiguously as an open mouth at render scale. |
| Part of the body crosses below the drawn waterline | "entire body in mid-air" FAILS | Failed on the calibration artifact for a fluke drawn below the water line. |
| A splash exists but is small and offset from the exit point | "large splash effect at the point where the dolphin has exited" FAILS | Both the size and the location are conditions. |
| A ring alternating exactly two colours (red/white, red/yellow) | Counts as "multi-coloured" | Two distinct alternating colours is more than one colour; the calibration artifact passed on a red/yellow ring, so a red/white one must too. |
| Wherever a requirement names **grey / gray** (q7 "grey dolphin", q6 req 7 "gray speed lines") | One word, one meaning: a near-neutral fill. It is measured on two bases, and this row carries both. **Body colour (q7) — red-minus-blue spread:** sample the mid-tone flank; about 45 or less counts as grey, about 80 or more is a blue/teal and FAILS. **Line and fill colour (q6) — max-minus-min spread:** 40 or less is gray at any lightness, at the same bar as the binding white rule; a warm tan or beige streak FAILS. The two bases agree on a true neutral and differ only in how a colour cast is measured. No artifact's outcome on this board turns on the difference | Puts the binding colour word on a repeatable footing and makes it do the same work on a dolphin's flank, a speed line, an awning and an envelope stripe. The q7 calibration dolphin that passed measures 44 red-to-blue (RGB 102,126,146) while the teal and steel-blue dolphins measure 85-91. The q6 qwen streaks sample RGB 210,166,111 and 207,164,111 - a max-minus-min spread of about 99, plainly tan at 1x. |
| A beak parted only as a thin sliver or narrow wedge (gape well under about 20 degrees) | "wide open" FAILS | Distinct from the wide-open V already allowed; a hairline gape does not read as an open mouth at render scale. |
| "mid-section passing through the center of the hoop" | Passes when the hoop's centre point falls inside the dolphin's body silhouette; FAILS when the centre point is empty background, or when the "hoop" is an open unclosed ribbon so nothing passes through it | Gives the placement clause a single checkable test instead of an impression. |
| Splash size threshold | Passes with visible vertical spray or a broad mound spanning roughly 15% of canvas width at the exit point; a row of low bumps, or faint translucent shards with no spray, FAILS | Sets the "large" bar consistently once, so the same drawing style is not passed in one file and failed in another. |
| Where the sea is drawn as a band, which line is the waterline | The band's top edge. A body part drawn over the sea band is not in mid-air; a part enclosed inside drawn splash foam above that edge still counts as airborne | Foam is spray, not water; the top edge is the only unambiguous surface line in a flat illustration. |
| Brown vs black hooves (q0 req 5) | Sample the hoof fill: a red-minus-blue channel spread of 15 or more counts as brown; a near-neutral dark fill (spread under 15) reads as black and FAILS | Puts the binding colour word on the same measurable footing as the grey-vs-blue rule. The q0 data separates cleanly: claude-opus-5 hooves measure 6 and 12 and qwen3.8-flash-next 0, while gpt-5.6-terra measures 18-34 and fable-5-1 38-42. |
| "blade partially buried in the soil, actively turning over a chunk of earth" | Passes only when BOTH hold. **Buried clause:** part of the share is covered by the SOIL MASS - the ground fill itself, a mound, ridge or furrow wall at the share, or a curled slice of earth still attached to the ground - OR the share's silhouette crosses below a drawn soil-surface line (the edge between the standing field surface and the cut or plowed soil, or the top edge of a mound). Detached clods, chips or airborne debris drawn OVER the share are NOT occlusion: a blade whose full outline reads as sitting on top of the surface is not buried just because flying debris crosses in front of it. A share drawn fully above the surface with its whole outline visible FAILS, whether the loose clods lie beside it or on top of it. **Turning clause:** a chunk of earth is visibly lifted - a clod, a curled slice, or a mound at the share. Detached and airborne clods DO satisfy this clause | Flat vector art rarely occludes, so crossing below the surface line counts as "in the soil" - the same treatment the waterline rule already gives. But counting flying debris as occlusion would let any artifact pass the buried clause by scattering clods over the blade, and the word "buried" would stop doing work: debris shows the turning, not the burying, so each clause reads the debris its own way. Both clauses are conditions, so both must hold. |
| What counts as a "dark furrow" and where it must be | Count only lines or bands DARKER than the surrounding soil; highlight lines lighter than the field never count. Passes when at least three such dark bands lie in the region behind the plow - a field uniformly ruled with furrow lines satisfies this, since three of those lines fall behind the plow | Otherwise a field of light ridge-highlights (gpt-5.6-terra) scores the same as one of dark cut furrows (claude-opus-5), and the word "dark" in the requirement does no work. |
| "leaning forward as if pulling" | Passes when the head and neck are lowered and thrust forward below the shoulder line with the traces taut to the plow, OR the torso tilts head-down with braced legs. FAILS only for a squarely standing cow whose head is held level with or above its back | Head-down into a taut harness is the draft pose; requiring a dramatic body tilt would fail nearly every flat side-view illustration and split near-identical poses arbitrarily. |
| Second clause of "short green grass, which is visibly being overturned by the plow" | Needs green sod visibly lifted, curled or flipped at the share. A plow merely positioned at the green/brown boundary that turns only bare brown soil FAILS, as does a field whose "grass" is tan stubble | Both clauses are conditions. Applied identically to claude-opus-5 (fails on the colour) and fable-5-1 (fails on the overturning). |
| Distant green hills beyond the horizon, with the field itself bare soil edge to edge | Not an "unplowed section of the field": requirement 10 FAILS, and so does requirement 11 for want of grass in the field | The requirement splits the field, not the scene; background scenery on the far side of the horizon line is not part of the field being plowed. |
| What counts as a "claw-foot" bathtub (q4 req 3) | The tub must stand on discrete feet whose silhouette reads as an animal foot - separate toes or lobes, visible claws, or a gripped ball. A smooth flared pedestal or trumpet stub, a plain rectangular block, or a tub resting flat on the floor all FAIL | The word "claw" has to do work, exactly as the binding colour words do. The q4 data separates cleanly: three claude-opus-5 renders draw two or three splayed toe lobes, while the claude base and gpt-5.6-terra v3 draw a featureless flare and qwen3.8-flash-next a rounded rectangular stub. |
| "the lower third of the duck submerged" (q4 req 5) | Measure the water-surface line against the duck's full drawn silhouette (including any translucent underwater part). Passes when the duck's silhouette is interrupted by or continues below that line AND the portion below it is between 20% and 50% of the silhouette height. FAILS when the whole duck outline sits above the line, when no water line is drawn at all, or when only a thin sliver (under 20%) falls below | Turns "lower third" into one repeatable measurement instead of an impression. The observed values split cleanly: 26/32/34% pass, 17/13/0% fail. A duck cut off exactly at the surface still counts as submerged up to its cut - flat vector art rarely draws what is underwater. |
| "concentric circular ripples in the water around its base" (q4 req 6) | Needs at least two nested arcs or rings centred on the duck's base. Long horizontal wavy strokes spanning the whole tub, a single dark shadow ellipse under the duck, or one or two isolated straight dashes at the waterline all FAIL | Otherwise generic water-texture strokes, which nearly every artifact draws, would satisfy a requirement that specifically asks for concentric rings caused by the duck. |
| "semi-transparent white, light pink, and light blue fills" (q4 req 7) | All three hues must be discernible on the bubbles at 1x render scale. A hairline iridescent crescent visible only at 8x zoom (measured at 4-50 px in an 800x600 render) is not a "light pink fill", and a pink soap bar elsewhere in the scene is not a bubble | The requirement names three fills, and a colour nobody can see in the render is not a fill. All 11 q4 artifacts fail this requirement; only claude-opus-5 puts any pink on a bubble at all. |
| "a large pile of bubbles against one side of the tub" (q4 req 9) | Needs a bubble mass banked at a side or end of the tub that rises above the rim or spans roughly a quarter or more of the tub's interior width. Small symmetric clusters of about six overlapping circles at each end (18-20% of tub width, sitting flat on the water) FAIL, as does an evenly spaced single-file row of bubbles across the whole tub. Having a pile on both sides does not fail the clause - the requirement does not say "only one side" | Sets the "large" bar once, the same way the splash-size rule does for q7, so the same drawing style is not passed in one file and failed in another. |
| A figure clipped by a foreground shape so a feature is sheared in half | Judge what renders. A duck whose head-top is cut flat by the tub rim has no "distinct body and head" (req 1 FAILS), and an eye cut into a flat-topped half-disc is not "a simple black dot" (req 2 FAILS) | Clipping is a visible defect at 1x, not a stylistic choice; the render is the artifact, so the requirement is judged against the shape actually drawn. |
| "envelope featuring vertical red and white stripes" (q5 req 2) | Passes when the envelope carries both clearly red and clearly white vertical stripes; extra stripe colours do NOT fail it. "White" means a near-neutral light fill: all channels >= 200 and a max-minus-min spread <= 40. Sampled values separate cleanly - claude-opus-5 v2/v3/animated light stripe RGB 251,241,220 (spread 31) is white, while gpt-5.6-terra 255,223,151 (spread 104) and the claude base 226,190,76 are yellows | "Featuring" is not "only", so a red/white/blue envelope still features red and white stripes; but a stripe that measures as a yellow is not a white one, which keeps the colour word binding. |
| "four human figures ... two adults and two children" (q5 req 5) | The count of four is one condition and the 2+2 split is another. The split passes when the figures separate into two visibly larger and two visibly smaller, measured on head diameter or overall figure scale with the smaller pair at about 85% or less of the larger pair. Four figures at one scale FAIL even when the count is right | Otherwise "styled as a family: two adults and two children" collapses into a head count. The gpt-5.6-terra figures measure 70/67 against 52/57 px (80%), so they pass on measurement even though the poses are near-identical. |
| "on a corner of the blanket" (q5 req 7) | Judge the object's CONTACT footprint (its base), not its drawn body, in the blanket's own quad: pass only when the base lies in the outer third along BOTH the left-right and the near-far axis - a corner cell of a 3x3 grid over the quad. A basket in the middle of an edge, in the centre, or off the blanket entirely FAILS. A tall basket whose top happens to reach near a far corner is still placed where its base sits | Flat perspective art draws tall objects overlapping the far edge, so body overlap would put almost any basket "on a corner". The q5 data separates on this: qwen3.8-27b-8bit sits at 85% across and 74% forward (passes) while all four claude-opus-5 baskets sit at 11-26% across but 60-64% forward, i.e. halfway down the left edge. |
| "bright yellow sun" | Any clearly yellow disc passes, however pastel; only a white, orange or red sun fails. Measured suns run 255,239,168 (claude-opus-5) to 245,241,183 (gpt-5.6-terra v1) and all read as yellow | Illustration suns are almost always a soft pale yellow; a saturation bar here would fail every artifact on the board and make the requirement do no work. |
| What counts when a requirement says "two small, distant clouds" | Count only shapes with a cloud silhouette, including a faint wispy one and one clipped by the canvas edge. Tiny perfectly round dots of about 8 px or less read as sparkles or stars and are NOT clouds, and a second small hot air balloon in the sky is not a cloud either | Without this, gpt-5.6-terra's sparkle dots would turn an exact two-cloud sky into a six-object sky, and the count clause would punish decoration rather than cloud count. |
| Counting "two horizontal metal hoops" on a barrel (q13 req 1) | Count every distinct grey/metallic band that encircles the barrel body, **including one drawn immediately below the rim** - that is a hoop, not the rim itself (the rim is the dark chime ellipse the band sits under). Bands drawn in the same brown palette as the staves, with no grey or metallic tone anywhere, are wood shading and are not hoops at all | All four claude-opus-5 barrels draw three identical grey banded hoops (one under the rim, two lower), so ignoring the top one would silently turn a three-hoop drawing into a two-hoop pass. gpt-5.6-terra v1 draws four or five brown bands sampling 100,44,21 and 141,69,28 against wood at 92,38,22 - no metal at all. qwen3.8-27b-8bit is the only artifact with exactly two silver hoops. |
| "buried in a mound of sand, so only the top half is visible" (q13 req 2) | Measure the barrel silhouette by row. Passes when the ground line cuts the barrel at **85% or more of its maximum drawn width** (i.e. at or above the mid-bulge, since a barrel is widest at half height) AND the visible height above the ground is no more than about 0.95x that maximum width. FAILS when the silhouette has tapered back in below the bulge, when the barrel's bottom or base curve is drawn above the sand, or when the barrel simply stands on the surface | Turns "top half" into one repeatable measurement, the way the "lower third of the duck" rule does. The q13 data separates cleanly: claude base 98% of max width at the cut and h/w 0.71 (pass), claude v2 100% and 0.61 (pass), qwen 98% and 0.80 (pass), against claude v3/animated 54-58% of max width (fail) and gpt-5.6-terra h/w 0.97-1.05 with the base curve drawn (fail). |
| Which fills count as "red rubies, green emeralds, blue sapphires" (q13 req 7) | Decide on HSV hue of the gem's base fill: **red** = hue 340-360 or 0-20, **green** = hue 80-165, **blue** = hue 200-260. A teal or cyan fill (hue about 166-199) is neither green nor blue, and a violet fill (hue 260-330) is not blue. All three must be present | Keeps the three named colour words binding while staying measurable. Crimson/ruby fills (216,30,91 and 227,44,101, hue 340-341, essentially the standard ruby #E0115F) count as red - rubies are conventionally drawn that way. The data separates: claude has 341/146/214 degrees (all three), gpt-5.6-terra v2/v3/animated have only 349 and 169, gpt v1 has 353/119 plus a 185 cyan and a 282 violet, qwen has 355 plus a 175 teal and a yellow. |
| "a large pile of shiny gold coins, both inside and outside the barrel" (q13 req 6) | Both the inside and the outside must show a coin mass - roughly eight or more coins heaped or clustered together. A handful of isolated coins scattered singly across the sand does NOT make a large pile | Otherwise three loose coins dropped on a dune scores the same as the twenty-plus heaped spill the requirement describes, and the words "large pile" do no work. gpt-5.6-terra puts 0-3 coins outside and qwen 6 spread evenly to both sides; all four claude renders heap twenty or more. |
| "draped over the edge ... trailing down into the spilled coins" (q13 req 8) | Both clauses are conditions. **Draped:** the string must cross the barrel's rim. **Trailing into:** its lowest pearl must touch or overlap a coin that is part of the spill (on the barrel's outer face or on the sand). A string that ends on bare wood or bare sand, more than about one pearl-diameter from any coin, FAILS, and loose unstrung beads are not a string at all | Splits the claude lineage on measurement rather than impression: v3 and animated end with the last pearl overlapping a spill coin (pass), the base ends in bare wood on the opposite side from the spill and v2 stops about two pearl-diameters short (both fail). |
| "bright highlights and glint effects on the coins, gems, and goblet" (q13 req 10) | All three named object classes must actually carry a highlight - a lighter facet or gradient, a specular band, or a drawn sparkle on the object. A flat single-fill gem (one colour across its whole area) FAILS. If the scene contains no goblet at all, the requirement FAILS, since an absent object cannot carry the required glint | Consistent with "a requirement with several conditions fails if ANY condition fails". The claude base gem samples one uniform RGB 216,30,91 across its area while v2/v3/animated gems carry two facet tones; only v3 and animated also have a goblet to glint. |
| The q5 "white" measurement applies wherever a requirement names white (q12 req 2, "red and white striped canopy") | Same test as the envelope stripes: white means all channels >= 200 with a max-minus-min spread <= 40. A cream or buttery light stripe FAILS | The colour word must do the same work on an awning as on an envelope. The q12 data separates as cleanly as the q5 data did: all four qwen3.8-flash-next canopies sample RGB 253,240,224 (spread 29, white), while the four gpt-5.6-terra canopies sample 247-251, 227-234, 162-192 (spread 57-87, a cream) - and the difference is visible at 1x, not only in the numbers. |
| What counts as a "wicker basket" — **every requirement on the board that names wicker: q5 req 2, q12 req 4 and q12 req 6** | The container must read as woven: a visible weave, cross-hatch or basket-weave banding, in a rounded or tapered basket silhouette. A plain rectangular or trapezoidal wooden crate - flat fill, a border, plank lines, or a single cross of one horizontal and one vertical band - is a crate, not a wicker basket. A lattice of several bands in BOTH axes over a contrasting panel fill is a weave and passes | Directly parallel to the q13 ruling that brown bands in the stave palette are not "metal hoops": a named material has to be drawn, not assumed. All 8 q12 artifacts display fruit in plain wooden crates, checked at 4-5x on each. q5 req 2 also names a wicker basket and was judged two passes before this row existed, so all 9 q5 balloon baskets were re-cropped at 6-14x and re-checked against it - see "Added after the q5 wicker re-check" below. |
| What counts as a "chalkboard" sign (q12 req 9) | The board must be a dark slate/black/dark-green panel carrying light (chalk-coloured) lettering. A light cream or wooden board with dark lettering is a painted sign and FAILS | Same class of binding descriptor as the colour words. The q12 data separates: all four gpt-5.6-terra signs are cream boards (fill RGB 244,226,177) with dark brown serif text, while all four qwen3.8-flash-next signs are dark green boards with white chalk text. |
| "hanging ... from the canopy" (q12 req 9) | A separate condition from the board's type and its text. Passes only when the sign is suspended below the canopy by a drawn cord, chain, rope or hook. A board fixed flat against the awning valance, standing on a post at counter level, screwed to the counter's front panel, or propped on the ground FAILS | "Named placement is binding" already covers positions; this makes the suspension clause checkable the same way. Only qwen3.8-flash-next v2 draws the two cords running up to the valance; the other seven mount the sign elsewhere. |
| "placed next to the apples" (q12 req 5) | Passes when the banana bunch touches the apple pile, or is the closest fruit group to it measured centre to centre. FAILS when another fruit group lies between them or is measurably closer | Turns a vague adjacency into one repeatable measurement, the way the corner-of-the-blanket rule does for q5. All 8 q12 artifacts put the bananas at the far end of the display: in gpt-5.6-terra they are the farthest of five groups from the apples (about 330 px against 150 px for the grapes), and in qwen3.8-flash-next the lemon crate and grape bowl both measure closer. |
| What counts as a "cobblestone ground surface" (q12 req 10) | Needs a packed, tiled pattern of adjacent paving stones (or their joint lines) covering the ground in front of the stall. A flat fill, soft wave bands, thin path lines, soft blurred patches, or sparse widely-spaced pebble outlines with bare ground between them all FAIL | Otherwise any ground texture at all would satisfy a requirement that names a specific paving. Sampled on every q12 render: gpt v1 flat tan plus one shadow ellipse, gpt v2 wave bands, gpt v3/animated two thin path lines, qwen base a single flat band, qwen v2/v3 soft filled ellipse patches, qwen animated scattered ellipse outlines. Eight of eight. |
| "the silhouette of another market stall in the background" (q12 req 11) | The background shape must carry the defining feature of a stall - an awning or canopy over an open front or counter. A flat, desaturated background fill counts as a silhouette in this flat-vector style, so monochrome is not required; but a plain building with a pitched or flat roof, a door and windows and no awning is not a market stall | The requirement names a stall, not scenery, and this keeps the noun binding while not punishing flat colour. It splits the q12 board: qwen3.8-flash-next v3 and animated draw a pale flat storefront under a scalloped teal/white awning (pass), while gpt-5.6-terra's tan pitched-roof houses, qwen v2's flat-roofed blue block and qwen base's empty sky all fail. |
| "front half having passed through the ring and its back half still inside the ring" (q6 req 4) | Fit the hoop's mid-band as a circle from its unoccluded arc, then split the car's body silhouette against that circle along the travel direction. Report three fractions: **through** (outside the circle, forward of its centre), **inside** (within the opening) and **behind** (outside, rearward). Passes only when behind is about 0 AND through lands between 0.30 and 0.70. FAILS when through is about 0 (nothing has emerged, whether the car is short of the hoop or sitting wholly inside it) and when through is 0.75 or more (effectively all the way out) | Turns "front half / back half" into one repeatable measurement, the way the "lower third of the duck" rule does. The q6 data does not come close to the band: gpt v1 measures through 0.87 / inside 0.13, gpt v2/v3/animated measure through 0.00 with 0.63-0.66 of the car still behind the ring, and all four qwen3.8-flash-next cars measure inside 1.00 / through 0.00. |
| What counts as "gray speed lines trailing behind the car" (q6 req 7) | Needs short parallel streaks in the air behind the moving car. A long continuous stroke that traces a structure - running from a base plate at the far edge of the canvas, along the ground, round the bend at a ramp's foot and up the incline to the wheel - is the ramp's outline or rail, not a speed line, even though it ends at the car and is grey | Parallel to the q13 "brown bands are not metal hoops" and q12 "crate is not wicker" rulings: the named thing has to be drawn, not inferred from an adjacent shape. All four gpt-5.6-terra q6 renders were traced stroke by stroke at 4x before this was applied. |
| "jagged, irregular flames" (q6 req 2), and "completely surrounded" | The flame clause passes when the tongues are pointed rather than rounded blobs and vary in length or lean around the hoop; the standard tapered vector flame tongue qualifies. "Completely surrounded" is measured as the largest angular gap between flames around the fitted circle - passes when no bare arc exceeds about 45 degrees, and an arc hidden behind the car is not counted as bare | Refusing every tapered-tongue flame would fail all eight artifacts on a purely stylistic reading and make the requirement do no work, so the checkable clause is the distribution. Measured largest gaps on the eight q6 rings run 17-34 degrees, all comfortably inside the bar. |
| "a red, **sporty** car" (q6 req 1) | "Sporty" gets no separate failing test; the binding conditions are that the car is red and that a body, wheels and windows are all drawn. Only a shape that plainly is not a car of that class (a truck, a van, a bus) would fail on it | Unlike "wicker", "claw-foot" or "chalkboard", which name a concrete construction that either is or is not drawn, "sporty" is a styling adjective with no drawable test; inventing one would be an aesthetic judgment applied unevenly. |
| "just having left the edge of the take-off ramp" (q6 req 5) | Measure from the rear wheel to the ramp's lip. Passes when the wheel sits on or within about half a wheel diameter of the lip with the car already pitched into the air; FAILS at more than that, and FAILS outright when no take-off ramp is drawn | Gives the phrase one measurement. It splits the q6 board: the three gpt-5.6-terra ramp renders put the rear tyre right on the ramp's top-right lip (pass), while all four qwen cars sit about 125 px - roughly 2.8 wheel diameters - up and away from the lip in the middle of the hoop, and gpt v1 has no ramp at all. |

## How a new call was recorded

Each pass that hit an ambiguity the table did not cover decided it, applied that
decision to every artifact in its own question, and appended a row with the
rationale. The next pass read the table before judging. No ambiguity was left
undecided, and no situation was decided two ways inside one pass. A future
rejudge that finds a gap should extend the table the same way rather than reopen
a settled row: changing a row silently rescores artifacts judged under the old
one.

The sections below are the per-pass notes — what each pass changed in the table,
and the all-fail and near-identical-variant checks it ran.

## Added after the q7 review

- When sampling colour to decide grey vs blue, the sample point must land on the
  animal's flank, not on background sky. A review sample that hit sky read 67 on
  a body that reads 33-42. Check what you sampled before trusting the number.
- The splash rule is two alternative tests, not one: a mound roughly 15% of
  canvas width at the exit point, OR visible spray arcs. Either passes. "Low
  bumps" alone fails.

## Added after the q0 review

- The requirement-8 "buried" clause was reworded above because the original row
  did not say whether debris drawn over the share counts as occlusion, and the
  q0 verdicts split both ways on it. The line is now: only the soil mass (or a
  crossing below a drawn surface line) buries the blade; detached clods drawn
  over the blade do not. The lifted-chunk clause still accepts clods.
- Re-checked against the reworded row, all four
  `opencode/qwen3.8-flash-next` cow renders fail requirement 8: the grey
  shovel-shaped share is drawn with a complete, unbroken outline on top of the
  tilled plane, the field is an oblique top-down view with no surface line for
  it to cross, and the only things over it are loose clods. Three of the four
  (base, v2, v3) had previously passed on that debris.
- `claude/claude-opus-5/cow-plowing` passes on the crossing branch, not on
  occlusion: the tan standing field meets the dark plowed strip on a drawn edge
  and the share's lower half is drawn below it. Its v2, v3 and animated pass on
  occlusion proper - a brown curled slice of earth is drawn across the
  moldboard. `claude/fable-5-1` v2, v3 and animated pass on occlusion too: a
  brown mound covers the bottom of the share.

## Added after the q5 judging

- The four `claude/claude-opus-5` picnic renders share one lineage, but they are
  not identical and were checked one at a time: the base envelope is gold/red/blue
  (req 2 fails) while v2, v3 and animated are red/white/blue (req 2 passes), and
  the distant-cloud count runs 4, 5, 6, 6 across base, v2, v3 and animated. No
  verdict was copied between variants; none of the nine renders is byte- or
  pixel-identical to another (checked with md5).
- The `-animated` renders of `gpt-5.6-terra` and `claude-opus-5` differ from their
  v3 siblings in the PNG bytes but not in any judged detail, so they land on the
  same ten verdicts by independent inspection, not by copying.

## Added after the q13 judging

- The four `claude/claude-opus-5` treasure-barrel renders share one lineage but
  none is pixel-identical to another (md5 all differ; v3 vs animated differ in
  39,906 of 480,000 pixels, spread over the whole canvas). Each was measured
  separately and they do NOT score alike: base and v2 land on 6/10, v3 and
  animated on 7/10. The splits are real - v3/animated show more than the top
  half of the barrel (req 2 fails) but do run the pearl string into a spill coin
  (req 8 passes) and do draw a goblet with a gradient (req 10 passes), while the
  base has flat unhighlighted gems and v2 has no goblet at all.
- The `gpt-5.6-terra` v3 and `-animated` renders differ in 240,394 of 960,000
  pixels (background gradient and wind streaks) but in no judged detail, so they
  land on the same ten verdicts by independent inspection, not by copying. No
  verdict was copied on this question.
- Requirement 9, the goblet partially buried in the coins **inside** the barrel,
  fails for all 9 artifacts, and the all-fail was checked object by object:
  claude base, v3 and animated draw a goblet but lie it on the open sand outside
  the barrel (sampled at 6x, bowl RGB 255,238,160 on sand); claude v2 has no
  goblet anywhere (a crown instead); all four gpt-5.6-terra renders and the
  qwen one contain no goblet-shaped object at all (qwen draws a crown). Nine of
  nine put nothing goblet-shaped inside the barrel.

## Added after the q12 judging

- The four `opencode/gpt-5.6-terra` fruit-stall renders share one lineage and all
  land on 1/11, but none is pixel-identical to another and each was inspected on
  its own. Their real differences are: v1 has no recognizable bananas (a pair of
  flat yellow blobs) while v2/v3/animated draw a proper bunch; the sign subtitle
  runs none / "PICKED THIS MORNING" / "MARKET MORNING" / "MARKET MORNING"; v3 and
  animated add a sun, ground path lines and a "LOCAL GROWERS - EVERY DAY" counter
  tagline; the canopy cream measures 247,229,170 / 251,233,186 / 249,227,162 /
  250,234,191. None of those differences touches a requirement outcome - the
  layout (3x2 wooden crate grid, oranges left, apples centre, watermelon in the
  bottom-right crate, no vendor, no cobbles, pitched-roof houses behind) is the
  same in all four, so the identical score is the drawing being the same drawing,
  not a copied verdict. v3 and animated differ in 364,090 of 1,080,000 pixels.
- No verdict was copied between variants on this question; the qwen pair does
  split (2/3/3/3, and v2 vs v3/animated pass different requirements: v2 is the
  only artifact whose sign hangs from the canopy, while v3 and animated are the
  only ones with a background market stall).
- Requirements 3, 4, 5, 6, 7, 8 and 10 fail for all 8 artifacts, and each all-fail
  was sampled for that feature specifically rather than assumed:
  - req 3: every render shows six or seven fruit kinds, counted at 2x.
  - req 4 and 6: every fruit container is a plain wooden crate, checked at 4-5x;
    on top of that gpt puts the apples in the centre and the oranges on the left,
    and qwen puts the oranges in the centre.
  - req 5: measured centre to centre in every render (see the row above).
  - req 7: no artifact rests a watermelon slice on the counter - gpt puts a dome
    in the bottom-right crate, qwen base draws three unmarked green circles at the
    foot of the counter, and qwen v2/v3/animated lay whole melons plus one round
    cross-section on the ground.
  - req 8: the four gpt renders contain no human figure at all; qwen base and v2
    contain none either; qwen v3 draws only a hat and two sleeves with the head
    hidden behind the apple pile; qwen animated draws a smiling man who is
    clean-shaven at 5x. No moustache appears anywhere on the board.
  - req 10: see the cobblestone row above - all eight grounds sampled.

## Added after the q6 judging

- q6 is the question whose `opencode/qwen3.8-flash-next/stunt-car-fire-ring*`
  half had never been scored by anyone (the slug matcher only recognised the
  gpt spelling). All four were judged from scratch here.
- No verdict was copied between variants. All eight renders differ by md5, and
  the four gpt-5.6-terra ones were inspected separately: v1 is a different
  composition entirely (1200x800, "APEX" livery, no ramps, car already out the
  far side of the hoop) and scores 3/8, while v2, v3 and animated share the
  "RUSH" ramp composition and land on 4/8. Their real differences - v3 and
  animated add two floating gantry bars and an orange stripe in the ramp's base
  plate, animated adds two detached flame petals at the upper left and a
  lighter sky - touch no requirement outcome. The four qwen renders also differ
  (base has no spoiler and plain ramps; v2 adds hazard stripes and a navy
  spoiler; v3 and animated swap the streaks for a pink spoiler and a gold
  exhaust wisp and draw spikier flames) and all land on 4/8, but requirement 7
  fails for two different reasons across them - see below.
- The two pairs tie at 4/8 on the ramp variants but pass **different**
  requirements: gpt-5.6-terra passes req 5 (rear wheel on the ramp lip) and
  fails req 3 (no landing ramp), qwen3.8-flash-next passes req 3 (both ramps,
  correct sides) and fails req 5 (car parked in the middle of the hoop).
- Requirements 4, 7 and 8 fail for all eight, and each all-fail was sampled for
  that feature specifically:
  - req 4: every hoop was fitted as a circle from its unoccluded arc (residuals
    2.9-8.2 px) and every car body split against it. Not one lands in the
    0.30-0.70 through-fraction band; see the row above for the numbers.
  - req 7: gpt v1 has no lines near the car at all (the only strokes there are
    brown background horizon curves); gpt v2/v3/animated have ramp-outline
    strokes traced at 4x from the base plate to the wheel; qwen base and v2
    have real streaks that measure tan (spread 99), and qwen v3 and animated
    have no trailing lines whatsoever.
  - req 8: the take-off lip was cropped at 4x on every render that has one.
    All are bare. gpt v1 and the four qwen renders have no spark shape anywhere
    near a ramp; the orange in v3/animated is a stripe painted in the ramp's
    base plate 600 px away, and the orange in the qwen renders is an exhaust
    wisp at the car's tail inside the hoop.

## Added after the q5 wicker re-check

The wicker row was written during the q12 pass, two passes after q5 was judged.
q5 requirement 2 - "a hot air balloon with a large envelope featuring vertical
red and white stripes and a brown wicker basket" - also names wicker, and the
six q5 failures had all been decided on the stripe clause alone, so the wicker
clause had never been tested on the three artifacts that passed. The row above
is now scoped to every requirement that names wicker, and requirement 2 was
re-examined on all nine q5 artifacts, not only the three that passed, so the
rule lands uniformly.

Method: each balloon basket was cropped from the PNG render at 6x, and the
claude wall was taken to 14x to resolve the banding. The SVG source was not
opened. Two known crates were re-cropped alongside them as the reference the
q12 pass set - `gpt-5.6-terra/fruit-stall-market-v2` and
`qwen3.8-flash-next/fruit-stall-v2` - so the same bar was applied to both
questions in one sitting.

What is drawn:

- The four `claude/claude-opus-5` picnic baskets are a tapered basket
  silhouette with a heavy rim band, a base band, and an interior lattice of
  four horizontal and four vertical darker bands forming a 5x4 grid of cells
  over a lighter panel. The two tones sample RGB 197,151,81 (panel) and
  147,102,42 (band), red-minus-blue 105-117, plainly brown. Bands in both axes
  over a contrasting fill is basket-weave banding, so **the wicker clause
  passes on all four**.
- The four `opencode/gpt-5.6-terra` balloon baskets are a flat brown trapezoid
  with a dark border and a single light cross - one horizontal band and one
  vertical band, no lattice. That is the crate pattern, so the wicker clause
  **fails** on all four.
- The `opencode/qwen3.8-27b-8bit` basket is a rounded-corner brown box carrying
  a 4x3 cross-hatch of darker lines. Lattice in both axes, so the wicker clause
  **passes**.

Outcome: no verdict changed. The three claude renders that passed requirement 2
(v2, v3, animated) draw a genuinely woven basket and keep the pass; the claude
base still fails on its gold/red/blue envelope, and the four gpt and one qwen
renders still fail on the stripe clause, which is reason enough on its own -
requirement 2 is compound, and the gpt four now fail both of its clauses.
Because nothing moved, `scores.json` was regenerated and is byte-identical, and
no published figure changed.

The q12 verdicts are untouched. Re-cropping the two reference crates confirmed
they are what the q12 pass called them: the gpt crate is a flat trapezoid with
a thin border and no interior banding at all, and the qwen crate is a rectangle
with a border and one horizontal plank line. Neither carries a lattice, so the
q5 pass and the q12 failures are the same rule applied to different drawings,
not two thresholds.

## One judge block across all 84 verdicts

Every verdict in `verdicts/` now carries the same four-key judge block - kind
`claude-vision`, model `claude-opus-5`, date 2026-09-07, and the one method
string. One file, `opencode/qwen3.8-flash-next/dolphin-hula-hoop-fish-animated`,
had carried a fifth key: `"note": "render is visually identical to the base
variant; same verdicts"`. That note described the render, not the judge, and it
was the only thing keeping the board from having a single identical judge block,
so it was moved here.

The claim it made is loose and the measurement replaces it. The animated render
is NOT identical to its v3 sibling: they differ in 152,675 of 1,920,000 pixels,
the animation frame having moved the bubble sparkles and shifted the dolphin
slightly. They differ in no judged detail - same grey body, same jaw closing on
the fish, same hand in frame, same hoop centre over the body, same splash above
the same waterline - so they land on the same seven verdicts by independent
inspection, not by copying, which is how the q5, q12, q13 and q6 notes above
already phrase the same situation. q7's v2 also lands on 7/7 and v1 on 2/7, so
this pair does split.
