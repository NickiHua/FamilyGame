using System.Collections;
using UnityEngine;
using UnityEngine.UI;
using TMPro;
using FantacyCentry.Domain.Units;

namespace FantacyCentry.View.Battle
{
    /// <summary>
    /// Fire-Emblem / 梦幻模拟战-style "cut to a side-view duel" — a pure-uGUI overlay (no extra
    /// camera / RenderTexture), so nothing is ever stretched or auto-zoomed.
    ///
    /// Layout, bottom to top: two character info panels (attacker left / defender right) sit at the
    /// very bottom; the battle-stage image sits DIRECTLY ABOVE them, shown with preserveAspect so it
    /// keeps its exact shape; the two duelists stand at the stage's vertical MIDDLE and are drawn at
    /// the SAME pixel size they are on the map (their animator frames are mirrored onto UI images).
    /// The live map shows behind a translucent dim. On a landed hit: screen shake + white flash.
    ///
    /// Toggle off via <see cref="BattleRunner.useBattleStage"/>.
    /// </summary>
    public sealed class BattleStageDirector : MonoBehaviour
    {
        [Header("Stage art")]
        [Tooltip("The battle-stage image (grass_stage). Shown with preserveAspect — never distorted.")]
        public Sprite stageSprite;

        [Header("Layout")]
        [Tooltip("Pixels reserved at the very bottom for the two character panels.")]
        public float panelZoneHeight = 150f;
        [Tooltip("Top of the stage band as a fraction of screen height (band = panelZoneHeight .. this).")]
        [Range(0.3f, 0.95f)] public float stageTopFraction = 0.62f;
        [Tooltip("Fraction of screen WIDTH the stage band spans (1 = full width).")]
        [Range(0.4f, 1f)] public float stageWidthFraction = 1f;
        [Tooltip("Horizontal stretch applied to the stage image only (1 = keep native shape).")]
        [Range(0.5f, 2f)] public float stageXStretch = 1.5f;
        [Tooltip("How dark the map behind the duel gets (0=untouched, 1=black).")]
        [Range(0f, 1f)] public float mapDim = 0.62f;

        [Header("Actors (drawn at map pixel size — do NOT need scaling)")]
        [Tooltip("Extra multiplier on the map-accurate character size (1 = exactly map size).")]
        public float charSizeMultiplier = 1f;
        [Tooltip("Feet ground line as a fraction of half the band height from centre (+ up). ~0 puts feet on the dirt path.")]
        [Range(-0.5f, 0.5f)] public float standYFrac = -0.28f;
        [Tooltip("Where a duelist starts, as a fraction of half the stage width from centre.")]
        [Range(0.1f, 0.5f)] public float spawnSpreadFrac = 0.34f;
        [Tooltip("Where a duelist stops to strike, as a fraction of half the stage width from centre.")]
        [Range(0.02f, 0.3f)] public float strikeSpreadFrac = 0.10f;
        [Tooltip("Walk speed as a fraction of the stage width per second.")]
        public float walkFracPerSec = 0.6f;

        [Header("Feel")]
        public float shakeMagnitude = 14f;   // pixels
        public float shakeDuration = 0.28f;
        public float flashDuration = 0.18f;

        [Header("Wiring")]
        [Tooltip("The map battle HUD canvas (END TURN / unit panel) — hidden during the duel.")]
        public Canvas mapHud;
        [Tooltip("The BattleHud — reused for its 立绘 portraits + char-panel frame in the forecast panels.")]
        public BattleHud hud;
        [Tooltip("The BattleRunner — to settle HP on the panels at the moment of impact.")]
        public BattleRunner runner;

        /// <summary>One side's damage result, so the stage can pop the number + settle the bar at impact.</summary>
        public struct Hit
        {
            public bool Landed;
            public int Dmg;
            public bool Crit;
            public int HpAfter;
            public static Hit Miss => new() { Landed = false };
        }

        [Header("Duel panels")]
        [Tooltip("Uniform scale of the two character panels (1 = full HUD size).")]
        [Range(0.4f, 1f)] public float panelScale = 0.66f;
        [Tooltip("Gap from the screen edge (px, before scaling) to each panel.")]
        public float panelEdgeMargin = 12f;

        [Header("Ability VFX frame banks (wired by builder)")]
        public Sprite[] swordwaveFrames;
        public Sprite[] lightningFrames;
        public Sprite[] icespikeFrames;
        public Sprite[] healFrames;
        [Tooltip("Playback speed of ability VFX frame sequences.")]
        public float vfxFps = 16f;
        [Tooltip("VFX size as a multiple of the target character's on-stage height.")]
        public float vfxScale = 1.7f;

        [Header("Ranged normal-attack projectiles (wired by builder)")]
        [Tooltip("Arrow sprite for bow units (points right).")]
        public Sprite arrowSprite;
        [Tooltip("Fireball frames for mage units.")]
        public Sprite[] fireballFrames;
        public float projectileSpeed = 1600f; // px/sec across the stage

        // Duelists are staged as inactive world clones (their animator runs and sets a SpriteRenderer);
        // we mirror that sprite onto a UI image each frame. Far-off so it never touches the map.
        private static readonly Vector3 CloneNursery = new(0f, -500f, 0f);

        private Canvas _canvas;
        private Image _dim, _flash, _stageImage;
        private RectTransform _band;      // holds stage image + duelist images; shakes as a unit
        private Image _atkImg, _defImg;
        private Image _vfxImg;   // ability effect frame player (on top of the duelists)
        private Image _projImg;  // ranged normal-attack projectile
        private BattleHud.InfoPanel _atkPanel, _defPanel;
        private readonly System.Collections.Generic.List<SpriteRenderer> _hiddenMap = new();
        private RangeOverlay _hiddenOverlay;
        private bool _built;

        // Active duel actor state (for per-frame mirroring).
        private SpriteRenderer _atkSR, _defSR;
        private float _atkScaleY, _defScaleY, _ppuScreen;

        public bool IsPlaying { get; private set; }

        // ------------------------------------------------------------------
        private void EnsureBuilt()
        {
            if (_built) return;
            _built = true;

            var canvasGo = new GameObject("BattleStageCanvas", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            canvasGo.transform.SetParent(transform, false);
            _canvas = canvasGo.GetComponent<Canvas>();
            _canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            _canvas.sortingOrder = 600;
            var scaler = canvasGo.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ConstantPixelSize; // 1 UI unit = 1 pixel
            scaler.scaleFactor = 1f;

            _dim = NewStretch("MapDim", canvasGo.transform, new Color(0f, 0f, 0f, 0f));

            // Band = the region above the panels; the stage + duelists live inside it and shake together.
            var bandGo = new GameObject("StageBand", typeof(RectTransform));
            bandGo.transform.SetParent(canvasGo.transform, false);
            _band = (RectTransform)bandGo.transform;
            _band.anchorMin = _band.anchorMax = new Vector2(0.5f, 0f);
            _band.pivot = new Vector2(0.5f, 0f);

            var stageGo = new GameObject("StageImage", typeof(RectTransform), typeof(Image));
            stageGo.transform.SetParent(_band, false);
            _stageImage = stageGo.GetComponent<Image>();
            _stageImage.sprite = stageSprite;
            _stageImage.preserveAspect = true;   // <-- keeps the exact shape, never squished
            _stageImage.raycastTarget = false;
            var srt = (RectTransform)stageGo.transform;
            srt.anchorMin = Vector2.zero; srt.anchorMax = Vector2.one;
            srt.offsetMin = Vector2.zero; srt.offsetMax = Vector2.zero;

            _atkImg = NewActorImage("AttackerActor", _band);
            _defImg = NewActorImage("DefenderActor", _band);
            _vfxImg = NewActorImage("AbilityVfx", _band);
            _projImg = NewActorImage("Projectile", _band);

            _flash = NewStretch("Flash", canvasGo.transform, new Color(1f, 1f, 1f, 0f));

            // Reuse the ACTUAL character panel (built by BattleHud) — attacker bottom-left,
            // defender bottom-right — so it matches the HUD exactly (no re-stretched copy).
            if (hud != null)
            {
                _atkPanel = hud.CreateInfoPanel(canvasGo.transform, leftSide: true);
                _defPanel = hud.CreateInfoPanel(canvasGo.transform, leftSide: false);
                ApplyPanelTransform(_atkPanel, left: true);
                ApplyPanelTransform(_defPanel, left: false);
                _atkPanel.Root.gameObject.SetActive(false);
                _defPanel.Root.gameObject.SetActive(false);
            }

            _canvas.gameObject.SetActive(false);
        }

        /// <summary>Scale a duel panel down uniformly and tuck it against its screen edge, leaving a
        /// gap in the middle (for a future 对战 versus icon).</summary>
        private void ApplyPanelTransform(BattleHud.InfoPanel panel, bool left)
        {
            const float panelWidth = 780f; // matches BuildInfoPanel's W
            var rt = panel.Root;
            rt.localScale = new Vector3(panelScale, panelScale, 1f);
            float halfW = panelWidth * panelScale * 0.5f;
            float centreX = panelEdgeMargin + halfW;   // pivot is (0.5,0) → this is the panel centre
            rt.anchoredPosition = new Vector2(left ? centreX : -centreX, 20f);
        }

        private static Image NewStretch(string name, Transform parent, Color color)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Image));
            go.transform.SetParent(parent, false);
            var img = go.GetComponent<Image>();
            img.color = color; img.raycastTarget = false;
            var rt = (RectTransform)go.transform;
            rt.anchorMin = Vector2.zero; rt.anchorMax = Vector2.one;
            rt.offsetMin = Vector2.zero; rt.offsetMax = Vector2.zero;
            return img;
        }

        private static Image NewActorImage(string name, Transform parent)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Image));
            go.transform.SetParent(parent, false);
            var img = go.GetComponent<Image>();
            img.raycastTarget = false;
            img.preserveAspect = true;
            var rt = (RectTransform)go.transform;
            rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f); // relative to band centre
            rt.pivot = new Vector2(0.5f, 0f);                      // pivot at the feet
            go.SetActive(false);
            return img;
        }

        /// <summary>Position the band (region above the panels) at the current screen size.</summary>
        private void LayoutBand()
        {
            float bandBottom = panelZoneHeight;
            float bandTop = Mathf.Max(bandBottom + 80f, Screen.height * stageTopFraction);
            float bandH = bandTop - bandBottom;
            float bandW = Mathf.Max(80f, Screen.width * stageWidthFraction);
            _band.sizeDelta = new Vector2(bandW, bandH);
            _band.anchoredPosition = new Vector2(0f, bandBottom);
            _bandPos = _band.anchoredPosition;
            if (_stageImage != null)
                _stageImage.rectTransform.localScale = new Vector3(stageXStretch, 1f, 1f);
            // Pixels-per-world-unit on the MAP, so duelists match their on-map size exactly.
            float ortho = Camera.main != null ? Camera.main.orthographicSize : 7f;
            _ppuScreen = Screen.height / (2f * Mathf.Max(0.01f, ortho));
        }

        private Vector2 _bandPos;

        // ------------------------------------------------------------------
        public IEnumerator Play(UnitView atkView, UnitView defView, Hit atkHit, bool counter, Hit counterHit)
        {
            EnsureBuilt();
            if (atkView == null || defView == null) yield break;
            IsPlaying = true;
            LayoutBand();
            _canvas.gameObject.SetActive(true);
            if (mapHud != null) mapHud.gameObject.SetActive(false);

            // Show the SAME character panel as the HUD: attacker left, defender right.
            if (_atkPanel != null && hud != null)
            {
                _atkPanel.Root.gameObject.SetActive(true);
                hud.RefreshPanel(_atkPanel, atkView.Unit);
            }
            if (_defPanel != null && hud != null)
            {
                _defPanel.Root.gameObject.SetActive(true);
                hud.RefreshPanel(_defPanel, defView.Unit);
            }

            yield return Fade(_dim, 0f, mapDim, 0.18f);

            HideMapUnits();   // clear the board so the duel isn't cluttered by the map sprites

            var atk = SpawnActor(atkView, _atkImg, left: true, out _atkSR, out _atkScaleY);
            var def = SpawnActor(defView, _defImg, left: false, out _defSR, out _defScaleY);
            atk.SetFacing(Facing.East);
            def.SetFacing(Facing.West);

            float half = _band.sizeDelta.x * 0.5f;
            float spawnX = half * spawnSpreadFrac;
            float meleeApproachX = spawnX - half * 0.16f; // walk right up next to the foe before swinging
            _atkImg.rectTransform.anchoredPosition = new Vector2(-spawnX, 0f);
            _defImg.rectTransform.anchoredPosition = new Vector2(spawnX, 0f);

            yield return new WaitForSeconds(0.25f);

            // Attacker: melee walks ACROSS to the foe and swings; ranged stays put and shoots.
            System.Action settleDef = () => SettleHit(_defPanel, _defImg.rectTransform, defView.Unit, atkHit);
            if (IsRanged(atkView.Unit))
            {
                yield return RangedStrike(_atkImg, atk, _defImg, def, atkHit.Landed, IsMagic(atkView.Unit), toRight: true, settleDef);
            }
            else
            {
                yield return WalkImg(_atkImg, atk, meleeApproachX, Facing.East);
                yield return Strike(atk, def, defActive: true, atkHit.Landed, settleDef);
                yield return WalkImg(_atkImg, atk, -spawnX, Facing.West);
                atk.SetFacing(Facing.East);
            }

            // Defender counters (same melee/ranged rule).
            if (counter)
            {
                System.Action settleAtk = () => SettleHit(_atkPanel, _atkImg.rectTransform, atkView.Unit, counterHit);
                if (IsRanged(defView.Unit))
                {
                    yield return RangedStrike(_defImg, def, _atkImg, atk, counterHit.Landed, IsMagic(defView.Unit), toRight: false, settleAtk);
                }
                else
                {
                    yield return WalkImg(_defImg, def, -meleeApproachX, Facing.West);
                    yield return Strike(def, atk, defActive: true, counterHit.Landed, settleAtk);
                    yield return WalkImg(_defImg, def, spawnX, Facing.East);
                    def.SetFacing(Facing.West);
                }
            }

            yield return new WaitForSeconds(0.2f);

            yield return Fade(_dim, mapDim, 0f, 0.18f);
            _atkImg.gameObject.SetActive(false);
            _defImg.gameObject.SetActive(false);
            if (atk != null) Destroy(atk.gameObject);
            if (def != null) Destroy(def.gameObject);
            _atkSR = _defSR = null;
            if (_atkPanel != null) _atkPanel.Root.gameObject.SetActive(false);
            if (_defPanel != null) _defPanel.Root.gameObject.SetActive(false);
            RestoreMapUnits();
            if (mapHud != null) mapHud.gameObject.SetActive(true);
            _canvas.gameObject.SetActive(false);
            IsPlaying = false;
        }

        /// <summary>
        /// Cast演出 for a ranged ability (剑气 / 闪电 / 治疗). The caster stays put and plays a cast
        /// pose; the effect's frame VFX plays ON the target sprite (so the hit lands on the target),
        /// then the target reacts (damage) or glows (heal). No walking, no counter.
        /// </summary>
        public IEnumerator PlayAbility(UnitView atkView, UnitView defView, Hit hit, string vfxKey, bool isHeal, float speedMul = 1f)
        {
            EnsureBuilt();
            if (atkView == null || defView == null) yield break;
            IsPlaying = true;
            LayoutBand();
            _canvas.gameObject.SetActive(true);
            if (mapHud != null) mapHud.gameObject.SetActive(false);

            if (_atkPanel != null && hud != null) { _atkPanel.Root.gameObject.SetActive(true); hud.RefreshPanel(_atkPanel, atkView.Unit); }
            if (_defPanel != null && hud != null) { _defPanel.Root.gameObject.SetActive(true); hud.RefreshPanel(_defPanel, defView.Unit); }

            yield return Fade(_dim, 0f, mapDim, 0.18f);
            HideMapUnits();

            var atk = SpawnActor(atkView, _atkImg, left: true, out _atkSR, out _atkScaleY);
            var def = SpawnActor(defView, _defImg, left: false, out _defSR, out _defScaleY);
            atk.SetFacing(Facing.East);
            def.SetFacing(Facing.West);

            float half = _band.sizeDelta.x * 0.5f;
            float spawnX = half * spawnSpreadFrac;
            _atkImg.rectTransform.anchoredPosition = new Vector2(-spawnX, 0f);
            _defImg.rectTransform.anchoredPosition = new Vector2(spawnX, 0f);

            yield return new WaitForSeconds(0.25f);

            // Caster cast pose.
            atk.PlayOneShot(CharacterSpriteAnimator.Action.Attack);
            yield return new WaitForSeconds(0.2f);

            // Play the effect; swordwave travels from the caster along the ground, others strike
            // in place on the target. All are ground-aligned (bottom pivot).
            Sprite[] bank = BankFor(vfxKey);
            bool swordwave = !string.IsNullOrEmpty(vfxKey) && vfxKey.ToLowerInvariant().Contains("sword");
            bool impactFired = false;
            System.Action impact = () =>
            {
                if (impactFired) return; impactFired = true;
                if (isHeal) { StartCoroutine(Fade(_flash, 0.3f, 0f, 0.25f)); }
                else if (hit.Landed)
                {
                    def.PlayOneShot(CharacterSpriteAnimator.Action.Hit);
                    StartCoroutine(Shake());
                    StartCoroutine(Fade(_flash, 0.5f, 0f, flashDuration));
                    BattleAudio.PlayHit();
                }
                // Pop the damage number + settle the defender's panel HP right on impact.
                if (!isHeal) SettleHit(_defPanel, _defImg.rectTransform, defView.Unit, hit);
            };
            float casterFeetX = _atkImg.rectTransform.anchoredPosition.x;
            yield return PlayVfx(bank, _defImg.rectTransform, impact,
                travelFromX: swordwave ? casterFeetX : (float?)null,
                impactFrac: swordwave ? 0.82f : 0.45f,
                speedMul: speedMul, headHold: swordwave);
            if (!impactFired) impact();

            yield return new WaitForSeconds(0.25f);

            yield return Fade(_dim, mapDim, 0f, 0.18f);
            _atkImg.gameObject.SetActive(false);
            _defImg.gameObject.SetActive(false);
            if (_vfxImg != null) _vfxImg.gameObject.SetActive(false);
            if (atk != null) Destroy(atk.gameObject);
            if (def != null) Destroy(def.gameObject);
            _atkSR = _defSR = null;
            if (_atkPanel != null) _atkPanel.Root.gameObject.SetActive(false);
            if (_defPanel != null) _defPanel.Root.gameObject.SetActive(false);
            RestoreMapUnits();
            if (mapHud != null) mapHud.gameObject.SetActive(true);
            _canvas.gameObject.SetActive(false);
            IsPlaying = false;
        }

        public Sprite[] BankFor(string key)
        {
            if (string.IsNullOrEmpty(key)) return null;
            key = key.ToLowerInvariant();
            if (key.Contains("sword")) return swordwaveFrames;
            if (key.Contains("light") || key.Contains("thunder")) return lightningFrames;
            if (key.Contains("ice") || key.Contains("frost")) return icespikeFrames;
            if (key.Contains("fire")) return fireballFrames;
            if (key.Contains("heal")) return healFrames;
            return null;
        }

        /// <summary>At the moment of a landed/missed hit: settle the target's HP bar on its panel and
        /// pop a floating number over its sprite (inside the stage).</summary>
        private void SettleHit(BattleHud.InfoPanel panel, RectTransform overRt,
                               FantacyCentry.Domain.Units.Unit target, Hit hit)
        {
            if (runner != null && target != null) runner.SetDisplayHp(target, hit.HpAfter);
            if (hud != null && panel != null && target != null) hud.RefreshPanel(panel, target);
            string text; Color col;
            if (!hit.Landed) { text = "MISS"; col = new Color(0.85f, 0.85f, 0.85f); }
            else if (hit.Crit) { text = "CRIT " + hit.Dmg; col = new Color(1f, 0.85f, 0.2f); }
            else { text = hit.Dmg.ToString(); col = new Color(1f, 0.5f, 0.45f); }
            if (overRt != null) StartCoroutine(StageFloat(overRt, text, col));
        }

        /// <summary>A floating combat number inside the stage band, rising + fading over the target.</summary>
        private IEnumerator StageFloat(RectTransform overRt, string text, Color col)
        {
            var go = new GameObject("StageFloat", typeof(RectTransform));
            var rt = (RectTransform)go.transform;
            rt.SetParent(_band, false);
            rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f);
            rt.pivot = new Vector2(0.5f, 0.5f);
            var tmp = go.AddComponent<TextMeshProUGUI>();
            if (hud != null && hud.font != null) tmp.font = hud.font;
            tmp.alignment = TextAlignmentOptions.Center;
            tmp.fontSize = 42f; tmp.fontStyle = FontStyles.Bold; tmp.raycastTarget = false;
            tmp.textWrappingMode = TextWrappingModes.NoWrap;
            tmp.text = text; tmp.color = col;
            Vector2 basePos = overRt.anchoredPosition + new Vector2(0f, overRt.sizeDelta.y * 0.75f);
            float t = 0f, dur = 0.9f;
            while (t < dur)
            {
                t += Time.deltaTime; float k = t / dur;
                rt.anchoredPosition = basePos + new Vector2(0f, 70f * k);
                Color c = col; c.a = 1f - k; tmp.color = c;
                rt.SetAsLastSibling();
                yield return null;
            }
            Destroy(go);
        }

        /// <summary>Play a frame bank on <see cref="_vfxImg"/> (ground-aligned). If <paramref name="travelFromX"/>
        /// is set the effect slides from that x to the target (剑气 wave), arriving by the impact frame;
        /// with <paramref name="headHold"/> the leading (travel) frames linger longer. <paramref name="speedMul"/>
        /// scales playback (0.5 = half speed). <paramref name="onImpact"/> fires at <paramref name="impactFrac"/>.</summary>
        private IEnumerator PlayVfx(Sprite[] bank, RectTransform target, System.Action onImpact,
                                   float? travelFromX = null, float impactFrac = 0.45f,
                                   float speedMul = 1f, bool headHold = false)
        {
            if (bank == null || bank.Length == 0)
            {
                onImpact?.Invoke();
                yield break;
            }
            var rt = _vfxImg.rectTransform;
            rt.pivot = new Vector2(0.5f, 0f); // ground pivot (feet line)
            _vfxImg.gameObject.SetActive(true);
            _vfxImg.transform.SetAsLastSibling();
            int impactIdx = Mathf.Clamp(Mathf.RoundToInt((bank.Length - 1) * impactFrac), 0, bank.Length - 1);
            float spf = 1f / Mathf.Max(0.5f, vfxFps * Mathf.Max(0.1f, speedMul));
            bool traveling = travelFromX.HasValue;
            for (int i = 0; i < bank.Length; i++)
            {
                Sprite s = bank[i];
                if (s != null)
                {
                    _vfxImg.sprite = s;
                    float h = target.sizeDelta.y * vfxScale;
                    float aspect = s.rect.height > 0 ? s.rect.width / s.rect.height : 1f;
                    rt.sizeDelta = new Vector2(h * aspect, h);
                    // Travel arrives at the target by the impact frame; then stays on the target.
                    float kx = traveling && impactIdx > 0 ? Mathf.Clamp01((float)i / impactIdx) : 1f;
                    float x = traveling
                        ? Mathf.Lerp(travelFromX.Value, target.anchoredPosition.x, kx)
                        : target.anchoredPosition.x;
                    rt.anchoredPosition = new Vector2(x, target.anchoredPosition.y);
                }
                if (i == impactIdx) onImpact?.Invoke();
                // Linger on the leading travel frames (剑气 forms + rushes on frames 1-2).
                float dur = (traveling && headHold && i < impactIdx) ? spf * 2.4f : spf;
                yield return new WaitForSeconds(dur);
            }
            _vfxImg.gameObject.SetActive(false);
        }

        /// <summary>Hide every unit sprite on the map AND the move/attack range tiles so the duel
        /// overlay reads cleanly; both are restored when the duel ends.</summary>
        private void HideMapUnits()
        {
            _hiddenMap.Clear();
            foreach (var view in FindObjectsByType<UnitView>(FindObjectsInactive.Exclude))
            {
                foreach (var r in view.GetComponentsInChildren<SpriteRenderer>(true))
                {
                    if (!r.enabled) continue;
                    r.enabled = false;
                    _hiddenMap.Add(r);
                }
            }
            // The red attack / blue move range circles.
            _hiddenOverlay = FindAnyObjectByType<RangeOverlay>();
            if (_hiddenOverlay != null && _hiddenOverlay.gameObject.activeSelf)
                _hiddenOverlay.gameObject.SetActive(false);
            else
                _hiddenOverlay = null;
        }

        private void RestoreMapUnits()
        {
            foreach (var r in _hiddenMap)
                if (r != null) r.enabled = true;
            _hiddenMap.Clear();
            if (_hiddenOverlay != null) _hiddenOverlay.gameObject.SetActive(true);
            _hiddenOverlay = null;
        }

        // ------------------------------------------------------------------
        /// <summary>Mirror each active duelist's current animator frame onto its UI image, at map size.</summary>
        private void LateUpdate()
        {
            if (!IsPlaying) return;
            Mirror(_atkSR, _atkImg, _atkScaleY);
            Mirror(_defSR, _defImg, _defScaleY);
        }

        private void Mirror(SpriteRenderer sr, Image img, float worldScaleY)
        {
            if (sr == null || img == null || sr.sprite == null) return;
            Sprite s = sr.sprite;
            img.sprite = s;
            float worldH = (s.rect.height / s.pixelsPerUnit) * worldScaleY;
            float hPx = worldH * _ppuScreen * charSizeMultiplier;
            float aspect = s.rect.height > 0 ? s.rect.width / s.rect.height : 1f;
            var rt = img.rectTransform;
            rt.sizeDelta = new Vector2(hPx * aspect, hPx);
            rt.localScale = new Vector3(sr.flipX ? -1f : 1f, 1f, 1f);
            // Feet-pivoted: place the feet on the dirt path (a fraction of the band height from centre).
            Vector2 p = rt.anchoredPosition;
            p.y = _band.sizeDelta.y * 0.5f * standYFrac;
            rt.anchoredPosition = p;
        }

        private CharacterSpriteAnimator SpawnActor(UnitView view, Image img, bool left,
                                                   out SpriteRenderer sr, out float worldScaleY)
        {
            GameObject clone = Instantiate(view.gameObject);
            clone.name = view.gameObject.name + "_duel";
            clone.transform.position = CloneNursery;   // off in the nursery, never seen directly
            StripComponent<UnitView>(clone);
            StripComponent<GridMover>(clone);
            StripComponent<YSort>(clone);
            StripComponent<MapObstacle>(clone);
            StripComponent<CharacterDemoController>(clone);

            sr = clone.GetComponentInChildren<SpriteRenderer>();
            if (sr != null) sr.enabled = false;         // we read its .sprite; we don't render it in world
            worldScaleY = clone.transform.lossyScale.y; // the prefab's own scale (≈0.6) = map size

            img.gameObject.SetActive(true);
            img.rectTransform.localScale = new Vector3(left ? 1f : -1f, 1f, 1f);
            return clone.GetComponent<CharacterSpriteAnimator>();
        }

        private static void StripComponent<T>(GameObject go) where T : Component
        {
            foreach (var c in go.GetComponentsInChildren<T>(true)) Destroy(c);
        }

        private IEnumerator WalkImg(Image img, CharacterSpriteAnimator anim, float targetX, Facing face)
        {
            if (img == null || anim == null) yield break;
            anim.SetFacing(face);
            anim.SetMoving(true);
            float speed = _band.sizeDelta.x * walkFracPerSec;
            var rt = img.rectTransform;
            while (Mathf.Abs(rt.anchoredPosition.x - targetX) > 1f)
            {
                Vector2 p = rt.anchoredPosition;
                p.x = Mathf.MoveTowards(p.x, targetX, speed * Time.deltaTime);
                rt.anchoredPosition = p;
                yield return null;
            }
            anim.SetMoving(false);
        }

        private IEnumerator Strike(CharacterSpriteAnimator attacker, CharacterSpriteAnimator defender, bool defActive, bool hit, System.Action onImpact = null)
        {
            float dur = attacker.PlayOneShot(CharacterSpriteAnimator.Action.Attack);
            BattleAudio.PlaySlash();
            yield return new WaitForSeconds(dur * 0.5f);
            if (hit && defActive && defender != null)
            {
                defender.PlayOneShot(CharacterSpriteAnimator.Action.Hit);
                StartCoroutine(Shake());
                StartCoroutine(Fade(_flash, 0.6f, 0f, flashDuration));
                BattleAudio.PlayHit();
            }
            onImpact?.Invoke();
            yield return new WaitForSeconds(Mathf.Max(0.1f, dur * 0.5f));
        }

        private static bool IsRanged(FantacyCentry.Domain.Units.Unit u) => u != null && u.MaxRange > 1;
        private static bool IsMagic(FantacyCentry.Domain.Units.Unit u) =>
            u != null && (u.Weapon == FantacyCentry.Domain.Units.WeaponType.Magic
                       || u.Weapon == FantacyCentry.Domain.Units.WeaponType.Holy
                       || u.Weapon == FantacyCentry.Domain.Units.WeaponType.Dark);

        /// <summary>Ranged normal attack: the shooter stays put, plays a cast/draw pose, and a
        /// projectile (arrow / fireball) flies to the target, which then reacts on a landed hit.</summary>
        private IEnumerator RangedStrike(Image shooterImg, CharacterSpriteAnimator shooterAnim,
                                         Image targetImg, CharacterSpriteAnimator targetAnim,
                                         bool hit, bool isMagic, bool toRight, System.Action onImpact = null)
        {
            shooterAnim.SetFacing(toRight ? Facing.East : Facing.West);
            shooterAnim.PlayOneShot(CharacterSpriteAnimator.Action.Attack);
            if (isMagic) BattleAudio.PlayMagic("fire"); else BattleAudio.PlaySlash();
            yield return new WaitForSeconds(0.18f);

            // Fly the projectile from shooter to target along a parabolic arc.
            var prt = _projImg.rectTransform;
            prt.pivot = new Vector2(0.5f, 0.5f);
            _projImg.gameObject.SetActive(true);
            _projImg.transform.SetAsLastSibling();
            Sprite[] fb = fireballFrames;
            // Size by the LONGER edge so a wide arrow doesn't blow up (arrow ~0.4× char height long).
            float projLen = Mathf.Max(18f, targetImg.rectTransform.sizeDelta.y * 0.4f);
            void SetProjSprite(Sprite s)
            {
                if (s == null) return;
                _projImg.sprite = s;
                float aspect = s.rect.height > 0 ? s.rect.width / s.rect.height : 1f;
                if (aspect >= 1f) prt.sizeDelta = new Vector2(projLen, projLen / aspect);
                else prt.sizeDelta = new Vector2(projLen * aspect, projLen);
            }
            SetProjSprite(isMagic ? (fb != null && fb.Length > 0 ? fb[0] : null) : arrowSprite);

            Vector2 from = shooterImg.rectTransform.anchoredPosition;
            Vector2 to = targetImg.rectTransform.anchoredPosition;
            // Launch from the shooter's mid-body, land on the target's mid-body.
            from.y += shooterImg.rectTransform.sizeDelta.y * 0.5f;
            to.y += targetImg.rectTransform.sizeDelta.y * 0.5f;
            float dist = Mathf.Abs(to.x - from.x);
            float arc = Mathf.Max(40f, dist * 0.28f);      // parabola peak height
            float dur = Mathf.Clamp(dist / Mathf.Max(1f, projectileSpeed), 0.18f, 0.7f);
            float t = 0f; int frame = 0; float frameT = 0f; Vector2 prev = from;
            while (t < dur)
            {
                t += Time.deltaTime;
                float k = Mathf.Clamp01(t / dur);
                Vector2 pos = Vector2.Lerp(from, to, k);
                pos.y += arc * 4f * k * (1f - k);          // parabolic arc
                prt.anchoredPosition = pos;
                // Point the arrow along its flight (nose up on the way, down on descent).
                if (!isMagic)
                {
                    Vector2 d = pos - prev;
                    if (d.sqrMagnitude > 0.01f)
                        prt.localRotation = Quaternion.Euler(0f, 0f, Mathf.Atan2(d.y, d.x) * Mathf.Rad2Deg);
                }
                prev = pos;
                if (isMagic && fb != null && fb.Length > 0)
                {
                    frameT += Time.deltaTime;
                    if (frameT >= 1f / 16f) { frameT = 0f; frame = (frame + 1) % Mathf.Min(6, fb.Length); SetProjSprite(fb[frame]); }
                }
                yield return null;
            }
            prt.localRotation = Quaternion.identity;
            _projImg.gameObject.SetActive(false);

            if (hit && targetAnim != null)
            {
                targetAnim.PlayOneShot(CharacterSpriteAnimator.Action.Hit);
                StartCoroutine(Shake());
                StartCoroutine(Fade(_flash, 0.5f, 0f, flashDuration));
                BattleAudio.PlayHit();
                // Magic impact: a small fireball burst on the target.
                if (isMagic && fb != null && fb.Length > 0)
                    yield return PlayVfx(fb, targetImg.rectTransform, null);
            }
            onImpact?.Invoke();
            yield return new WaitForSeconds(0.12f);
            shooterAnim.SetFacing(toRight ? Facing.East : Facing.West);
        }

        private IEnumerator Shake()
        {
            float t = 0f;
            while (t < shakeDuration)
            {
                t += Time.deltaTime;
                float damper = 1f - (t / shakeDuration);
                Vector2 off = Random.insideUnitCircle * (shakeMagnitude * damper);
                _band.anchoredPosition = _bandPos + off;
                yield return null;
            }
            _band.anchoredPosition = _bandPos;
        }

        private IEnumerator Fade(Graphic g, float from, float to, float time)
        {
            float t = 0f;
            Color c = g.color;
            c.a = from; g.color = c;
            while (t < time)
            {
                t += Time.deltaTime;
                c.a = Mathf.Lerp(from, to, t / time);
                g.color = c;
                yield return null;
            }
            c.a = to; g.color = c;
        }
    }
}
