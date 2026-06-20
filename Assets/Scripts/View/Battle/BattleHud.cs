using System;
using System.Collections;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using FantacyCentry.Domain.Units;

namespace FantacyCentry.View.Battle
{
    /// <summary>
    /// uGUI heads-up display that lives on the battle <see cref="Canvas"/>. For now it owns the
    /// turn banner (a wide ornate plate that slides in, holds, then fades when the active side
    /// changes). Later steps add the action menu, damage floaters and unit info panel here too.
    /// The banner UI is built entirely in code so the editor scene builder only has to add this
    /// component and assign the two banner sprites — no prefab wiring required.
    /// </summary>
    [RequireComponent(typeof(Canvas))]
    public sealed class BattleHud : MonoBehaviour
    {
        [Header("Wiring")]
        public BattleRunner runner;
        public BattleInputController input;

        [Tooltip("Camera used to project damage-floater world positions onto the canvas. " +
                 "Falls back to Camera.main if left empty.")]
        public Camera worldCamera;

        [Header("Turn banner sprites (Assets/Art/UI/banners/)")]
        public Sprite bannerPlayer;
        public Sprite bannerEnemy;

        [Header("Action buttons (Assets/Art/UI/buttons/)")]
        public Sprite buttonNormal;
        public Sprite buttonHover;
        public Sprite buttonPressed;

        [Tooltip("Optional CJK font. Leave empty to use TMP's default font (Latin only). " +
                 "Assign a Chinese TMP font asset to show 我方回合 / 敌方回合.")]
        public TMP_FontAsset font;

        [Header("Banner text")]
        public string playerText = "PLAYER PHASE";
        public string enemyText = "ENEMY PHASE";

        [Header("Banner timing (seconds)")]
        public float slideIn = 0.4f;
        public float hold = 1.25f;
        public float fadeOut = 0.8f;

        [Tooltip("Peak opacity of the banner (1 = solid). Lower for a translucent overlay.")]
        [Range(0f, 1f)]
        public float peakAlpha = 0.82f;

        [Header("Damage floaters")]
        [Tooltip("Seconds a damage/MISS number stays on screen before fading out.")]
        public float floaterLife = 0.9f;
        [Tooltip("How far (world units) a floater drifts upward over its life.")]
        public float floaterRise = 0.8f;

        [Header("Unit HP bars (float above each unit)")]
        [Tooltip("World-space height above a unit's feet to float its HP bar.")]
        public float hpBarWorldOffset = 1.15f;
        [Tooltip("HP bar size in canvas pixels (width x height).")]
        public Vector2 hpBarSize = new Vector2(70f, 9f);

        [Header("Unit info panel (Assets/Art/UI/panels/)")]
        public Sprite panelUnitInfo;

        private RectTransform _banner;
        private CanvasGroup _bannerGroup;
        private Image _bannerImage;
        private TMP_Text _bannerLabel;
        private Coroutine _bannerRoutine;

        // Action menu (bottom-left command buttons + status label).
        private TMP_Text _statusLabel;
        private Button _waitButton;
        private Button _endTurnButton;

        // Damage-floater pool (parented under a full-rect, raycast-off container).
        private RectTransform _floaterRoot;
        private readonly List<Floater> _floaters = new();

        // World-following HP bars (one lazily-built bar per unit view).
        private RectTransform _hpRoot;
        private readonly Dictionary<UnitView, HpBar> _hpBars = new();

        // Unit info panel (bottom-right; shows the selected or hovered unit).
        // Clean, non-pixel look: built entirely from uGUI primitives so the LAYOUT is ours (text
        // always aligns) rather than guessing slots baked into a pixel-art panel sprite. A high-res
        // frame + character portrait can be dropped in later without moving any of this text.
        private RectTransform _infoPanel;
        private Image _infoBorderImg;        // outer frame, tinted by team
        private Image _infoPortraitImg;      // portrait placeholder frame, tinted by team
        private TMP_Text _infoPortraitLetter; // placeholder initial until real 立绘 art exists
        private TMP_Text _infoName;
        private TMP_Text[] _statCells;       // 4x2 grid: ATK DEF MAG RES / HIT EVA CRT MOV
        private TMP_Text _infoHp;
        private RectTransform _infoHpFill;
        private Image _infoHpFillImg;

        /// <summary>True while the turn banner is animating in/holding/out. The battle runner
        /// waits on this so neither side acts until the banner has cleared.</summary>
        public bool IsBannerPlaying { get; private set; }

        private void Awake()
        {
            BuildBanner();
            BuildActionMenu();
            BuildFloaterRoot();
            BuildHpBarRoot();
            BuildInfoPanel();
        }

        private void OnEnable()
        {
            if (runner != null) runner.PhaseChanged += OnPhaseChanged;
            if (input != null) input.SelectionChanged += RefreshActionMenu;
        }

        private void OnDisable()
        {
            if (runner != null) runner.PhaseChanged -= OnPhaseChanged;
            if (input != null) input.SelectionChanged -= RefreshActionMenu;
        }

        private void Update()
        {
            // Button availability depends on busy/phase state that changes outside selection
            // events (e.g. the banner clearing), so keep it in sync each frame — cheap.
            RefreshActionMenu();
            UpdateFloaters();
            UpdateHpBars();
            UpdateInfoPanel();
        }

        private void OnPhaseChanged(Team team, int round)
        {
            bool isPlayer = team == Team.Player;
            _bannerImage.sprite = isPlayer ? bannerPlayer : bannerEnemy;
            _bannerLabel.text = isPlayer ? playerText : enemyText;

            if (_bannerRoutine != null) StopCoroutine(_bannerRoutine);
            _bannerRoutine = StartCoroutine(PlayBanner());
        }

        private IEnumerator PlayBanner()
        {
            const float restY = 0f;       // settled at the vertical centre of the screen
            const float belowY = -60f;    // starts slightly low, drifts up into place

            IsBannerPlaying = true;
            _banner.gameObject.SetActive(true);
            _bannerGroup.alpha = 0f;

            // Drift up + fade in.
            float t = 0f;
            while (t < slideIn)
            {
                t += Time.deltaTime;
                float k = slideIn > 0f ? Mathf.Clamp01(t / slideIn) : 1f;
                float eased = 1f - (1f - k) * (1f - k); // ease-out
                _banner.anchoredPosition = new Vector2(0f, Mathf.Lerp(belowY, restY, eased));
                _bannerGroup.alpha = peakAlpha * k;
                yield return null;
            }
            _banner.anchoredPosition = new Vector2(0f, restY);
            _bannerGroup.alpha = peakAlpha;

            yield return new WaitForSeconds(hold);

            // Fade out.
            t = 0f;
            while (t < fadeOut)
            {
                t += Time.deltaTime;
                float k = fadeOut > 0f ? Mathf.Clamp01(t / fadeOut) : 1f;
                _bannerGroup.alpha = peakAlpha * (1f - k);
                yield return null;
            }

            _bannerGroup.alpha = 0f;
            _banner.gameObject.SetActive(false);
            _bannerRoutine = null;
            IsBannerPlaying = false;
        }

        // --- UI construction -------------------------------------------------

        private void BuildBanner()
        {
            var go = new GameObject("TurnBanner",
                typeof(RectTransform), typeof(CanvasGroup), typeof(Image));
            _banner = go.GetComponent<RectTransform>();
            _banner.SetParent(transform, false);

            // Anchored to the centre of the canvas.
            _banner.anchorMin = new Vector2(0.5f, 0.5f);
            _banner.anchorMax = new Vector2(0.5f, 0.5f);
            _banner.pivot = new Vector2(0.5f, 0.5f);
            _banner.sizeDelta = new Vector2(760f, 150f);
            _banner.anchoredPosition = new Vector2(0f, 0f);

            _bannerGroup = go.GetComponent<CanvasGroup>();
            _bannerGroup.blocksRaycasts = false; // banner never eats clicks
            _bannerGroup.interactable = false;
            _bannerGroup.alpha = 0f;

            _bannerImage = go.GetComponent<Image>();
            _bannerImage.sprite = bannerPlayer;
            _bannerImage.type = Image.Type.Simple;
            _bannerImage.preserveAspect = true;
            _bannerImage.raycastTarget = false;

            // Centred label inside the banner.
            var labelGo = new GameObject("Label", typeof(RectTransform));
            var labelRt = labelGo.GetComponent<RectTransform>();
            labelRt.SetParent(_banner, false);
            labelRt.anchorMin = Vector2.zero;
            labelRt.anchorMax = Vector2.one;
            labelRt.offsetMin = Vector2.zero;
            labelRt.offsetMax = Vector2.zero;

            _bannerLabel = labelGo.AddComponent<TextMeshProUGUI>();
            if (font != null) _bannerLabel.font = font;
            _bannerLabel.alignment = TextAlignmentOptions.Center;
            _bannerLabel.enableAutoSizing = true;
            _bannerLabel.fontSizeMin = 18f;
            _bannerLabel.fontSizeMax = 54f;
            _bannerLabel.fontStyle = FontStyles.Bold;
            _bannerLabel.color = new Color(0.97f, 0.93f, 0.78f); // warm parchment gold
            _bannerLabel.raycastTarget = false;
            _bannerLabel.text = playerText;

            go.SetActive(false);
        }

        // --- Action menu -----------------------------------------------------

        private void BuildActionMenu()
        {
            // Status label (top-left): whose turn / what is selected.
            var statusGo = new GameObject("StatusLabel", typeof(RectTransform));
            var statusRt = statusGo.GetComponent<RectTransform>();
            statusRt.SetParent(transform, false);
            statusRt.anchorMin = new Vector2(0f, 1f);
            statusRt.anchorMax = new Vector2(0f, 1f);
            statusRt.pivot = new Vector2(0f, 1f);
            statusRt.anchoredPosition = new Vector2(24f, -20f);
            statusRt.sizeDelta = new Vector2(420f, 40f);

            _statusLabel = statusGo.AddComponent<TextMeshProUGUI>();
            if (font != null) _statusLabel.font = font;
            _statusLabel.alignment = TextAlignmentOptions.TopLeft;
            _statusLabel.fontSize = 26f;
            _statusLabel.fontStyle = FontStyles.Bold;
            _statusLabel.color = new Color(0.97f, 0.93f, 0.78f);
            _statusLabel.raycastTarget = false;

            // Command buttons, stacked in the bottom-left corner.
            _waitButton = BuildButton("WaitButton", "WAIT (W)",
                new Vector2(24f, 104f), OnWaitClicked);
            _endTurnButton = BuildButton("EndTurnButton", "END TURN (Space)",
                new Vector2(24f, 24f), OnEndTurnClicked);

            RefreshActionMenu();
        }

        private Button BuildButton(string name, string label, Vector2 corner, Action onClick)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Image), typeof(Button));
            var rt = go.GetComponent<RectTransform>();
            rt.SetParent(transform, false);
            rt.anchorMin = new Vector2(0f, 0f);
            rt.anchorMax = new Vector2(0f, 0f);
            rt.pivot = new Vector2(0f, 0f);
            rt.anchoredPosition = corner;
            rt.sizeDelta = new Vector2(280f, 72f);

            var img = go.GetComponent<Image>();
            img.sprite = buttonNormal;
            img.type = Image.Type.Sliced; // 9-slice so the gold corners stay crisp
            img.preserveAspect = false;
            // The plate art is ~565x164 native with a 44px gold corner; this button is only
            // ~72px tall, so render the 9-slice border smaller (higher multiplier = smaller
            // border) to keep the chamfered corners proportional and stop them overlapping.
            img.pixelsPerUnitMultiplier = 2.5f;

            var btn = go.GetComponent<Button>();
            btn.targetGraphic = img;
            if (buttonNormal != null || buttonHover != null || buttonPressed != null)
            {
                btn.transition = Selectable.Transition.SpriteSwap;
                var ss = new SpriteState
                {
                    highlightedSprite = buttonHover != null ? buttonHover : buttonNormal,
                    pressedSprite = buttonPressed != null ? buttonPressed : buttonNormal,
                    selectedSprite = buttonNormal,
                    disabledSprite = buttonNormal,
                };
                btn.spriteState = ss;
            }
            btn.onClick.AddListener(() => onClick());

            // Centred caption.
            var labelGo = new GameObject("Label", typeof(RectTransform));
            var labelRt = labelGo.GetComponent<RectTransform>();
            labelRt.SetParent(rt, false);
            labelRt.anchorMin = Vector2.zero;
            labelRt.anchorMax = Vector2.one;
            labelRt.offsetMin = new Vector2(12f, 8f);
            labelRt.offsetMax = new Vector2(-12f, -8f);

            var text = labelGo.AddComponent<TextMeshProUGUI>();
            if (font != null) text.font = font;
            text.alignment = TextAlignmentOptions.Center;
            text.enableAutoSizing = true;
            text.fontSizeMin = 14f;
            text.fontSizeMax = 28f;
            text.fontStyle = FontStyles.Bold;
            text.color = new Color(0.97f, 0.93f, 0.78f);
            text.raycastTarget = false;
            text.text = label;

            return btn;
        }

        private void OnWaitClicked()
        {
            if (input != null) input.WaitFromUI();
        }

        private void OnEndTurnClicked()
        {
            if (input != null) input.EndTurnFromUI();
        }

        private void RefreshActionMenu()
        {
            if (runner == null || !runner.Ready) return;

            bool playerActable = runner.CurrentTurn == Team.Player && !runner.IsBusy && !runner.IsOver;

            if (_statusLabel != null)
            {
                string status;
                if (runner.IsOver) status = "Battle over";
                else if (runner.CurrentTurn != Team.Player) status = "Enemy turn...";
                else if (runner.IsBusy) status = "Your turn (acting...)";
                else if (input != null && input.SelectedUnit != null) status = "Selected: " + input.SelectedUnit.Id;
                else status = "Your turn - click a unit";
                _statusLabel.text = status;
            }

            if (_waitButton != null)
                _waitButton.interactable = playerActable && input != null && input.CanControlSelected();
            if (_endTurnButton != null)
                _endTurnButton.interactable = playerActable;
        }

        // --- Damage floaters ------------------------------------------------------------

        private sealed class Floater
        {
            public RectTransform Rt;
            public TextMeshProUGUI Tmp;
            public Vector3 World;   // anchor in world space; drifts up over life
            public Color Base;      // colour at full opacity
            public float Born;      // Time.time when spawned
            public bool Active;
        }

        private void BuildFloaterRoot()
        {
            var go = new GameObject("Floaters", typeof(RectTransform));
            _floaterRoot = go.GetComponent<RectTransform>();
            _floaterRoot.SetParent(transform, false);
            _floaterRoot.anchorMin = Vector2.zero;
            _floaterRoot.anchorMax = Vector2.one;
            _floaterRoot.offsetMin = Vector2.zero;
            _floaterRoot.offsetMax = Vector2.zero;
            // Keep floaters under the banner so big numbers never cover the phase plate.
            _floaterRoot.SetAsFirstSibling();
        }

        /// <summary>Spawn a floating combat number at a world position. Called by the runner
        /// when damage/MISS resolves. Pools and reuses TMP labels.</summary>
        public void SpawnFloater(Vector3 world, string text, Color color)
        {
            Floater f = null;
            for (int i = 0; i < _floaters.Count; i++)
            {
                if (!_floaters[i].Active) { f = _floaters[i]; break; }
            }
            if (f == null)
            {
                var go = new GameObject("Floater", typeof(RectTransform));
                var rt = go.GetComponent<RectTransform>();
                rt.SetParent(_floaterRoot, false);
                rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f);
                rt.pivot = new Vector2(0.5f, 0.5f);
                rt.sizeDelta = new Vector2(160f, 40f);

                var tmp = go.AddComponent<TextMeshProUGUI>();
                if (font != null) tmp.font = font;
                tmp.alignment = TextAlignmentOptions.Center;
                tmp.fontSize = 34f;
                tmp.fontStyle = FontStyles.Bold;
                tmp.raycastTarget = false;
                tmp.textWrappingMode = TextWrappingModes.NoWrap;

                f = new Floater { Rt = rt, Tmp = tmp };
                _floaters.Add(f);
            }

            f.World = world;
            f.Base = color;
            f.Born = Time.time;
            f.Active = true;
            f.Tmp.text = text;
            f.Tmp.color = color;
            f.Rt.gameObject.SetActive(true);
        }

        private void UpdateFloaters()
        {
            if (_floaters.Count == 0) return;
            Camera cam = worldCamera != null ? worldCamera : Camera.main;
            if (cam == null) return;

            var canvasRect = (RectTransform)transform;
            for (int i = 0; i < _floaters.Count; i++)
            {
                Floater f = _floaters[i];
                if (!f.Active) continue;

                float age = Time.time - f.Born;
                if (age >= floaterLife)
                {
                    f.Active = false;
                    f.Rt.gameObject.SetActive(false);
                    continue;
                }

                float t = age / floaterLife;
                Vector3 wp = f.World + Vector3.up * (t * floaterRise);
                Vector3 sp = cam.WorldToScreenPoint(wp);
                if (sp.z < 0f) { f.Rt.gameObject.SetActive(false); continue; }
                f.Rt.gameObject.SetActive(true);

                // ScreenSpaceOverlay → pass a null camera to map screen px to canvas-local.
                if (RectTransformUtility.ScreenPointToLocalPointInRectangle(
                        canvasRect, sp, null, out Vector2 local))
                {
                    f.Rt.anchoredPosition = local;
                }

                float alpha = t < 0.6f ? 1f : 1f - (t - 0.6f) / 0.4f;
                Color c = f.Base; c.a = alpha;
                f.Tmp.color = c;
            }
        }

        // --- Unit HP bars ---------------------------------------------------------------

        private sealed class HpBar
        {
            public RectTransform Rt;      // container, repositioned over the unit each frame
            public Image Border;          // team-tinted frame behind the bar
            public Image Fill;            // coloured fill, width scaled by HP ratio
            public RectTransform FillRt;
        }

        private void BuildHpBarRoot()
        {
            var go = new GameObject("HpBars", typeof(RectTransform));
            _hpRoot = go.GetComponent<RectTransform>();
            _hpRoot.SetParent(transform, false);
            _hpRoot.anchorMin = Vector2.zero;
            _hpRoot.anchorMax = Vector2.one;
            _hpRoot.offsetMin = Vector2.zero;
            _hpRoot.offsetMax = Vector2.zero;
            // Sit behind the floaters and banner so numbers/plates always read on top.
            _hpRoot.SetAsFirstSibling();
        }

        private HpBar CreateHpBar()
        {
            var go = new GameObject("HpBar", typeof(RectTransform));
            var rt = go.GetComponent<RectTransform>();
            rt.SetParent(_hpRoot, false);
            rt.anchorMin = rt.anchorMax = new Vector2(0.5f, 0.5f);
            rt.pivot = new Vector2(0.5f, 0.5f);
            rt.sizeDelta = hpBarSize;

            // Border (slightly larger dark slab, tinted by team in UpdateHpBars).
            RectTransform borderRt = NewImage("Border", rt, new Color(0.05f, 0.05f, 0.07f, 0.95f));
            StretchOutset(borderRt, 2f);

            // Empty-bar background.
            RectTransform bgRt = NewImage("Bg", rt, new Color(0.16f, 0.05f, 0.05f, 0.95f));
            StretchOutset(bgRt, 0f);

            // Fill (anchored to the left edge; width scaled by HP ratio).
            RectTransform fillRt = NewImage("Fill", rt, new Color(0.30f, 0.85f, 0.30f, 1f));
            fillRt.anchorMin = new Vector2(0f, 0f);
            fillRt.anchorMax = new Vector2(0f, 1f);
            fillRt.pivot = new Vector2(0f, 0.5f);
            fillRt.anchoredPosition = Vector2.zero;
            fillRt.sizeDelta = new Vector2(hpBarSize.x, 0f);

            return new HpBar
            {
                Rt = rt,
                Border = borderRt.GetComponent<Image>(),
                Fill = fillRt.GetComponent<Image>(),
                FillRt = fillRt,
            };
        }

        private void UpdateHpBars()
        {
            if (runner == null) return;
            Camera cam = worldCamera != null ? worldCamera : Camera.main;
            if (cam == null) return;

            var canvasRect = (RectTransform)transform;
            foreach (UnitView view in runner.Views)
            {
                if (view == null) continue;
                Unit u = view.Unit;
                int shownHp = u != null ? runner.DisplayHpOf(u) : 0;
                // Drive visibility off the *displayed* HP, not the Domain's live IsAlive: during an
                // enemy phase a unit may already be dead in the model while its death swing hasn't
                // played yet, and we want the bar to linger until that hit lands.
                bool show = u != null && shownHp > 0 && view.gameObject.activeInHierarchy;

                if (!_hpBars.TryGetValue(view, out HpBar bar))
                {
                    if (!show) continue;
                    bar = CreateHpBar();
                    _hpBars[view] = bar;
                }

                if (!show) { bar.Rt.gameObject.SetActive(false); continue; }

                Vector3 wp = view.transform.position + Vector3.up * hpBarWorldOffset;
                Vector3 sp = cam.WorldToScreenPoint(wp);
                if (sp.z < 0f) { bar.Rt.gameObject.SetActive(false); continue; }
                bar.Rt.gameObject.SetActive(true);

                if (RectTransformUtility.ScreenPointToLocalPointInRectangle(
                        canvasRect, sp, null, out Vector2 local))
                {
                    bar.Rt.anchoredPosition = local;
                }

                float ratio = Mathf.Clamp01((float)shownHp / Mathf.Max(1, u.Stats.MaxHp));
                bar.FillRt.sizeDelta = new Vector2(hpBarSize.x * ratio, 0f);
                bar.Fill.color = HpColor(ratio);
                bar.Border.color = u.Team == Team.Player
                    ? new Color(0.15f, 0.25f, 0.5f, 0.95f)   // ally blue frame
                    : new Color(0.5f, 0.12f, 0.12f, 0.95f);  // enemy red frame
            }
        }

        /// <summary>Green when healthy, through yellow, to red when low.</summary>
        private static Color HpColor(float ratio)
        {
            if (ratio > 0.5f)
                return Color.Lerp(new Color(0.95f, 0.80f, 0.20f), new Color(0.30f, 0.85f, 0.30f),
                    (ratio - 0.5f) / 0.5f);
            return Color.Lerp(new Color(0.85f, 0.20f, 0.20f), new Color(0.95f, 0.80f, 0.20f),
                ratio / 0.5f);
        }

        // --- Unit info panel ------------------------------------------------------------

        private void BuildInfoPanel()
        {
            const float W = 560f, H = 216f, pad = 14f;
            float square = H - 2f * pad;
            float rxMin = (pad + square + pad) / W;
            float rxMax = (W - pad) / W;
            float ryMin = pad / H;
            float ryMax = (H - pad) / H;

            var go = new GameObject("UnitInfoPanel", typeof(RectTransform), typeof(Image));
            _infoPanel = go.GetComponent<RectTransform>();
            _infoPanel.SetParent(transform, false);
            _infoPanel.anchorMin = new Vector2(1f, 0f);
            _infoPanel.anchorMax = new Vector2(1f, 0f);
            _infoPanel.pivot = new Vector2(1f, 0f);
            _infoPanel.anchoredPosition = new Vector2(-24f, 24f);
            _infoPanel.sizeDelta = new Vector2(W, H);

            // Outer image = a thin team-tinted frame; a darker pane sits inset on top of it. No
            // pixel-art sprite is used (panelUnitInfo is left unwired for a future HD frame swap).
            _infoBorderImg = go.GetComponent<Image>();
            _infoBorderImg.sprite = RoundedSprite();
            _infoBorderImg.type = Image.Type.Sliced;
            _infoBorderImg.color = new Color(0.45f, 0.5f, 0.65f, 0.95f);
            _infoBorderImg.raycastTarget = false;

            RectTransform body = NewRoundedImage("Body", _infoPanel, new Color(0.09f, 0.10f, 0.13f, 0.95f), out _);
            StretchOutset(body, -3f);

            // Portrait placeholder (left square): team-tinted rounded frame + dark fill + the unit's
            // initial. Swap the fill for a real 立绘 sprite later without touching the right column.
            RectTransform portrait = NewRoundedImage("Portrait", _infoPanel,
                new Color(0.40f, 0.45f, 0.6f, 1f), out _infoPortraitImg);
            portrait.anchorMin = new Vector2(0f, 0.5f);
            portrait.anchorMax = new Vector2(0f, 0.5f);
            portrait.pivot = new Vector2(0f, 0.5f);
            portrait.anchoredPosition = new Vector2(pad, 0f);
            portrait.sizeDelta = new Vector2(square, square);

            RectTransform portraitFill = NewRoundedImage("PortraitFill", portrait,
                new Color(0.13f, 0.15f, 0.20f, 1f), out _);
            StretchOutset(portraitFill, -3f);
            _infoPortraitLetter = NewText("Initial", portraitFill, TextAlignmentOptions.Center, 96f, true);
            PlaceText(_infoPortraitLetter, Vector2.zero, Vector2.one);

            // Right column: name / divider / 4x2 stat grid / HP bar. Anchoring it to a clean rect we
            // own means every child below aligns by construction (no slot-guessing against baked art).
            var col = new GameObject("Right", typeof(RectTransform)).GetComponent<RectTransform>();
            col.SetParent(_infoPanel, false);
            col.anchorMin = new Vector2(rxMin, ryMin);
            col.anchorMax = new Vector2(rxMax, ryMax);
            col.offsetMin = col.offsetMax = Vector2.zero;

            _infoName = NewText("Name", col, TextAlignmentOptions.Left, 30f, true);
            PlaceText(_infoName, new Vector2(0f, 0.80f), new Vector2(1f, 1f));

            RectTransform rule = NewImage("Rule", col, new Color(1f, 1f, 1f, 0.12f));
            rule.anchorMin = new Vector2(0f, 0.765f);
            rule.anchorMax = new Vector2(1f, 0.765f);
            rule.pivot = new Vector2(0.5f, 0.5f);
            rule.sizeDelta = new Vector2(0f, 2f);

            var grid = new GameObject("Stats", typeof(RectTransform)).GetComponent<RectTransform>();
            grid.SetParent(col, false);
            grid.anchorMin = new Vector2(0f, 0.30f);
            grid.anchorMax = new Vector2(1f, 0.74f);
            grid.offsetMin = grid.offsetMax = Vector2.zero;
            _statCells = new TMP_Text[8];
            for (int i = 0; i < 8; i++)
            {
                int c = i % 4, row = i / 4;
                TMP_Text cell = NewText("S" + i, grid, TextAlignmentOptions.Left, 17f, false);
                var crt = (RectTransform)cell.transform;
                crt.anchorMin = new Vector2(c / 4f, 1f - (row + 1) / 2f);
                crt.anchorMax = new Vector2((c + 1) / 4f, 1f - row / 2f);
                crt.offsetMin = crt.offsetMax = Vector2.zero;
                _statCells[i] = cell;
            }

            var hpRow = new GameObject("HpRow", typeof(RectTransform)).GetComponent<RectTransform>();
            hpRow.SetParent(col, false);
            hpRow.anchorMin = new Vector2(0f, 0f);
            hpRow.anchorMax = new Vector2(1f, 0.24f);
            hpRow.offsetMin = hpRow.offsetMax = Vector2.zero;

            TMP_Text hpTag = NewText("HpTag", hpRow, TextAlignmentOptions.Left, 18f, true);
            PlaceText(hpTag, new Vector2(0f, 0f), new Vector2(0.13f, 1f));
            hpTag.text = "HP";

            RectTransform groove = NewRoundedImage("Groove", hpRow, new Color(0.05f, 0.05f, 0.07f, 0.9f), out _);
            groove.anchorMin = new Vector2(0.15f, 0.12f);
            groove.anchorMax = new Vector2(1f, 0.88f);
            groove.offsetMin = groove.offsetMax = Vector2.zero;

            _infoHpFill = NewRoundedImage("Fill", groove, new Color(0.30f, 0.85f, 0.30f, 1f), out _infoHpFillImg);
            _infoHpFill.anchorMin = new Vector2(0f, 0f);
            _infoHpFill.anchorMax = new Vector2(1f, 1f);
            _infoHpFill.offsetMin = _infoHpFill.offsetMax = Vector2.zero;

            _infoHp = NewText("HpNum", groove, TextAlignmentOptions.Center, 18f, true);
            PlaceText(_infoHp, Vector2.zero, Vector2.one);

            go.SetActive(false);
        }

        private void UpdateInfoPanel()
        {
            if (_infoPanel == null || input == null) return;

            Unit u = input.SelectedUnit != null ? input.SelectedUnit : input.HoveredUnit;
            int shownHp = u != null ? (runner != null ? runner.DisplayHpOf(u) : u.Hp) : 0;
            if (u == null || shownHp <= 0)
            {
                if (_infoPanel.gameObject.activeSelf) _infoPanel.gameObject.SetActive(false);
                return;
            }

            if (!_infoPanel.gameObject.activeSelf) _infoPanel.gameObject.SetActive(true);

            bool ally = u.Team == Team.Player;
            Color team = ally ? new Color(0.35f, 0.55f, 0.95f, 0.95f) : new Color(0.95f, 0.40f, 0.40f, 0.95f);
            _infoBorderImg.color = team;
            _infoPortraitImg.color = new Color(team.r, team.g, team.b, 1f);

            Stats s = u.Stats;
            string name = string.IsNullOrEmpty(u.DisplayName) ? "?" : u.DisplayName;
            _infoPortraitLetter.text = name.Substring(0, 1).ToUpperInvariant();
            _infoName.text = name + "   (" + (ally ? "Ally" : "Enemy") + ")";

            _statCells[0].text = "ATK " + s.Strength;
            _statCells[1].text = "DEF " + s.Defense;
            _statCells[2].text = "MAG " + s.Magic;
            _statCells[3].text = "RES " + s.Resist;
            _statCells[4].text = "HIT " + s.Accuracy;
            _statCells[5].text = "EVA " + s.Evade;
            _statCells[6].text = "CRT " + s.Crit;
            _statCells[7].text = "MOV " + s.Move;

            // HP reflects what the playback currently shows (lags the Domain during multi-hit phases).
            float ratio = Mathf.Clamp01((float)shownHp / Mathf.Max(1, s.MaxHp));
            _infoHpFill.anchorMax = new Vector2(ratio, 1f);
            _infoHpFillImg.color = HpColor(ratio);
            _infoHp.text = shownHp + " / " + s.MaxHp;
        }

        // --- Small UI builders shared by the HP bars / info panel -----------------------

        private static RectTransform NewImage(string name, RectTransform parent, Color color)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Image));
            var rt = go.GetComponent<RectTransform>();
            rt.SetParent(parent, false);
            var img = go.GetComponent<Image>();
            img.color = color;
            img.raycastTarget = false;
            return rt;
        }

        /// <summary>An <see cref="NewImage"/> that uses the shared rounded-rect 9-slice sprite so the
        /// (non-pixel) panel/portrait/HP-bar corners read soft and crisp at any resolution. The
        /// sprite is white, so <paramref name="color"/> tints it directly.</summary>
        private RectTransform NewRoundedImage(string name, RectTransform parent, Color color, out Image img)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Image));
            var rt = go.GetComponent<RectTransform>();
            rt.SetParent(parent, false);
            img = go.GetComponent<Image>();
            img.sprite = RoundedSprite();
            img.type = Image.Type.Sliced;
            img.color = color;
            img.raycastTarget = false;
            return rt;
        }

        /// <summary>A lazily-built white rounded-rect texture sliced with corner borders. Generated
        /// in code (no art asset) so the clean UI has zero dependency on imported sprites.</summary>
        private static Sprite _roundedSprite;
        private static Sprite RoundedSprite()
        {
            if (_roundedSprite != null) return _roundedSprite;
            const int r = 16;
            int size = r * 2 + 2;
            var tex = new Texture2D(size, size, TextureFormat.RGBA32, false)
            {
                filterMode = FilterMode.Bilinear,
                wrapMode = TextureWrapMode.Clamp,
            };
            var px = new Color32[size * size];
            for (int y = 0; y < size; y++)
            {
                for (int x = 0; x < size; x++)
                {
                    float dx = x < r ? r - x : (x > size - 1 - r ? x - (size - 1 - r) : 0f);
                    float dy = y < r ? r - y : (y > size - 1 - r ? y - (size - 1 - r) : 0f);
                    float d = Mathf.Sqrt(dx * dx + dy * dy);
                    float a = Mathf.Clamp01(r - d + 0.5f); // 1px anti-aliased edge
                    px[y * size + x] = new Color32(255, 255, 255, (byte)(a * 255f));
                }
            }
            tex.SetPixels32(px);
            tex.Apply();
            _roundedSprite = Sprite.Create(tex, new Rect(0f, 0f, size, size), new Vector2(0.5f, 0.5f),
                100f, 0, SpriteMeshType.FullRect, new Vector4(r, r, r, r));
            return _roundedSprite;
        }

        /// <summary>Stretch a rect to fill its parent, growing (outset>0) or shrinking it equally
        /// on every side.</summary>
        private static void StretchOutset(RectTransform rt, float outset)
        {
            rt.anchorMin = Vector2.zero;
            rt.anchorMax = Vector2.one;
            rt.offsetMin = new Vector2(-outset, -outset);
            rt.offsetMax = new Vector2(outset, outset);
        }

        private TMP_Text NewText(string name, RectTransform parent, TextAlignmentOptions align,
            float size, bool bold)
        {
            var go = new GameObject(name, typeof(RectTransform));
            var rt = go.GetComponent<RectTransform>();
            rt.SetParent(parent, false);
            var t = go.AddComponent<TextMeshProUGUI>();
            if (font != null) t.font = font;
            t.alignment = align;
            t.fontSize = size;
            t.fontStyle = bold ? FontStyles.Bold : FontStyles.Normal;
            t.color = new Color(0.97f, 0.93f, 0.78f);
            t.raycastTarget = false;
            t.textWrappingMode = TextWrappingModes.NoWrap;
            return t;
        }

        private static void PlaceText(TMP_Text t, Vector2 anchorMin, Vector2 anchorMax)
        {
            var rt = (RectTransform)t.transform;
            rt.anchorMin = anchorMin;
            rt.anchorMax = anchorMax;
            rt.offsetMin = Vector2.zero;
            rt.offsetMax = Vector2.zero;
        }
    }
}
