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

        [Header("Turn band colours (full-width translucent sweep)")]
        public Color bandColorPlayer = new Color(0.10f, 0.38f, 0.85f);
        public Color bandColorEnemy = new Color(0.82f, 0.16f, 0.16f);

        [Header("Action buttons (Assets/Art/UI/buttons/)")]
        public Sprite buttonNormal;
        public Sprite buttonHover;
        public Sprite buttonPressed;

        [Header("Command icons (Assets/Art/UI/icons/)")]
        public Sprite iconSkill;
        public Sprite iconMagic;
        public Sprite iconItem;
        public Sprite iconWait;

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

        [Tooltip("Peak opacity of the band (1 = solid). Lower for a more translucent overlay.")]
        [Range(0f, 1f)]
        public float peakAlpha = 0.6f;

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

        [Header("Unit info panel — HD gold frame (Assets/Art/UI/hd/panel_info_frame)")]
        [Tooltip("Wire panel_info_frame here. If left empty, a procedural rounded frame is used.")]
        public Sprite panelUnitInfo;

        [Tooltip("True when panelUnitInfo already has a SOLID opaque centre (e.g. panel_simple). " +
                 "Then no NavyFill backing layer is added — the panel fills its own interior.")]
        public bool panelSolidCenter;

        /// <summary>Maps a unit id (Unit.DisplayName) to its 立绘 bust. Units without an entry show a
        /// tinted silhouette placeholder, so each unit's panel shows its OWN portrait (or none) —
        /// never another unit's.</summary>
        [System.Serializable]
        public struct PortraitEntry { public string unitId; public Sprite sprite; }
        [Tooltip("Per-unit 立绘. unitId must match the spawn id (e.g. \"LuLi\"). Units not listed use a placeholder silhouette.")]
        public PortraitEntry[] portraits;

        private RectTransform _banner;
        private CanvasGroup _bannerGroup;
        private Image _bannerImage;
        private TMP_Text _bannerLabel;
        private Coroutine _bannerRoutine;

        // Action menu (status label + END TURN; per-unit commands live in the right-side panel).
        private TMP_Text _statusLabel;
        private Button _endTurnButton;

        // Right-side vertical command panel (攻击/技能/魔法/道具/待机).
        private enum Cmd { Skill, Magic, Item, Wait }
        private sealed class CommandRow
        {
            public Cmd cmd;
            public Button button;
            public Image rowBg;
            public Image icon;
            public TextMeshProUGUI label;
            public bool functional;
        }
        private RectTransform _cmdPanel;
        private CommandRow[] _cmdRows;

        // Damage-floater pool (parented under a full-rect, raycast-off container).
        private RectTransform _floaterRoot;
        private readonly List<Floater> _floaters = new();

        // World-following HP bars (one lazily-built bar per unit view).
        private RectTransform _hpRoot;
        private readonly Dictionary<UnitView, HpBar> _hpBars = new();

        // Unit info panel (bottom-centre, shifted left — Langrisser/梦战 classic). Shows the
        // selected or hovered unit. Clean, non-pixel look: built entirely from uGUI primitives so
        // the LAYOUT is ours (every field aligns by construction) rather than guessing slots baked
        // into a pixel-art sprite. A high-res gold frame + half-body 立绘 drop in later (Phase 2/3)
        // without moving any of this text.
        /// <summary>All the live widgets of one unit-info panel. The HUD owns one (bound to the
        /// selected/hovered unit); the battle-stage duel builds two more (attacker/defender) via
        /// <see cref="CreateInfoPanel"/> so they are the SAME panel, not a re-styled copy.</summary>
        public sealed class InfoPanel
        {
            public RectTransform Root;
            public Image BorderImg;        // outer frame, tinted by team
            public Image PortraitArt;      // real 立绘 bust (opaque); shown when the unit has one
            public Image PortraitSil;      // placeholder silhouette; shown when the unit has none
            public TMP_Text PortraitLetter; // placeholder initial until real 立绘 art exists
            public TMP_Text Name;
            public TMP_Text Lv;            // 等级 (placeholder until Unit.Level exists)
            public TMP_Text Job;           // 职业 (UnitClass)
            public TMP_Text Range;         // 射程 pill (MinRange..MaxRange)
            public TMP_Text Move;          // 移动 pill (Stats.Move)
            public TMP_Text[] StatCells;   // 2col x 3row grid: ATK/MAG, DEF/RES, HIT/CRT
            public TMP_Text Hp;
            public RectTransform HpFill;
            public Image HpFillImg;
            public TMP_Text Mp;
            public RectTransform MpFill;
            public Image MpFillImg;
        }

        private InfoPanel _info;   // the HUD's own panel (follows selection/hover)

        /// <summary>True while the turn banner is animating in/holding/out. The battle runner
        /// waits on this so neither side acts until the banner has cleared.</summary>
        public bool IsBannerPlaying { get; private set; }

        private void Awake()
        {
            BuildBanner();
            BuildActionMenu();
            BuildCommandPanel();
            BuildFloaterRoot();
            BuildHpBarRoot();
            _info = BuildInfoPanel(transform, new Vector2(0.5f, 0f), new Vector2(-150f, 22f), startActive: false);
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
            _bannerImage.color = isPlayer ? bandColorPlayer : bandColorEnemy;
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

            // Full-width band across the centre of the screen.
            _banner.anchorMin = new Vector2(0f, 0.5f);
            _banner.anchorMax = new Vector2(1f, 0.5f);
            _banner.pivot = new Vector2(0.5f, 0.5f);
            _banner.sizeDelta = new Vector2(0f, 132f); // width follows the screen, fixed height
            _banner.anchoredPosition = new Vector2(0f, 0f);

            _bannerGroup = go.GetComponent<CanvasGroup>();
            _bannerGroup.blocksRaycasts = false; // banner never eats clicks
            _bannerGroup.interactable = false;
            _bannerGroup.alpha = 0f;

            _bannerImage = go.GetComponent<Image>();
            _bannerImage.sprite = null;               // plain translucent colour band, no art
            _bannerImage.color = bandColorPlayer;
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
            _bannerLabel.fontStyle = FontStyles.Bold | FontStyles.Italic;
            _bannerLabel.color = new Color(0.98f, 0.98f, 0.98f);
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

            // END TURN stays a standalone plate bottom-left; the per-unit commands (攻击/待机/…)
            // live in the right-side command panel built separately.
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

        private void OnEndTurnClicked()
        {
            if (input != null) input.EndTurnFromUI();
        }

        // --- Right-side command panel ---------------------------------------

        private void BuildCommandPanel()
        {
            // Vertical command list reusing the char_panel gold frame as a TALL 9-slice plate
            // (gold corners kept, baked-navy middle stretched). One row per command: framed icon
            // on the left, label on the right, each sitting in a recessed dark slot.
            var defs = new (Cmd cmd, string label, Sprite icon, bool functional)[]
            {
                (Cmd.Skill,  "SKILL",  iconSkill,  false),
                (Cmd.Magic,  "MAGIC",  iconMagic,  false),
                (Cmd.Item,   "ITEM",   iconItem,   false),
                (Cmd.Wait,   "WAIT",   iconWait,   true),
            };

            const float rowH = 62f, rowGap = 8f, padX = 30f, padTop = 30f, padBot = 30f, width = 300f;
            float height = padTop + padBot + defs.Length * rowH + (defs.Length - 1) * rowGap;

            var go = new GameObject("CommandPanel", typeof(RectTransform), typeof(Image));
            _cmdPanel = go.GetComponent<RectTransform>();
            _cmdPanel.SetParent(transform, false);
            _cmdPanel.anchorMin = new Vector2(1f, 0.5f);
            _cmdPanel.anchorMax = new Vector2(1f, 0.5f);
            _cmdPanel.pivot = new Vector2(1f, 0.5f);
            _cmdPanel.anchoredPosition = new Vector2(-48f, 0f);
            _cmdPanel.sizeDelta = new Vector2(width, height);

            var bg = go.GetComponent<Image>();
            if (panelUnitInfo != null)
            {
                bg.sprite = panelUnitInfo;          // char_panel: gold frame + baked navy centre
                bg.type = Image.Type.Sliced;        // tall stretch keeps the gold corners intact
                bg.pixelsPerUnitMultiplier = 3.2f;  // render the 110px border at a sensible thickness
                bg.color = Color.white;
            }
            else
            {
                bg.color = new Color(0.09f, 0.11f, 0.16f, 0.96f);
            }
            bg.raycastTarget = false;               // only the rows capture clicks; gaps fall through to the map

            _cmdRows = new CommandRow[defs.Length];
            for (int i = 0; i < defs.Length; i++)
            {
                float top = -(padTop + i * (rowH + rowGap));
                _cmdRows[i] = BuildCommandRow(defs[i].cmd, defs[i].label, defs[i].icon,
                    defs[i].functional, padX, top, width - padX * 2f, rowH);
            }

            _cmdPanel.gameObject.SetActive(false);
        }

        private CommandRow BuildCommandRow(Cmd cmd, string label, Sprite icon, bool functional,
            float padX, float top, float rowW, float rowH)
        {
            var rowGo = new GameObject("Row_" + cmd, typeof(RectTransform), typeof(Image), typeof(Button));
            var rt = rowGo.GetComponent<RectTransform>();
            rt.SetParent(_cmdPanel, false);
            rt.anchorMin = new Vector2(0f, 1f);
            rt.anchorMax = new Vector2(0f, 1f);
            rt.pivot = new Vector2(0f, 1f);
            rt.anchoredPosition = new Vector2(padX, top);
            rt.sizeDelta = new Vector2(rowW, rowH);

            // Recessed slot: a white rounded sprite tinted by the Button's state colours, so the
            // normal state reads as a dark engraved inset and hover glows warm gold.
            var rowBg = rowGo.GetComponent<Image>();
            rowBg.sprite = RoundedSprite();
            rowBg.type = Image.Type.Sliced;
            rowBg.color = Color.white;

            var btn = rowGo.GetComponent<Button>();
            btn.targetGraphic = rowBg;
            btn.transition = Selectable.Transition.ColorTint;
            var cb = btn.colors;
            cb.normalColor = new Color(0.04f, 0.05f, 0.09f, 0.55f);      // dark recessed slot
            cb.highlightedColor = new Color(0.82f, 0.67f, 0.33f, 0.78f); // warm gold glow on hover
            cb.pressedColor = new Color(0.62f, 0.50f, 0.24f, 0.90f);
            cb.selectedColor = new Color(0.04f, 0.05f, 0.09f, 0.55f);
            cb.disabledColor = new Color(0.10f, 0.10f, 0.13f, 0.28f);
            cb.colorMultiplier = 1f;
            cb.fadeDuration = 0.08f;
            btn.colors = cb;

            // Framed icon on the left.
            float iconSize = rowH - 8f;
            var iconGo = new GameObject("Icon", typeof(RectTransform), typeof(Image));
            var iconRt = iconGo.GetComponent<RectTransform>();
            iconRt.SetParent(rt, false);
            iconRt.anchorMin = new Vector2(0f, 0.5f);
            iconRt.anchorMax = new Vector2(0f, 0.5f);
            iconRt.pivot = new Vector2(0f, 0.5f);
            iconRt.anchoredPosition = new Vector2(6f, 0f);
            iconRt.sizeDelta = new Vector2(iconSize, iconSize);
            var iconImg = iconGo.GetComponent<Image>();
            iconImg.sprite = icon;
            iconImg.preserveAspect = true;
            iconImg.raycastTarget = false;
            if (icon == null) iconImg.color = new Color(1f, 1f, 1f, 0f);

            // Label to the right of the icon.
            var labelGo = new GameObject("Label", typeof(RectTransform));
            var labelRt = labelGo.GetComponent<RectTransform>();
            labelRt.SetParent(rt, false);
            labelRt.anchorMin = new Vector2(0f, 0f);
            labelRt.anchorMax = new Vector2(1f, 1f);
            labelRt.offsetMin = new Vector2(iconSize + 18f, 0f);
            labelRt.offsetMax = new Vector2(-12f, 0f);
            var tmp = labelGo.AddComponent<TextMeshProUGUI>();
            if (font != null) tmp.font = font;
            tmp.alignment = TextAlignmentOptions.Left;
            tmp.fontSize = 30f;
            tmp.fontStyle = FontStyles.Bold;
            tmp.color = new Color(0.97f, 0.93f, 0.78f);
            tmp.raycastTarget = false;
            tmp.text = label;

            btn.onClick.AddListener(() => OnCommandClicked(cmd));

            return new CommandRow
            {
                cmd = cmd, button = btn, rowBg = rowBg, icon = iconImg, label = tmp, functional = functional,
            };
        }

        private void OnCommandClicked(Cmd cmd)
        {
            if (input == null) return;
            switch (cmd)
            {
                case Cmd.Wait: input.WaitFromUI(); break;
                default: break; // SKILL / MAGIC / ITEM — not implemented yet
            }
        }

        private void RefreshCommandRows(bool playerActable)
        {
            if (_cmdRows == null) return;
            foreach (var row in _cmdRows)
            {
                // MOVE / ATTACK / WAIT stay lit whenever the unit can act; picking one reveals its
                // range. SKILL / MAGIC / ITEM are greyed until implemented.
                bool on = row.functional && playerActable;
                row.button.interactable = on;
                row.label.color = on
                    ? new Color(0.97f, 0.93f, 0.78f)
                    : new Color(0.55f, 0.55f, 0.58f);
                if (row.icon.sprite != null)
                    row.icon.color = on ? Color.white : new Color(1f, 1f, 1f, 0.4f);
            }
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

            bool canControl = playerActable && input != null && input.CanControlSelected();
            if (_cmdPanel != null)
            {
                _cmdPanel.gameObject.SetActive(canControl);
                if (canControl) RefreshCommandRows(playerActable);
            }
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

        /// <summary>Build a unit-info panel under <paramref name="parent"/> at the given anchor.
        /// Returns the live widget handle; call <see cref="RefreshPanel"/> to fill it for a unit.</summary>
        private InfoPanel BuildInfoPanel(Transform parent, Vector2 anchor, Vector2 anchoredPos, bool startActive)
        {
            const float W = 780f, H = 200f, pad = 14f;
            var p = new InfoPanel();

            var go = new GameObject("UnitInfoPanel", typeof(RectTransform), typeof(Image));
            p.Root = go.GetComponent<RectTransform>();
            p.Root.SetParent(parent, false);
            // Bottom-centre, shifted left of centre (梦战 classic). Sits clear of the bottom-left
            // action buttons; the portrait window overflows upward (half-body pokes out).
            p.Root.anchorMin = anchor;
            p.Root.anchorMax = anchor;
            p.Root.pivot = new Vector2(0.5f, 0f);
            p.Root.anchoredPosition = anchoredPos;
            p.Root.sizeDelta = new Vector2(W, H);

            // Background. When the HD gold frame (panelUnitInfo) is wired in the Inspector we
            // draw it as-is: its native 1722x458 ≈ the panel's 780x200 ratio, so Image.Simple
            // scales it down crisply (Bilinear+mipmap) without distorting the corner filigree.
            // Otherwise fall back to the procedural rounded frame + a dark inner pane.
            p.BorderImg = go.GetComponent<Image>();
            bool hasHdFrame = panelUnitInfo != null;
            if (hasHdFrame)
            {
                // The HD frame is a GOLD border with a TRANSPARENT centre, so we layer:
                //   (1) NavyFill  — a deep-navy plate behind everything, filling the frame's inner
                //       hole and tucked slightly UNDER the gold rim (no transparent seam; navy also
                //       shows through the gaps in the corner filigree, like a backing plate).
                //   (2) GoldFrame — the panel_info_frame sprite drawn on top of the navy.
                // The root image itself is left transparent. Children added later (portrait, text)
                // draw on top of the gold, so they stay readable.
                p.BorderImg.color = new Color(0f, 0f, 0f, 0f);
                p.BorderImg.raycastTarget = false;

                // Navy plate (same deep navy as the original panel, RGB 23,33,50). Anchored to the
                // measured inner hole (x 0.020-0.981, y 0.041-0.958), expanded a touch so it tucks
                // under the gold rim on every side. Skipped when the panel already has a solid centre.
                if (!panelSolidCenter)
                {
                    RectTransform navy = NewImage("NavyFill", p.Root,
                        new Color(23f / 255f, 33f / 255f, 50f / 255f, 1f));
                    navy.anchorMin = new Vector2(0.014f, 0.030f);
                    navy.anchorMax = new Vector2(0.986f, 0.968f);
                    navy.offsetMin = navy.offsetMax = Vector2.zero;
                }

                // Gold frame on top of the navy.
                var goldGo = new GameObject("GoldFrame", typeof(RectTransform), typeof(Image));
                var goldRt = goldGo.GetComponent<RectTransform>();
                goldRt.SetParent(p.Root, false);
                goldRt.anchorMin = Vector2.zero;
                goldRt.anchorMax = Vector2.one;
                goldRt.offsetMin = goldRt.offsetMax = Vector2.zero;
                var gold = goldGo.GetComponent<Image>();
                gold.sprite = panelUnitInfo;
                gold.type = Image.Type.Sliced;          // 9-slice so the wide panel never stretches the gold corners
                gold.pixelsPerUnitMultiplier = 3.2f;    // render the 140px border at a sensible thickness
                gold.color = Color.white;     // show the gold's true colour, no team tint
                gold.raycastTarget = false;
            }
            else
            {
                p.BorderImg.sprite = RoundedSprite();
                p.BorderImg.type = Image.Type.Sliced;
                p.BorderImg.color = new Color(0.45f, 0.5f, 0.65f, 0.95f);
                RectTransform body = NewRoundedImage("Body", p.Root, new Color(0.09f, 0.10f, 0.13f, 0.95f), out _);
                StretchOutset(body, -3f);
                p.BorderImg.raycastTarget = false;
            }

            // --- Portrait / 立绘 (foreground bust). No hard frame: a real立绘 is an opaque
            // upper-body cut-out that sits IN FRONT of the navy, to the RIGHT of the left gold
            // corner (so the corner filigree stays visible), and OVERFLOWS above the gold top
            // edge (梦战 look). The window is ALWAYS built; which bust it shows is chosen per unit
            // in RefreshPanel (so each unit shows its OWN 立绘, or a placeholder — never another
            // unit's). Sized by a representative aspect so the right column start stays stable.
            float leftGold = hasHdFrame ? 96f : pad;       // clear the left corner flourish
            float portraitAspect = 1.1f;
            if (portraits != null)
                foreach (var e in portraits)
                    if (e.sprite != null) { portraitAspect = e.sprite.rect.width / e.sprite.rect.height; break; }
            float portraitH = 268f;
            float portraitW = portraitH * portraitAspect;
            RectTransform portrait = new GameObject("Portrait", typeof(RectTransform))
                .GetComponent<RectTransform>();
            portrait.SetParent(p.Root, false);
            portrait.anchorMin = new Vector2(0f, 0f);
            portrait.anchorMax = new Vector2(0f, 0f);
            portrait.pivot = new Vector2(0f, 0f);
            portrait.anchoredPosition = new Vector2(leftGold, pad);
            portrait.sizeDelta = new Vector2(portraitW, portraitH);

            // Placeholder bust silhouette — semi-transparent so it reads as a shadow, not a framed
            // box; team-tinted each frame. Shown only when the unit has no 立绘.
            RectTransform sil = NewRoundedImage("PortraitSilhouette", portrait,
                new Color(0.40f, 0.45f, 0.6f, 0.32f), out p.PortraitSil);
            sil.anchorMin = Vector2.zero;
            sil.anchorMax = Vector2.one;
            sil.offsetMin = sil.offsetMax = Vector2.zero;
            p.PortraitLetter = NewText("Initial", portrait, TextAlignmentOptions.Center, 120f, true);
            PlaceText(p.PortraitLetter, Vector2.zero, Vector2.one);

            // Real 立绘 layer (opaque bust), drawn on top of the placeholder, overflowing the top
            // gold edge. Hidden until a unit with art is shown.
            var pgo = new GameObject("PortraitArt", typeof(RectTransform), typeof(Image));
            var prt = pgo.GetComponent<RectTransform>();
            prt.SetParent(portrait, false);
            prt.anchorMin = Vector2.zero; prt.anchorMax = Vector2.one;
            prt.offsetMin = prt.offsetMax = Vector2.zero;
            p.PortraitArt = pgo.GetComponent<Image>();
            p.PortraitArt.type = Image.Type.Simple;
            p.PortraitArt.preserveAspect = true;
            p.PortraitArt.color = Color.white;
            p.PortraitArt.raycastTarget = false;
            pgo.SetActive(false);

            // --- Right column: name/Lv header + JOB + HP/MP bars + range/move pills + stat grid.
            // Anchored to a clean rect we own, so every child aligns by construction.
            // The HD frame's gold corner flourishes intrude ~104px at each corner (display size);
            // inset the right edge to clear the top/bottom-right corners. The portrait at the far
            // left intentionally sits in front of the left corners (it is a foreground 立绘).
            float cornerInset = hasHdFrame ? 104f : pad;
            float rxMin = (leftGold + portraitW + 12f) / W;
            float rxMax = (W - cornerInset) / W;
            // With the HD frame, pull content into the navy band so the name doesn't overflow the
            // gold top edge and the element row clears the gold bottom edge (~22px gold trim).
            float vInset = hasHdFrame ? 24f : pad;
            float ryMin = vInset / H;
            float ryMax = (H - vInset) / H;
            var col = new GameObject("Right", typeof(RectTransform)).GetComponent<RectTransform>();
            col.SetParent(p.Root, false);
            col.anchorMin = new Vector2(rxMin, ryMin);
            col.anchorMax = new Vector2(rxMax, ryMax);
            col.offsetMin = col.offsetMax = Vector2.zero;

            // Header band (y 0.82-1.0): name (left) + Lv (right).
            p.Name = NewText("Name", col, TextAlignmentOptions.Left, 28f, true);
            PlaceText(p.Name, new Vector2(0f, 0.82f), new Vector2(0.7f, 1f));
            p.Lv = NewText("Lv", col, TextAlignmentOptions.Right, 22f, true);
            PlaceText(p.Lv, new Vector2(0.7f, 0.82f), new Vector2(1f, 1f));

            RectTransform rule = NewImage("Rule", col, new Color(1f, 1f, 1f, 0.12f));
            rule.anchorMin = new Vector2(0f, 0.80f);
            rule.anchorMax = new Vector2(1f, 0.80f);
            rule.pivot = new Vector2(0.5f, 0.5f);
            rule.sizeDelta = new Vector2(0f, 2f);

            // Left half (x 0..0.5): JOB label, HP bar, MP bar, range/move pills.
            var left = new GameObject("LeftCol", typeof(RectTransform)).GetComponent<RectTransform>();
            left.SetParent(col, false);
            left.anchorMin = new Vector2(0f, 0f);
            left.anchorMax = new Vector2(0.5f, 0.78f);
            left.offsetMin = new Vector2(0f, 0f);
            left.offsetMax = new Vector2(-8f, 0f);

            // 梦战-style shaded sub-region grouping the HP/MP/pills block (below the raised JOB tab).
            if (hasHdFrame)
            {
                RectTransform leftShade = NewRoundedImage("LeftShade", left, new Color(0f, 0f, 0f, 0.28f), out _);
                leftShade.anchorMin = new Vector2(0f, 0f);
                leftShade.anchorMax = new Vector2(1f, 0.78f);
                leftShade.offsetMin = new Vector2(-2f, -2f);
                leftShade.offsetMax = new Vector2(2f, 2f);
            }

            // JOB raised plate (梦战: the JOB tab sits a notch higher than the bars, with a gold rim).
            RectTransform jobPlate = NewRoundedImage("JobPlate", left, new Color(0.16f, 0.14f, 0.09f, 0.96f), out _);
            jobPlate.anchorMin = new Vector2(0f, 0.80f);
            jobPlate.anchorMax = new Vector2(0.74f, 1.06f);
            jobPlate.offsetMin = jobPlate.offsetMax = Vector2.zero;
            RectTransform jobEdge = NewRoundedImage("JobEdge", jobPlate, new Color(0.62f, 0.50f, 0.24f, 1f), out _);
            StretchOutset(jobEdge, 2f);
            jobEdge.SetAsFirstSibling();
            p.Job = NewText("Job", jobPlate, TextAlignmentOptions.Center, 17f, true);
            PlaceText(p.Job, new Vector2(0.06f, 0f), new Vector2(1f, 1f));

            RectTransform hpBar = MakeBar(left, "HP", out p.HpFill, out p.HpFillImg, out p.Hp);
            hpBar.anchorMin = new Vector2(0f, 0.52f);
            hpBar.anchorMax = new Vector2(1f, 0.74f);
            hpBar.offsetMin = hpBar.offsetMax = Vector2.zero;

            RectTransform mpBar = MakeBar(left, "MP", out p.MpFill, out p.MpFillImg, out p.Mp);
            mpBar.anchorMin = new Vector2(0f, 0.26f);
            mpBar.anchorMax = new Vector2(1f, 0.48f);
            mpBar.offsetMin = mpBar.offsetMax = Vector2.zero;

            p.Range = MakePill(left, new Vector2(0f, 0f), new Vector2(0.48f, 0.20f));
            p.Move = MakePill(left, new Vector2(0.52f, 0f), new Vector2(1f, 0.20f));

            // Right half (x 0.5..1): 2col x 3row stat grid + element-icon placeholder row.
            var right = new GameObject("StatCol", typeof(RectTransform)).GetComponent<RectTransform>();
            right.SetParent(col, false);
            right.anchorMin = new Vector2(0.5f, 0f);
            right.anchorMax = new Vector2(1f, 0.78f);
            right.offsetMin = new Vector2(8f, 0f);
            right.offsetMax = new Vector2(0f, 0f);

            // 梦战-style shaded sub-region grouping the stat grid + element row.
            if (hasHdFrame)
            {
                RectTransform rightShade = NewRoundedImage("RightShade", right, new Color(0f, 0f, 0f, 0.28f), out _);
                rightShade.anchorMin = new Vector2(0f, 0f);
                rightShade.anchorMax = new Vector2(1f, 1f);
                rightShade.offsetMin = new Vector2(-2f, -2f);
                rightShade.offsetMax = new Vector2(2f, 2f);
            }

            var grid = new GameObject("Stats", typeof(RectTransform)).GetComponent<RectTransform>();
            grid.SetParent(right, false);
            grid.anchorMin = new Vector2(0f, 0.20f);
            grid.anchorMax = new Vector2(1f, 1f);
            grid.offsetMin = grid.offsetMax = Vector2.zero;
            p.StatCells = new TMP_Text[6];
            for (int i = 0; i < 6; i++)
            {
                int c = i % 2, row = i / 2;
                TMP_Text cell = NewText("S" + i, grid, TextAlignmentOptions.Left, 17f, false);
                var crt = (RectTransform)cell.transform;
                crt.anchorMin = new Vector2(c / 2f, 1f - (row + 1) / 3f);
                crt.anchorMax = new Vector2((c + 1) / 2f, 1f - row / 3f);
                crt.offsetMin = crt.offsetMax = Vector2.zero;
                p.StatCells[i] = cell;
            }

            // Element / skill icon row: dim placeholder squares (real icons in a later phase).
            var iconRow = new GameObject("Elements", typeof(RectTransform)).GetComponent<RectTransform>();
            iconRow.SetParent(right, false);
            iconRow.anchorMin = new Vector2(0f, 0f);
            iconRow.anchorMax = new Vector2(1f, 0.16f);
            iconRow.offsetMin = iconRow.offsetMax = Vector2.zero;
            for (int i = 0; i < 4; i++)
            {
                RectTransform sq = NewRoundedImage("Elem" + i, iconRow,
                    new Color(0.20f, 0.22f, 0.28f, 0.9f), out _);
                sq.anchorMin = sq.anchorMax = new Vector2(0f, 0.5f);
                sq.pivot = new Vector2(0f, 0.5f);
                sq.sizeDelta = new Vector2(20f, 20f);
                sq.anchoredPosition = new Vector2(i * 26f, 0f);
            }

            go.SetActive(startActive);
            return p;
        }

        /// <summary>Build a duel info panel (attacker→bottom-left, defender→bottom-right) under an
        /// arbitrary canvas, so the battle-stage overlay shows the SAME character panel as the HUD.</summary>
        public InfoPanel CreateInfoPanel(Transform parent, bool leftSide)
        {
            Vector2 anchor = new(leftSide ? 0f : 1f, 0f);
            // 780-wide panel: tuck it against the screen edge with a small margin.
            Vector2 pos = new(leftSide ? 400f : -400f, 20f);
            return BuildInfoPanel(parent, anchor, pos, startActive: true);
        }

        /// <summary>Build a labelled value bar (tag + dark groove + coloured fill + centred number)
        /// inside <paramref name="parent"/>. The fill scales via its anchorMax.x, set per-frame.</summary>
        private RectTransform MakeBar(RectTransform parent, string tag, out RectTransform fillRt,
            out Image fillImg, out TMP_Text numText)
        {
            var barGo = new GameObject(tag + "Bar", typeof(RectTransform));
            var bar = barGo.GetComponent<RectTransform>();
            bar.SetParent(parent, false);

            TMP_Text tagText = NewText("Tag", bar, TextAlignmentOptions.Left, 15f, true);
            PlaceText(tagText, new Vector2(0f, 0f), new Vector2(0.18f, 1f));
            tagText.text = tag;

            RectTransform groove = NewRoundedImage("Groove", bar, new Color(0.05f, 0.05f, 0.07f, 0.9f), out _);
            groove.anchorMin = new Vector2(0.20f, 0.10f);
            groove.anchorMax = new Vector2(1f, 0.90f);
            groove.offsetMin = groove.offsetMax = Vector2.zero;

            fillRt = NewRoundedImage("Fill", groove, new Color(0.30f, 0.85f, 0.30f, 1f), out fillImg);
            fillRt.anchorMin = new Vector2(0f, 0f);
            fillRt.anchorMax = new Vector2(1f, 1f);
            fillRt.offsetMin = fillRt.offsetMax = Vector2.zero;

            numText = NewText("Num", groove, TextAlignmentOptions.Center, 15f, true);
            PlaceText(numText, Vector2.zero, Vector2.one);

            return bar;
        }

        /// <summary>A small rounded chip with centred text (used for the 射程/移动 readouts).</summary>
        private TMP_Text MakePill(RectTransform parent, Vector2 anchorMin, Vector2 anchorMax)
        {
            RectTransform pill = NewRoundedImage("Pill", parent, new Color(0.16f, 0.18f, 0.24f, 0.95f), out _);
            pill.anchorMin = anchorMin;
            pill.anchorMax = anchorMax;
            pill.offsetMin = pill.offsetMax = Vector2.zero;
            TMP_Text t = NewText("PillText", pill, TextAlignmentOptions.Center, 15f, true);
            PlaceText(t, Vector2.zero, Vector2.one);
            return t;
        }

        private void UpdateInfoPanel()
        {
            if (_info == null || input == null) return;

            Unit u = input.SelectedUnit != null ? input.SelectedUnit : input.HoveredUnit;
            int shownHp = u != null ? (runner != null ? runner.DisplayHpOf(u) : u.Hp) : 0;
            if (u == null || shownHp <= 0)
            {
                if (_info.Root.gameObject.activeSelf) _info.Root.gameObject.SetActive(false);
                return;
            }

            if (!_info.Root.gameObject.activeSelf) _info.Root.gameObject.SetActive(true);
            PopulateInfoPanel(_info, u, shownHp);
        }

        /// <summary>Fill a duel info panel for <paramref name="u"/> (used by the battle-stage overlay).</summary>
        public void RefreshPanel(InfoPanel p, Unit u)
        {
            if (p == null || u == null) return;
            int shownHp = runner != null ? runner.DisplayHpOf(u) : u.Hp;
            PopulateInfoPanel(p, u, shownHp);
        }

        /// <summary>Write every widget of <paramref name="p"/> from unit <paramref name="u"/>.</summary>
        private void PopulateInfoPanel(InfoPanel p, Unit u, int shownHp)
        {
            bool ally = u.Team == Team.Player;
            Color team = ally ? new Color(0.35f, 0.55f, 0.95f, 0.95f) : new Color(0.95f, 0.40f, 0.40f, 0.95f);
            // The HD gold frame must render at its true colour (white tint, fully opaque); only the
            // procedural fallback frame gets the translucent team tint. Tinting the HD sprite would
            // dim the gold and, via the <1 alpha, let the map show through the navy.
            if (panelUnitInfo == null) p.BorderImg.color = team;

            Stats s = u.Stats;
            string name = string.IsNullOrEmpty(u.DisplayName) ? "?" : u.DisplayName;

            // Pick THIS unit's 立绘 (or none → placeholder). Each unit shows its own portrait.
            Sprite ps = PortraitFor(name);
            bool hasArt = ps != null;
            if (p.PortraitArt.gameObject.activeSelf != hasArt)
                p.PortraitArt.gameObject.SetActive(hasArt);
            if (p.PortraitSil.gameObject.activeSelf == hasArt)
                p.PortraitSil.gameObject.SetActive(!hasArt);
            if (p.PortraitLetter.gameObject.activeSelf == hasArt)
                p.PortraitLetter.gameObject.SetActive(!hasArt);
            if (hasArt)
            {
                if (p.PortraitArt.sprite != ps) p.PortraitArt.sprite = ps;
            }
            else
            {
                p.PortraitSil.color = new Color(team.r, team.g, team.b, 0.32f);
                p.PortraitLetter.text = name.Substring(0, 1).ToUpperInvariant();
            }
            p.Name.text = name;
            p.Lv.text = "Lv 1"; // placeholder until Unit.Level exists
            p.Job.text = JobName(u.Class);

            p.Range.text = "RNG " +
                (u.MinRange == u.MaxRange ? u.MaxRange.ToString() : u.MinRange + "-" + u.MaxRange);
            p.Move.text = "MOV " + s.Move;

            p.StatCells[0].text = "ATK " + s.Strength;
            p.StatCells[1].text = "MAG " + s.Magic;
            p.StatCells[2].text = "DEF " + s.Defense;
            p.StatCells[3].text = "RES " + s.Resist;
            p.StatCells[4].text = "HIT " + s.Accuracy;
            p.StatCells[5].text = "CRT " + s.Crit;

            // HP reflects what the playback currently shows (lags the Domain during multi-hit phases).
            float hpRatio = Mathf.Clamp01((float)shownHp / Mathf.Max(1, s.MaxHp));
            p.HpFill.anchorMax = new Vector2(hpRatio, 1f);
            p.HpFillImg.color = HpColor(hpRatio);
            p.Hp.text = shownHp + " / " + s.MaxHp;

            float mpRatio = Mathf.Clamp01((float)u.Mp / Mathf.Max(1, s.MaxMp));
            p.MpFill.anchorMax = new Vector2(mpRatio, 1f);
            p.MpFillImg.color = new Color(0.32f, 0.55f, 0.95f, 1f);
            p.Mp.text = u.Mp + " / " + s.MaxMp;
        }

        /// <summary>The 立绘 bust for a unit id, or null if none is wired (→ placeholder).</summary>
        public Sprite PortraitFor(string unitId)
        {
            if (portraits != null)
                foreach (var e in portraits)
                    if (e.sprite != null && e.unitId == unitId)
                        return e.sprite;
            return null;
        }

        /// <summary>Display label for a combat class (English for now; CJK font swap later).</summary>
        private static string JobName(UnitClass c) => c switch
        {
            UnitClass.Infantry => "Infantry",
            UnitClass.Cavalry => "Cavalry",
            UnitClass.Flying => "Flying",
            UnitClass.Armored => "Armored",
            UnitClass.Mage => "Mage",
            _ => c.ToString(),
        };

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
