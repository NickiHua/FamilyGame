#!/usr/bin/env python3
r"""
gpt_transparent_image_generation.py — GPT-Image generator for FantacyCentry HD UI assets.

Why this exists
---------------
Gemini / ChatGPT web only ever *paint* a background (magenta or checker), so we
must chroma-key it out afterwards -> fringe, colour bleed, flattened corners.
The OpenAI Image API can output a TRUE alpha channel (like PixelLab sprites):

    background="transparent"   ->   real transparent PNG, NO keying needed.

IMPORTANT model note (verified 2026-06):
    * gpt-image-1 / gpt-image-1-mini / gpt-image-1.5  ->  support transparent bg
    * gpt-image-2 (newest)                            ->  does NOT support it
We default to model="gpt-image-1.5" (transparent-capable, cheaper AND better
than gpt-image-1: e.g. high 1024x1024 = $0.133 vs $0.167).

Auth
----
The API key is read (in priority order) from:
    1. --key-file <path>           (default: openaikey.txt at repo root)
    2. OPENAI_API_KEY env variable
openaikey.txt is gitignored. NEVER commit a key.

Usage (CWD = FamilyGame/)
-------------------------
    # one of the built-in presets (transparent bg, no keying)
    .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py panel
    .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py banner-blue
    .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py banner-red
    .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py button

    # use an existing image as a STYLE REFERENCE / init (edits endpoint)
    .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py banner-blue ^
        --ref Assets/Art/UI/hd/panel_info_frame.png

    # free-form prompt (custom REQUIRES --type for the output folder)
    .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py custom ^
        --type icon --prompt "..." --size 1024x1024

Portraits (立绘 / bust / concept — see docs/pipelines/portrait-asset-pipeline.md)
--------------------------------------------------------------------------------
    # ① concept sheet — OPAQUE neutral bg anchor (full body + 5 expression busts)
    .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py suyao-concept

    # ② full-body 立绘 — TRANSPARENT alpha, uses the concept as style/identity ref
    .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py suyao-full ^
        --ref art/portraits/suyao/concept.png

    # ③ expression bust — TRANSPARENT, generic preset; identity from --ref
    .\.venv\Scripts\python.exe scripts\gpt_transparent_image_generation.py portrait-bust ^
        --ref art/portraits/suyao/concept.png --type suyao --expression happy

Portrait outputs land in art_undecided/portraits/<character>/. Concept presets use
--background opaque; full/bust use --background transparent (the API PARAMETER —
never write "transparent background" into a portrait prompt, it wrecks the face).

Outputs default to:  art_undecided/ui/<type>/<preset>_<timestamp>_<i>.png
where <type> is the UI component folder (panel / banner / button / icon / ...),
inferred from the preset or set with --type. That top-level art_undecided/ folder
holds RAW output awaiting review; after you approve, the keeper moves to
art/ui/<type>/ (master) and a copy goes to Assets/Art/UI/<plural>/ for Unity.
See docs/pipelines/ui-asset-pipeline.md.
"""
from __future__ import annotations

import argparse
import base64
import datetime as _dt
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Prompts — TRANSPARENT-background variants (no magenta, no checker, real alpha)
# Adapted from docs/prompts/ui-prompts.md §8.2 / §8.3 / §8.4.
# ---------------------------------------------------------------------------
_COMMON_TAIL = (
    "High-resolution SMOOTH digital painting, clean anti-aliased vector-like "
    "rendering, crisp smooth gradients. Flat even lighting, NO 3D plastic gloss, "
    "NO heavy drop shadow, NOT pixel art, no jagged or chunky pixels. "
    "NO text, NO letters, NO numbers, NO icons, NO characters, NO portrait, "
    "no watermark, no signature. "
    "The background MUST be fully transparent — render ONLY the UI shape itself "
    "on a transparent background, nothing else, no backdrop, no plate behind it."
)

# Variant for action-icon buttons: the simple action GLYPH inside each frame IS
# wanted, so we must NOT forbid icons here (only forbid text / letters / numbers).
_ICON_TAIL = (
    "High-resolution SMOOTH digital painting, clean anti-aliased vector-like "
    "rendering, crisp smooth gradients. Flat even lighting, NO 3D plastic gloss, "
    "NO heavy drop shadow, NOT pixel art, no jagged or chunky pixels. "
    "NO text, NO letters, NO numbers, no watermark, no signature. "
    "The background MUST be fully transparent — render ONLY the icon buttons "
    "themselves on a transparent background, nothing else, no backdrop, no plate "
    "behind them, transparent gaps between the separate buttons."
)

# ---------------------------------------------------------------------------
# PORTRAIT prompts (character 立绘 / bust / concept sheet).
# See docs/prompts/portrait-prompts.md + docs/pipelines/portrait-asset-pipeline.md.
# IMPORTANT: NEVER write "transparent background" into a portrait prompt — that
# wrecks the face. Transparency is set via the `background` API PARAMETER only.
# The Image API does NOT rewrite prompts, so these are written in ENGLISH.
# ---------------------------------------------------------------------------
_PORTRAIT_STYLE = (
    "Classic modern Japanese SRPG / commercial JRPG character-art style: clean and "
    "refined, smooth natural lineart, soft cel-shading with a light painterly touch, "
    "soft unified lighting, vivid but not oversaturated colours. Slender natural body "
    "proportions, tasteful Japanese-anime facial aesthetics, an elegant yet practical "
    "fantasy costume that is restrained (not over-decorated, not gaudy). Strong class "
    "identity and character identity, cohesive with a single unified party art "
    "direction so every character reads as one commercial JRPG cast. High-quality, "
    "commercial-grade illustration. NO text, NO labels, NO logo, NO watermark, NO "
    "signature, NO border, NO UI elements."
)

# Concept reference sheet layout: full body on the RIGHT, 5 expression busts on the
# LEFT column. Opaque neutral background — the concept is a style/identity ANCHOR,
# not a game asset, so it does NOT need alpha.
_PORTRAIT_CONCEPT_LAYOUT = (
    "A high-quality character design reference sheet for an original, commercial "
    "Japanese tactical RPG (SRPG). FIXED LAYOUT: on the RIGHT, ONE complete full-body "
    "character portrait — the ENTIRE figure from the very top of the head down to the "
    "feet must be FULLY inside the frame, standing upright in a dignified natural "
    "pose, drawn SMALL enough that there is clear empty margin ABOVE the head and "
    "BELOW the feet; absolutely nothing cropped (do not let the head, hair, held staff "
    "or feet touch or run off any edge). On the LEFT, a single vertical column of FIVE "
    "face / bust expression headshots of the SAME character, evenly stacked top to "
    "bottom in this order: neutral, happy, sad, angry, puzzled. Plain flat neutral "
    "light-grey studio background. "
    # Hard camera / framing constraint (gpt-image tends to crop heads at 1:1) —
    # obey over aesthetics; empty padding on all sides; zoom out if it doesn't fit.
    "FRAMING CONSTRAINT (obey strictly, framing priority over aesthetics): frame as a "
    "full-body long shot; the entire head, hair, both feet and every expression "
    "headshot must sit fully inside the canvas with clear empty padding above and "
    "below; NO cinematic or fashion crop; if anything does not fit, ZOOM THE CAMERA "
    "OUT until it fully fits. "
)

# Per-character description blocks (append to layout / full / bust as needed).
# Structured CHARACTER CARD — locks the identity/style traits that must stay
# consistent across concept / 立绘 / busts. Skin tone omitted on purpose (western
# fantasy JRPG default = fair). Locked from the approved medium concept.
_SUYAO = (
    "CHARACTER — Su Yao, the party's priest / holy healer (gentle magic support). "
    "AGE / GENDER: an 18-year-old girl. "
    "BUILD: slender and youthful, about 6.5 heads tall — NOT chibi, NOT a tall adult. "
    "HAIR: long straight silver hair flowing past the waist, centre-parted with soft "
    "bangs framing the face. "
    "EYES: clear blue. "
    "FACE: delicate gentle features with a calm, warm, kindly, trustworthy expression. "
    "OUTFIT (white-and-gold priestess): a floor-length long-sleeved white robe / dress "
    "with gold hem trim and a decorative gold front panel, cinched by a gold waist "
    "sash; a short white shoulder cape edged with fine gold scrollwork, fastened at "
    "the throat with a small gem clasp; the head is bare (NO hood, NO veil) so the "
    "silver hair shows fully; white-and-gold slippers. "
    "PALETTE: white + pale gold, silver hair, a single blue gem accent — restrained, "
    "holy, lightweight. "
    "SIGNATURE STAFF: one elegant holy staff — a slender silver shaft topped with an "
    "ornate gold head that holds a faceted blue teardrop crystal flanked by a pair of "
    "small white angel wings; a healing / sacred implement, NOT an aggressive weapon. "
    "CLASS READ: unmistakably a priest / healer — holy robe + staff, carries no weapon; "
    "dignified, calm, non-aggressive posture. "
    "DETAIL: keep the whole design CLEAN and RESTRAINED — flat cel-shading, controlled "
    "gold trim, NO busy over-detailing, no cluttered ornament, no heavy painterly "
    "noise. "
)

_LINGSHUANG = (
    "CHARACTER — Ling Shuang, the party's front-line lancer / spear knight. "
    "AGE / GENDER: a 25-year-old woman. "
    "BUILD: tall, mature and athletic, about 7 heads tall — a poised adult warrior, "
    "clearly taller and more grown-up than the young priest, NOT chibi. "
    "HAIR: long pink hair worn in a high PONYTAIL tied with a large white bow, soft "
    "bangs framing the face; the ponytail is long and flowing, kept as a CLEAN, "
    "COHESIVE shape with smooth strands — avoid lots of messy, scattered flyaway "
    "strands. "
    "EYES: clear blue. "
    "FACE: beautiful, mature features with a confident, determined, spirited and "
    "gallant expression; reliable and dignified. "
    "OUTFIT (light fantasy knight): sleek, elegant, finely-crafted LIGHT PLATE knight "
    "armour — mainly white and silver with subtle pink accents — refined with delicate "
    "engraved trim, classic Japanese-fantasy, practical and NOT revealing; well-shaped "
    "cuirass, pauldrons, gauntlets and greaves over a fitted underlayer. NO cape, NO "
    "cloak. "
    "PALETTE: white + silver armour, pink hair with pink accents — clean and knightly. "
    "SIGNATURE WEAPON: one long, slender, elegant SPEAR / lance with a refined silver "
    "blade, held upright; natural realistic weapon proportions befitting an elite "
    "lancer (a real spear, not oversized). "
    "CLASS READ: unmistakably a front-line spear knight — light armour + long spear, "
    "standing upright in a confident, disciplined yet elegant stance. "
    "DETAIL: keep the design CLEAN and COHESIVE — flat cel-shading; refined, tasteful "
    "armour detailing is welcome but no chaotic clutter and no heavy painterly noise. "
)

_LULI = (
    "CHARACTER — Lu Li, the party's protagonist swordsman. "
    "AGE / GENDER: a 20-year-old young man. "
    "BUILD: slender, athletic and fit, tall, about 7.5 heads. "
    "HAIR: short brown hair, tidy with natural bangs. "
    "EYES: clear blue. "
    "FACE: handsome youthful features with a bright, confident, genuine look and an "
    "easy natural smile. "
    "OUTFIT: white LIGHT knight armour with a DEEP BLUE cape; refined and practical, "
    "flexible yet protective, classic Japanese-fantasy, NOT over-complex and NOT "
    "gaudy; clean and crisp. "
    "PALETTE: white + silver armour, a deep blue cape, brown hair — clean and knightly. "
    "SIGNATURE WEAPON: an elegant LONG SWORD worn at the waist in a simple refined "
    "scabbard with a clean guard; natural proportions befitting a young kingdom "
    "swordsman. "
    "CLASS READ: unmistakably a melee swordsman — light armour + sheathed long sword, "
    "standing upright in a confident, relaxed stance, one hand resting naturally near "
    "the sword hilt. "
    "DETAIL: keep the design CLEAN and RESTRAINED — flat cel-shading, NO busy "
    "over-detailing, no heavy painterly noise. "
)

# COMBINED sheet: full body (right) + FOUR waist-up busts (left column) in ONE
# generation → 立绘 and busts share the EXACT SAME clothing (fixes cross-image drift).
# {e1}..{e4} filled from --busts. Cut afterwards: right = 立绘, left column split 4.
_PORTRAIT_SHEET_4 = (
    "A high-quality character design sheet for an original, commercial Japanese "
    "tactical RPG (SRPG), on a plain flat neutral light-grey studio background. "
    "FIXED LAYOUT: on the RIGHT, ONE complete FULL-BODY portrait of the character, "
    "standing upright in a dignified natural pose. On the LEFT, a single vertical "
    "column of FOUR WAIST-UP bust portraits of the SAME character, evenly stacked top "
    "to bottom in this order: {e1}; {e2}; {e3}; {e4}. "
    "CRITICAL CONSISTENCY: the full body and ALL FOUR busts wear the EXACT SAME "
    "clothing / armour, the same hairstyle and the same colours — identical in every "
    "way; the ONLY difference between the busts is each one's FACIAL EXPRESSION. "
    "FRAMING (obey strictly): the full-body figure's entire head, hair, weapon and "
    "BOTH feet, and every bust's whole head and hair, must sit fully inside the canvas "
    "with clear empty padding on all sides; NOTHING cropped; if anything does not fit, "
    "ZOOM OUT until it fully fits. "
)

# ONE-bust variant (right full body + left ONE neutral bust). For enemy mooks that
# only need 立绘 + a single portrait.
_PORTRAIT_SHEET_1 = (
    "A high-quality character design sheet for an original, commercial Japanese "
    "tactical RPG (SRPG), on a plain flat neutral light-grey studio background. "
    "FIXED LAYOUT: on the RIGHT, ONE complete FULL-BODY portrait of the character, "
    "standing upright in a natural pose. On the LEFT, ONE single WAIST-UP bust portrait "
    "of the SAME character with a neutral expression. "
    "CRITICAL CONSISTENCY: the full body and the bust wear the EXACT SAME clothing / "
    "armour and colours, identical in every way. "
    "FRAMING (obey strictly): the full-body figure's entire head, helmet, weapon and "
    "BOTH feet, and the bust's whole head, must sit fully inside the canvas with clear "
    "empty padding on all sides; NOTHING cropped; if anything does not fit, ZOOM OUT "
    "until it fully fits. "
)

# --- Enemy character cards (imperial teal-green palette; mooks = cold small eyes,
# captain = closed visor, faceless) ---------------------------------------------
_EMPIRE_ARCHER = (
    "CHARACTER — a generic Empire foot archer: a faceless rank-and-file enemy mook, "
    "NOT a named hero. "
    "AGE / GENDER / BUILD: a lean, wiry man in his 20s, ordinary soldier build, about "
    "7 heads. "
    "FACE / EYES: small, narrow, dull, mean eyes — a coarse, common, unremarkable "
    "soldier face; low-brow and slightly brutish, NOT noble, NOT heroic, NOT the big "
    "righteous eyes of the heroes. "
    "OUTFIT (imperial): an open-faced steel nasal / kettle-hat helmet topped with a "
    "short dark-green feather PLUME / crest on top; a dark TEAL-GREEN tabard over brown "
    "leather and chainmail light armour; "
    "brass and leather trim; a bracer on the left forearm. "
    "PALETTE: dark teal-green + steel grey + brown leather + brass — drab imperial "
    "military colours, NOT the bright white/gold of the heroes. "
    "SIGNATURE WEAPON: a recurved wooden longbow with brass-bound limbs held in hand, "
    "and a brown leather quiver of arrows on the back. "
    "CLASS READ: a plain imperial foot archer. "
    "DETAIL: CLEAN and RESTRAINED, flat cel-shading; grim, plain, anonymous. "
)

_EMPIRE_AXE = (
    "CHARACTER — a generic Empire axe infantryman: a faceless rank-and-file enemy "
    "mook, NOT a named hero. "
    "AGE / GENDER / BUILD: a burly, broad, gruff man, heavy soldier build, about "
    "6.5-7 heads. "
    "FACE / EYES: cold, small, narrow, hard eyes — grim and mean, deliberately NOT big "
    "hero eyes; a thick beard and a hard scowling mouth; a plain anonymous soldier "
    "face. "
    "OUTFIT (imperial): a steel helmet with small angular side ornaments; a dark "
    "TEAL-GREEN tabard over steel and chainmail armour; brass trim and brown leather "
    "straps. "
    "PALETTE: dark teal-green + steel + brass + brown leather. "
    "SIGNATURE WEAPON: a one-handed steel battle axe in one hand, and a round wooden "
    "shield with a steel boss on the other arm. "
    "CLASS READ: a plain imperial axe infantry soldier. "
    "DETAIL: CLEAN and RESTRAINED, flat cel-shading; grim, plain, anonymous. "
)

_EMPIRE_CAPTAIN = (
    "CHARACTER — an Empire Captain: an elite enemy officer / mini-boss, imposing and "
    "more ornate than the rank-and-file, a grim antagonist. "
    "AGE / GENDER / BUILD: a tall, imposing armoured man with a commanding presence, "
    "about 7.5 heads. "
    "FACE: he wears a CLOSED VISORED steel helm — the face is FULLY hidden behind the "
    "visor, an intimidating faceless elite (only a dark narrow eye-slit, no visible "
    "eyes or skin). "
    "OUTFIT (imperial elite): heavier, finer SILVER full plate armour with dark "
    "TEAL-GREEN and brass trim and a captain's insignia; a dark green cape / cloak from "
    "the shoulders; clearly more ornate than the common soldiers. "
    "PALETTE: silver steel + dark teal-green + brass + a dark green cape. "
    "SIGNATURE WEAPON: an elegant steel longsword in one hand and a heater / kite "
    "shield bearing the imperial emblem on the other arm. "
    "CLASS READ: an armoured imperial captain / knight-officer, a cut above the mooks. "
    "DETAIL: refined but grim; imposing, disciplined, sinister authority; flat "
    "cel-shading, no clutter. "
)

# Full-body 立绘 scaffold (character identity comes from the --ref concept image).
_PORTRAIT_FULL = (
    "Using the attached image as the exact character and style reference, generate ONE "
    "single COMPLETE FULL-BODY character portrait (tachie / 立绘) of the SAME character "
    "— full length from head to toe, both feet fully visible, standing upright in an "
    "elegant natural pose, the whole figure centred with generous empty margin on all "
    "four sides and nothing cropped or touching any edge. Keep the IDENTICAL face, "
    "hairstyle, hair colour, costume, colours and props (including the staff) as the "
    "reference character. "
    "FRAMING CONSTRAINT (obey strictly, framing priority over aesthetics): frame as a "
    "full-body long shot; the entire head, hair, held staff and both feet must sit "
    "fully inside the canvas with clear empty padding above the head and below the "
    "feet; NO cinematic or fashion crop; if anything does not fit, ZOOM THE CAMERA OUT "
    "until it fully fits. "
)

# Half-body bust scaffold — character-agnostic (identity from --ref), reusable for
# the whole cast. {expression} is filled from --expression.
_PORTRAIT_BUST = (
    "Using the attached image as the exact character and style reference, generate ONE "
    "single half-body bust portrait (head and chest, facing the viewer) of the SAME "
    "character showing a clear, distinct {expression} facial expression. Keep the "
    "IDENTICAL face, hairstyle, hair colour, costume and colours as the reference "
    "character. Frame the bust centred with the ENTIRE head and hair fully inside the "
    "canvas and clear empty space above the head — never crop the top of the head or "
    "hair; nothing cropped. "
)

# 2x2 bust SHEET (4 expressions in ONE generation → guaranteed consistent
# clothing/hair/position, unlike 4 separate calls which drift). Feed the approved
# 立绘 as --ref so the clothing matches the FINAL outfit (concept outfit differs).
_PORTRAIT_BUSTS_2X2 = (
    "Using the attached image as the EXACT reference for the character AND the "
    "clothing, generate a clean 2x2 GRID (four equal cells, evenly spaced) of FOUR "
    "half-body bust portraits of the SAME character — waist-up, facing the viewer. "
    "CRITICAL CONSISTENCY: all four busts must be IDENTICAL in face shape, hairstyle, "
    "hair, outfit / clothing, colours, body, angle, size and framing — copy the "
    "clothing from the reference EXACTLY. The ONLY thing that may differ between the "
    "four cells is the FACIAL EXPRESSION. Do NOT change the clothing, hair, pose, size "
    "or position between cells. "
    "Expressions in reading order: TOP-LEFT = {e1}; TOP-RIGHT = {e2}; BOTTOM-LEFT = "
    "{e3}; BOTTOM-RIGHT = {e4}. Each expression must be clear and distinct. Waist-up "
    "only; in every cell the whole head and hair sit fully inside the "
    "cell with clear space above the head; nothing cropped. "
)

# Maps a preset to its output subfolder. UI presets -> art_undecided/ui/<type>/;
# portrait presets (category="portrait") -> art_undecided/portraits/<type>/.
PRESET_TYPE: dict[str, str] = {
    "panel": "panel",
    "banner-blue": "banner",
    "banner-red": "banner",
    "button": "button",
    "select-frame": "range",
    "action-icons": "icon",
    # portraits (subfolder = character id)
    "suyao-concept": "suyao",
    "suyao-full": "suyao",
    "lingshuang-concept": "lingshuang",
    "lingshuang-full": "lingshuang",
    "luli-sheet": "luli",
    "suyao-sheet": "suyao",
    "lingshuang-sheet": "lingshuang",
    "empirearcher-sheet": "empirearcher",
    "empireaxe-sheet": "empireaxe",
    "empirecaptain-sheet": "empirecaptain",
    "portrait-bust": "portrait",  # generic; pass --type <char> to route per character
    "portrait-busts": "portrait",  # 2x2 four-expression sheet; pass --type <char>
}

PRESETS: dict[str, dict] = {
    # ① panel anchor — defines the gold style. 9-slice friendly, ~4:1.
    # 2026-06-22: thin gold + small corner flourishes + SOLID navy centre (not hollow).
    # Best run with --ref art/ui/button/button_normal_long.png as the style anchor.
    "panel": dict(
        size="1536x1024",
        prompt=(
            "Using the attached image as the exact style reference for the gold "
            "border (same THIN delicate gold line, same SMALL simple corner "
            "flourishes — do NOT make the gold thicker or more ornate), generate ONE "
            "single wide horizontal UI panel frame for a Japanese fantasy tactical "
            "RPG, isolated and centered, and NOTHING ELSE, roughly 4:1 (wide) aspect "
            "with rounded corners. The interior is a SOLID, FLAT, EVENLY filled deep "
            "NAVY-BLUE (completely opaque, NOT hollow, NOT transparent, NOT a window). "
            "The thin gold border runs cleanly around all four sides with ONE small "
            "simple gold flourish at each of the four corners, minimal and "
            "understated. The four straight edges are plain thin gold lines so it can "
            "be 9-sliced (corners fixed, navy center and edges stretch). The wide "
            "middle is plain flat navy with NO ornament, so engine text sits on top. "
            "Lightweight and clean — the gold must NOT dominate. " + _COMMON_TAIL
        ),
    ),
    # ② phase banner — solid navy bar, simple gold end-caps, ~3:1 (API max ratio).
    "banner-blue": dict(
        size="1536x1024",
        prompt=(
            "Generate ONE long horizontal ornamental phase BANNER for a Japanese "
            "fantasy tactical RPG and NOTHING ELSE, a very wide thin horizontal bar "
            "(about 3:1, as wide and short as allowed), isolated and centered. The "
            "whole banner is a SOLID filled deep NAVY-BLUE horizontal bar (the center "
            "is SOLID navy, completely filled, NOT hollow, NOT a window). On the far "
            "left and far right place a SMALL, SIMPLE, restrained gold corner accent "
            "each — just a single thin elegant gold flourish, MINIMAL scrollwork, NOT "
            "a big ornate baroque block, NOT busy, NOT dense filigree. A thin clean "
            "gold pinstripe runs along the top and bottom edges of the whole bar. The "
            "wide middle is plain, flat, even solid navy with NO ornament, so engine "
            "text can sit on top of it. Refined, elegant, mostly empty, understated. "
            + _COMMON_TAIL
        ),
    ),
    "banner-red": dict(
        size="1536x1024",
        prompt=(
            "Generate ONE long horizontal ornamental phase BANNER for a Japanese "
            "fantasy tactical RPG and NOTHING ELSE, a very wide thin horizontal bar "
            "(about 3:1, as wide and short as allowed), isolated and centered. The "
            "whole banner is a SOLID filled deep CRIMSON-RED horizontal bar (the "
            "center is SOLID red, completely filled, NOT hollow, NOT a window). On the "
            "far left and far right place a SMALL, SIMPLE, restrained gold corner "
            "accent each — just a single thin elegant gold flourish, MINIMAL "
            "scrollwork, NOT a big ornate baroque block, NOT busy, NOT dense filigree. "
            "A thin clean gold pinstripe runs along the top and bottom edges of the "
            "whole bar. The wide middle is plain, flat, even solid red with NO "
            "ornament, so engine text can sit on top of it. Refined, elegant, mostly "
            "empty, understated. " + _COMMON_TAIL
        ),
    ),
    # ③ command button frames — 3 states in a row, PLAIN gold edge only.
    # 2026-06-22: stripped of corner accents — a clean rounded gold-edged navy
    # button, hollow centre (engine draws label/icon on top). Reused for the
    # character command menu rows and the END TURN button.
    "button": dict(
        size="1536x1024",
        prompt=(
            "Generate THREE horizontal command BUTTON frames for a Japanese fantasy "
            "tactical RPG, arranged in a single row side by side, and NOTHING ELSE. "
            "Each is a compact wide rounded rectangle (about 3:1) with generously "
            "ROUNDED, soft corners and a deep translucent navy-blue interior, framed "
            "by ONE single smooth gold edge with a gently ROUNDED, slightly raised "
            "bevel that follows the rounded rectangle all the way around — soft and "
            "rounded, not a razor-thin sharp line, but still simple: absolutely NO "
            "corner flourish, NO scrollwork, NO ornament, NO accent, NO gems, just a "
            "clean smooth rounded gold rim. Hollow empty center so engine icons and "
            "text sit on top. The three differ ONLY in state: left = NORMAL (calm "
            "navy + gold), middle = HOVER (slightly brighter, subtle gold glow), "
            "right = PRESSED (slightly darker / inset). Identical shape and size "
            "across all three. NO text, NO icons inside. Do NOT draw panels, bars, or "
            "a kit — only the three plain rounded gold-edged button frames. "
            + _COMMON_TAIL
        ),
    ),
    # ④ select / cursor frame — gold corner brackets, hollow transparent centre,
    # sized to overlay a single battle-map cell. HD replacement for the old pixel
    # art/ui/range/select_frame.png. Run WITH --ref art/ui/range/select_frame.png.
    "select-frame": dict(
        size="1024x1024",
        prompt=(
            "Using the attached image as the exact style/layout reference, generate "
            "ONE square selected-tile CURSOR FRAME for a Japanese fantasy tactical "
            "RPG, isolated and centered, and NOTHING ELSE. It is made of FOUR gold "
            "corner BRACKETS (one in each corner) joined by thin gold edges, in the "
            "same refined navy-and-gold style as the reference, with elegant small "
            "gold corner scrollwork. The ENTIRE CENTER is COMPLETELY HOLLOW and "
            "fully TRANSPARENT — an empty window, NO fill, NO navy, NO glass, so the "
            "battle map shows straight through it. Only the thin gold bracket border "
            "ring is drawn. Square, sized to overlay a single map cell. " + _COMMON_TAIL
        ),
    ),
    # ⑤ action icon buttons — SEVEN small square HD gold-framed buttons in TWO
    # rows (4 on top, 3 on bottom), smooth (NOT pixel art), matching the
    # panel/button gold family. Navy fill, each with its action glyph baked in.
    # Glyph order: attack / skill / magic / item / wait / defend / move.
    # Run WITH --ref art_undecided/ui/icon_ref_transparent.png (icon CONTENT only;
    # render in smooth HD gold style, NOT the reference's pixel-art look).
    "action-icons": dict(
        size="1024x1024",
        prompt=(
            "Generate SEVEN small SQUARE command icon BUTTONS for a Japanese fantasy "
            "tactical RPG, laid out in a TIDY GRID of TWO ROWS — FOUR buttons in the "
            "top row and THREE buttons in the bottom row — evenly spaced, and NOTHING "
            "ELSE. The attached image shows the action concepts for reference ONLY — "
            "match what each icon DEPICTS, but DO NOT copy its pixel-art style; "
            "instead render everything SMOOTH and high-resolution with refined gold "
            "filigree, the same elegant navy-and-gold look as a matching UI panel. "
            "Every button is identical in size and frame: a small rounded-corner "
            "square with a thin refined SMOOTH gold border and a SMALL tasteful gold "
            "corner flourish at each corner, filled with a SOLID deep navy-blue "
            "interior (NOT hollow, NOT transparent inside). Centered on each navy face "
            "is ONE clear, bold, smooth golden action symbol. Top row left-to-right: "
            "(1) a SWORD for attack, (2) a four-point SPARKLE / star burst for skill, "
            "(3) a wizard STAFF topped with a glowing magic orb for magic, (4) a "
            "round POTION bottle for item. Bottom row left-to-right: (5) an HOURGLASS "
            "for wait, (6) a SHIELD for defend, (7) a BOOT for move. All SEVEN buttons "
            "must be FULLY INSIDE the canvas with clear even margins on every side — "
            "none touching, overlapping or cropped by any edge. Identical frame on "
            "all seven; only the inner symbol differs. Do NOT draw panels, bars, big "
            "buttons or a kit — only the seven small icon buttons in a two-row grid. "
            + _ICON_TAIL
        ),
    ),
    # -----------------------------------------------------------------------
    # PORTRAITS. category="portrait" -> output art_undecided/portraits/<type>/.
    # Concept = OPAQUE neutral bg (anchor only). Full/bust = TRANSPARENT param.
    # -----------------------------------------------------------------------
    # 苏瑶 SuYao concept sheet: full body right + 5 expression busts left.
    "suyao-concept": dict(
        size="1024x1024",
        category="portrait",
        background="opaque",
        prompt=(_PORTRAIT_CONCEPT_LAYOUT + _SUYAO + _PORTRAIT_STYLE),
    ),
    # 苏瑶 full-body 立绘 (run WITH --ref art/portraits/suyao/concept.png).
    # OPAQUE: transparent degrades quality + punches holes in the white robe (A/B
    # verified 2026-07-04). Cut to transparent afterwards with rembg isnet-anime.
    "suyao-full": dict(
        size="1024x1536",
        category="portrait",
        background="opaque",
        prompt=(_PORTRAIT_FULL + _SUYAO + _PORTRAIT_STYLE),
    ),
    # LingShuang concept sheet (landscape: 5 busts left + full body right).
    "lingshuang-concept": dict(
        size="1536x1024",
        category="portrait",
        background="opaque",
        prompt=(_PORTRAIT_CONCEPT_LAYOUT + _LINGSHUANG + _PORTRAIT_STYLE),
    ),
    # LingShuang full-body 立绘 (run WITH --ref concept). OPAQUE → rembg after.
    "lingshuang-full": dict(
        size="1024x1536",
        category="portrait",
        background="opaque",
        prompt=(_PORTRAIT_FULL + _LINGSHUANG + _PORTRAIT_STYLE),
    ),
    # LuLi COMBINED sheet: full body + 4 busts in ONE image (consistent clothing).
    # Set the 4 expressions with --busts. OPAQUE → cut afterwards.
    "luli-sheet": dict(
        size="1536x1024",
        category="portrait",
        background="opaque",
        prompt=(_PORTRAIT_SHEET_4 + _LULI + _PORTRAIT_STYLE),
    ),
    # SuYao / LingShuang combined sheets (same unified layout as luli-sheet).
    "suyao-sheet": dict(
        size="1536x1024",
        category="portrait",
        background="opaque",
        prompt=(_PORTRAIT_SHEET_4 + _SUYAO + _PORTRAIT_STYLE),
    ),
    "lingshuang-sheet": dict(
        size="1536x1024",
        category="portrait",
        background="opaque",
        prompt=(_PORTRAIT_SHEET_4 + _LINGSHUANG + _PORTRAIT_STYLE),
    ),
    # Enemy sheets: right full body + left ONE neutral bust (_PORTRAIT_SHEET_1).
    "empirearcher-sheet": dict(
        size="1536x1024",
        category="portrait",
        background="opaque",
        prompt=(_PORTRAIT_SHEET_1 + _EMPIRE_ARCHER + _PORTRAIT_STYLE),
    ),
    "empireaxe-sheet": dict(
        size="1536x1024",
        category="portrait",
        background="opaque",
        prompt=(_PORTRAIT_SHEET_1 + _EMPIRE_AXE + _PORTRAIT_STYLE),
    ),
    "empirecaptain-sheet": dict(
        size="1536x1024",
        category="portrait",
        background="opaque",
        prompt=(_PORTRAIT_SHEET_1 + _EMPIRE_CAPTAIN + _PORTRAIT_STYLE),
    ),
    # Generic expression bust (character identity from --ref concept). Fill the
    # expression with --expression; route per character with --type <char>.
    "portrait-bust": dict(
        size="1024x1024",
        category="portrait",
        background="transparent",
        prompt=(_PORTRAIT_BUST + _PORTRAIT_STYLE),
    ),
    # 2x2 four-expression bust sheet (ONE generation = consistent clothing/hair).
    # OPAQUE (transparent degrades quality + punches holes in white robes); slice +
    # rembg-cut locally after. TALL 1024x1536 gives headroom (1:1 crops heads). Feed
    # the approved 立绘 as --ref. Route with --type <char>.
    "portrait-busts": dict(
        size="1024x1536",
        category="portrait",
        background="opaque",
        prompt=(_PORTRAIT_BUSTS_2X2 + _PORTRAIT_STYLE),
    ),
}


def _load_key(key_file: Path | None) -> str:
    if key_file and key_file.is_file():
        key = key_file.read_text(encoding="utf-8").strip()
        if key:
            return key
    env = os.environ.get("OPENAI_API_KEY", "").strip()
    if env:
        return env
    sys.exit(
        "ERROR: no API key. Put it in openaikey.txt (repo root) or set "
        "OPENAI_API_KEY. (openaikey.txt is gitignored.)"
    )


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent

    ap = argparse.ArgumentParser(description="Generate HD UI assets via GPT-Image.")
    ap.add_argument(
        "preset",
        choices=list(PRESETS) + ["custom"],
        help="Which prompt preset to use, or 'custom' with --prompt.",
    )
    ap.add_argument("--prompt", help="Free-form prompt (required for 'custom').")
    ap.add_argument(
        "--ref",
        action="append",
        default=[],
        help="Reference / init image path (repeatable). Uses the edits endpoint.",
    )
    ap.add_argument("--out", help="Output PNG path. Default: auto-named under art_undecided/ui/<type>/.")
    ap.add_argument(
        "--type",
        help="UI component type = the art_undecided/ui/<type>/ output folder "
             "(panel, banner, button, icon, bar, nameplate). Defaults from the "
             "preset; REQUIRED for 'custom'.",
    )
    ap.add_argument("--model", default="gpt-image-1.5", help="Default gpt-image-1.5 (supports transparent bg, cheaper+better than gpt-image-1).")
    ap.add_argument(
        "--size",
        help="WxH, e.g. 1536x1024. Default depends on preset.",
    )
    ap.add_argument(
        "--quality",
        default="high",
        choices=["low", "medium", "high", "auto"],
    )
    ap.add_argument(
        "--background",
        default=None,
        choices=["transparent", "opaque", "auto"],
        help="transparent = true alpha PNG (立绘/bust); opaque = solid bg (concept). "
             "Default: from the preset, else transparent.",
    )
    ap.add_argument(
        "--expression",
        default="neutral",
        help="Facial expression for portrait-bust (neutral/happy/sad/angry/puzzled "
             "or a short phrase). Fills {expression} in bust prompts.",
    )
    ap.add_argument(
        "--busts",
        default="calm neutral|happy with a bright smile|sad and sorrowful|"
                "angry, frowning and stern",
        help="Four expressions for the portrait-busts 2x2 sheet, separated by '|' "
             "in reading order TL|TR|BL|BR.",
    )
    ap.add_argument(
        "--category",
        choices=["ui", "portrait"],
        help="Output tree: ui -> art_undecided/ui/<type>/, portrait -> "
             "art_undecided/portraits/<type>/. Default: from preset, else ui.",
    )
    ap.add_argument("--n", type=int, default=1, help="How many images.")
    ap.add_argument(
        "--key-file",
        default=str(repo_root / "openaikey.txt"),
        help="Path to a file containing the API key.",
    )
    args = ap.parse_args()

    # resolve prompt + size
    if args.preset == "custom":
        if not args.prompt:
            sys.exit("ERROR: 'custom' requires --prompt.")
        prompt = args.prompt
        size = args.size or "1024x1024"
        cfg = {}
    else:
        cfg = PRESETS[args.preset]
        prompt = args.prompt or cfg["prompt"]
        size = args.size or cfg["size"]

    # fill {expression} placeholder (portrait-bust); harmless if absent
    prompt = prompt.replace("{expression}", args.expression)

    # fill 2x2 bust expressions {e1}..{e4} (portrait-busts); harmless if absent
    if "{e1}" in prompt:
        parts = [p.strip() for p in args.busts.split("|")]
        if len(parts) != 4:
            sys.exit("ERROR: --busts needs 4 expressions separated by '|'.")
        for i, p in enumerate(parts, 1):
            prompt = prompt.replace("{e%d}" % i, p)

    # resolve background: CLI overrides preset, preset overrides transparent default
    background = args.background or cfg.get("background") or "transparent"

    # resolve output category + subfolder
    category = args.category or cfg.get("category") or "ui"
    ui_type = args.type or PRESET_TYPE.get(args.preset)
    if not ui_type:
        sys.exit(
            "ERROR: cannot infer output folder. Pass --type <panel|banner|button|"
            "icon|bar|nameplate for UI, or a character id for portraits> "
            "(required for 'custom')."
        )

    # lazy import so --help works without the SDK installed
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("ERROR: openai SDK missing. Run: .venv\\Scripts\\python -m pip install openai")

    client = OpenAI(api_key=_load_key(Path(args.key_file)))

    common = dict(
        model=args.model,
        prompt=prompt,
        size=size,
        n=args.n,
        background=background,
    )
    # gpt-image-1 family supports quality low/medium/high; pass it through.
    if args.quality:
        common["quality"] = args.quality

    print(f"[gen] model={args.model} size={size} bg={background} "
          f"quality={args.quality} refs={len(args.ref)}")
    print(f"[gen] prompt: {prompt[:90]}...")

    if args.ref:
        # edits endpoint: use reference image(s) as init / style anchor
        files = []
        try:
            for r in args.ref:
                p = Path(r)
                if not p.is_file():
                    sys.exit(f"ERROR: ref image not found: {r}")
                files.append(open(p, "rb"))
            image_arg = files if len(files) > 1 else files[0]
            result = client.images.edit(image=image_arg, **common)
        finally:
            for f in files:
                f.close()
    else:
        result = client.images.generate(**common)

    # write outputs -> art_undecided/<ui|portraits>/<type>/ (raw, awaiting review)
    out_arg = args.out
    stamp = _dt.datetime.now().strftime("%H%M%S")
    base_tree = "portraits" if category == "portrait" else "ui"
    default_dir = repo_root / "art_undecided" / base_tree / ui_type
    default_dir.mkdir(parents=True, exist_ok=True)

    for i, item in enumerate(result.data):
        b64 = item.b64_json
        data = base64.b64decode(b64)
        if out_arg and args.n == 1:
            out_path = Path(out_arg)
        elif out_arg:
            stem = Path(out_arg)
            out_path = stem.with_name(f"{stem.stem}_{i}{stem.suffix or '.png'}")
        else:
            out_path = default_dir / f"{args.preset}_{stamp}_{i}.png"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(data)
        print(f"[ok] wrote {out_path}  ({len(data)//1024} KB)")


if __name__ == "__main__":
    main()
