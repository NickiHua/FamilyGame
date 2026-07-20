using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem.UI;
using UnityEngine.UI;
using FantacyCentry.View;
using FantacyCentry.View.Battle;
using FantacyCentry.Domain.Units;

namespace FantacyCentry.EditorTools
{
    /// <summary>
    /// One-click playable battle: drops the map background + logic grid, spawns the three allies
    /// and two empire foes near the centre, and wires the <see cref="BattleRunner"/>,
    /// <see cref="RangeOverlay"/> and <see cref="BattleInputController"/>. Press Play, click an ally,
    /// click a blue cell to move, click a gold foe to attack, Space to end the turn.
    /// </summary>
    public static class BattleSceneBuilder
    {
        private const string MapPng = ""; // painted Tilemap is the visual; no legacy background
        private const string MapJson = "Assets/Art/Maps/stage1_map.json";
        private const string CharDir = "Assets/Art/Characters/";
        private const string RangeDir = "Assets/Art/UI/range/";
        private const string ButtonDir = "Assets/Art/UI/buttons/";
        private const string PanelDir = "Assets/Art/UI/panels/";
        private const string PortraitDir = "Assets/Art/UI/portraits/";
        private const string IconDir = "Assets/Art/UI/icons/";
        private const float CharacterScale = 0.6f;

        [MenuItem("Tools/FantacyCentry/Build Battle Scene")]
        private static void BuildBattleScene()
        {
            var bg = AssetDatabase.LoadAssetAtPath<Sprite>(MapPng);
            var json = AssetDatabase.LoadAssetAtPath<TextAsset>(MapJson);
            if (json == null)
            {
                Debug.LogError("[BattleSceneBuilder] Missing map json at " + MapJson);
                return;
            }

            CleanupPrevious();

            // --- Logic grid -------------------------------------------------
            var gridGo = new GameObject("MapGrid");
            var grid = gridGo.AddComponent<MapGrid>();
            grid.mapJson = json;
            grid.Parse();
            if (grid.Size <= 0)
            {
                Debug.LogError("[BattleSceneBuilder] Failed to parse map grid.");
                Object.DestroyImmediate(gridGo);
                return;
            }

            // --- Background (optional) -- painted Tilemap is the visual; only build the
            //     legacy rendered background if a sprite exists.
            if (bg != null)
            {
                var bgGo = new GameObject("MapBackground");
                var bgSr = bgGo.AddComponent<SpriteRenderer>();
                bgSr.sprite = bg;
                bgSr.sortingOrder = -5000;
                Vector2 c0 = grid.CenterWorld;
                bgGo.transform.position = new Vector3(c0.x, c0.y, 0f);
            }

            // The hand-painted Stage1 Tilemap is now just an editing canvas — the runtime
            // ground is the full dual-grid below (rebuilt from JSON). Disable any pre-existing
            // Tilemap renderers so the two bases don't double up and drift half a cell.
            foreach (var tmr in Object.FindObjectsByType<UnityEngine.Tilemaps.TilemapRenderer>(
                         FindObjectsInactive.Exclude))
                tmr.enabled = false;

            // --- Full dual-grid ground rebuilt from JSON (no hard base, blended edges) ---
            DualGridBuilder.Build(grid);

            // --- Map objects / props ---------------------------------------
            // Hand-placed objects (houses/trees/bridges/farmland) captured via
            // Tools/FantacyCentry/Export Placed Objects take priority: rebuild that exact
            // layout from stage1_objects.json. Only fall back to the procedural tree/stone
            // scatter when no such placement exists yet.
            if (ObjectPlacementIO.Build() < 0)
                PropScatterTool.Scatter(grid);

            // --- Overlay ----------------------------------------------------
            var overlayGo = new GameObject("RangeOverlay");
            var overlay = overlayGo.AddComponent<RangeOverlay>();
            overlay.moveTile = AssetDatabase.LoadAssetAtPath<Sprite>(RangeDir + "move_tile.png");
            overlay.attackTile = AssetDatabase.LoadAssetAtPath<Sprite>(RangeDir + "attack_tile.png");
            overlay.selectFrame = AssetDatabase.LoadAssetAtPath<Sprite>(RangeDir + "select_frame.png");

            // --- Runner -----------------------------------------------------
            var runnerGo = new GameObject("BattleRunner");
            var runner = runnerGo.AddComponent<BattleRunner>();
            runner.mapGrid = grid;
            runner.overlay = overlay;
            runner.spawns = BuildSpawns(grid);

            // --- Battle stage (side-view duel演出) ---------------------------
            var stageGo = new GameObject("BattleStageDirector");
            var stage = stageGo.AddComponent<BattleStageDirector>();
            stage.stageSprite = AssetDatabase.LoadAssetAtPath<Sprite>(
                "Assets/Art/Objects/BattleStages/grass_stage.png");
            runner.stageDirector = stage;
            runner.useBattleStage = true; // default: cut to the duel; toggle off on BattleRunner for fast combat
            stage.runner = runner;        // so the stage can settle HP on the panels at impact
            // Ability VFX frame banks (剑气 / 闪电 / 冰锥 / 治疗) played in the duel stage / on the map.
            stage.swordwaveFrames = LoadFrames("Assets/Art/VFX/swordwave/");
            stage.lightningFrames = LoadFrames("Assets/Art/VFX/lightning/");
            stage.icespikeFrames = LoadFrames("Assets/Art/VFX/icespike/");
            stage.healFrames = LoadFrames("Assets/Art/VFX/heal/");
            // Ranged normal-attack projectiles (弓箭手 arrow / 法师 fireball).
            stage.arrowSprite = AssetDatabase.LoadAssetAtPath<Sprite>("Assets/Art/Objects/Projectile/arrow_normal.png");
            stage.fireballFrames = LoadFrames("Assets/Art/VFX/fireball/");

            // --- Battle SFX -------------------------------------------------
            var audioGo = new GameObject("BattleAudio", typeof(AudioSource));
            var audio = audioGo.AddComponent<BattleAudio>();
            audio.source = audioGo.GetComponent<AudioSource>();
            audio.footsteps = LoadClips("Assets/Audio/footstep/", "kenney_step_grass_1", "kenney_step_grass_2", "kenney_step_grass_3");
            audio.slashes = LoadClips("Assets/Audio/slash/", "leohpaz_slash", "leohpaz_attack");
            audio.hits = LoadClips("Assets/Audio/hit/", "leohpaz_hit", "leohpaz_impact_flesh", "kenney_impact_heavy");
            audio.ui = LoadClips("Assets/Audio/ui/", "leohpaz_click_confirm", "kenney_click_soft");
            audio.magicFire = LoadClip("Assets/Audio/magic/leohpaz_fire.wav");
            audio.magicThunder = LoadClip("Assets/Audio/magic/leohpaz_thunder.wav");
            audio.magicIce = LoadClip("Assets/Audio/magic/leohpaz_ice.wav");
            audio.charge = LoadClip("Assets/Audio/magic/leohpaz_charge.wav");
            audio.heal = LoadClip("Assets/Audio/heal/leohpaz_heal.wav");

            // --- Input ------------------------------------------------------
            var input = runnerGo.AddComponent<BattleInputController>();
            input.runner = runner;
            input.overlay = overlay;
            input.worldCamera = Camera.main;
            input.worldOrigin = grid.Origin;

            // --- Canvas HUD -------------------------------------------------
            var canvasGo = new GameObject("BattleCanvas",
                typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            var canvas = canvasGo.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            var scaler = canvasGo.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1920f, 1080f);
            scaler.matchWidthOrHeight = 0.5f;

            var hud = canvasGo.AddComponent<BattleHud>();
            hud.runner = runner;
            hud.input = input;
            hud.worldCamera = Camera.main;
            hud.font = CnFontBuilder.EnsureFont();   // dynamic Chinese TMP font (CJK-capable)
            hud.buttonNormal = AssetDatabase.LoadAssetAtPath<Sprite>(ButtonDir + "button_normal.png");
            hud.buttonHover = AssetDatabase.LoadAssetAtPath<Sprite>(ButtonDir + "button_hover.png");
            hud.buttonPressed = AssetDatabase.LoadAssetAtPath<Sprite>(ButtonDir + "button_pressed.png");
            hud.panelUnitInfo = AssetDatabase.LoadAssetAtPath<Sprite>(PanelDir + "char_panel.png");
            hud.panelSolidCenter = true;   // char_panel.png has a solid navy centre baked in — no NavyFill
            hud.iconSkill = AssetDatabase.LoadAssetAtPath<Sprite>(IconDir + "icon_skill.png");
            hud.iconMagic = AssetDatabase.LoadAssetAtPath<Sprite>(IconDir + "icon_magic.png");
            hud.iconItem = AssetDatabase.LoadAssetAtPath<Sprite>(IconDir + "icon_item.png");
            hud.iconWait = AssetDatabase.LoadAssetAtPath<Sprite>(IconDir + "icon_wait.png");
            hud.iconStatus = AssetDatabase.LoadAssetAtPath<Sprite>(IconDir + "icon_status.png");
            // Per-unit 立绘: each character now has TWO assets in Assets/Art/UI/portraits/:
            //   <Id>_bust.png =胸像 (used in the small unit-info panel)
            //   <Id>_full.png = 全身立绘 (used in the full-screen character detail overlay)
            // Both keyed by unit id (== DisplayName); units without art fall back to a silhouette.
            string[] portraitIds = { "LuLi", "SuYao", "LingShuang", "EmpireArcher", "EmpireAxeSoldier", "EmpireCaptain" };
            var busts = new BattleHud.PortraitEntry[portraitIds.Length];
            var fulls = new BattleHud.PortraitEntry[portraitIds.Length];
            for (int pi = 0; pi < portraitIds.Length; pi++)
            {
                busts[pi] = new BattleHud.PortraitEntry
                {
                    unitId = portraitIds[pi],
                    sprite = AssetDatabase.LoadAssetAtPath<Sprite>(PortraitDir + portraitIds[pi] + "_bust.png"),
                };
                fulls[pi] = new BattleHud.PortraitEntry
                {
                    unitId = portraitIds[pi],
                    sprite = AssetDatabase.LoadAssetAtPath<Sprite>(PortraitDir + portraitIds[pi] + "_full.png"),
                };
            }
            hud.portraits = busts;
            hud.fullPortraits = fulls;
            runner.hud = hud; // gate the turn flow on the banner
            stage.mapHud = canvas; // hide the map HUD (END TURN / unit panel) during the duel
            stage.hud = hud;       // reuse the character panel frame + 立绘 for the duel forecast panels

            // EventSystem (new Input System module) so uGUI buttons work in later steps.
            if (Object.FindAnyObjectByType<EventSystem>() == null)
            {
                var esGo = new GameObject("EventSystem",
                    typeof(EventSystem), typeof(InputSystemUIInputModule));
            }

            // --- Camera -----------------------------------------------------
            int c = grid.Size / 2;
            if (Camera.main != null)
            {
                Camera.main.transform.position = new Vector3(grid.Origin.x + c, grid.Origin.y + c, -10f);
                Camera.main.orthographic = true;
                Camera.main.orthographicSize = 7f;
                var follow = Camera.main.GetComponent<CameraFollow>();
                if (follow != null) Object.DestroyImmediate(follow); // the map follow rig is map-scene only

                // Edge-scroll / arrow-key panning, clamped to the map extent so the player
                // can look around a battlefield larger than one screen.
                var pan = Camera.main.GetComponent<BattleCameraPan>();
                if (pan == null) pan = Camera.main.gameObject.AddComponent<BattleCameraPan>();
                pan.cam = Camera.main;
                pan.boundsMin = new Vector2(grid.Origin.x - 0.5f, grid.Origin.y - 0.5f);
                pan.boundsMax = new Vector2(grid.Origin.x + grid.Width - 0.5f, grid.Origin.y + grid.Height - 0.5f);
            }

            Selection.activeGameObject = runnerGo;
            EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
            Debug.Log("[BattleSceneBuilder] Battle scene assembled (" + runner.spawns.Count +
                      " units). Press Play: click an ally, move, attack, Space ends the turn.");
        }

        /// <summary>Load one AudioClip by exact asset path (null if missing).</summary>
        private static AudioClip LoadClip(string path) =>
            AssetDatabase.LoadAssetAtPath<AudioClip>(path);
        private static AudioClip[] LoadClips(string dir, params string[] names)
        {
            var list = new List<AudioClip>();
            foreach (string n in names)
            {
                AudioClip c = AssetDatabase.LoadAssetAtPath<AudioClip>(dir + n + ".ogg")
                              ?? AssetDatabase.LoadAssetAtPath<AudioClip>(dir + n + ".wav");
                if (c != null) list.Add(c);
            }
            return list.ToArray();
        }

        /// <summary>Load frame0.png, frame1.png, ... from a folder as an ordered Sprite bank.</summary>
        private static Sprite[] LoadFrames(string dir)
        {
            var list = new List<Sprite>();
            for (int i = 0; ; i++)
            {
                Sprite s = AssetDatabase.LoadAssetAtPath<Sprite>(dir + "frame" + i + ".png");
                if (s == null) break;
                list.Add(s);
            }
            return list.ToArray();
        }

        /// <summary>
        /// Remove objects from earlier builds (or the old demo scene) so each build starts clean:
        /// no duplicate MapGrid/background and no leftover, unbound character "dummies" that the
        /// player would click instead of the real battle units.
        /// </summary>
        private static void CleanupPrevious()
        {
            var doomedNames = new HashSet<string>
            {
                "MapGrid", "MapBackground", "RangeOverlay", "BattleRunner",
                "BattleCanvas", "EventSystem", "DualGrid", "GroundTiles",
                "LingShuang", "LuLi", "SuYao", "EmpireArcher", "EmpireAxeSoldier",
                "BattleStageDirector", "BattleAudio", "ScatteredProps",
                ObjectPlacementIO.ContainerName, "MapClipMask",
            };

            foreach (GameObject root in EditorSceneManager.GetActiveScene().GetRootGameObjects())
            {
                // Strip Unity's " (1)" / " (2)" clone suffix before matching.
                string baseName = root.name;
                int paren = baseName.IndexOf(" (");
                if (paren >= 0) baseName = baseName.Substring(0, paren);

                if (doomedNames.Contains(baseName))
                    Object.DestroyImmediate(root);
            }
        }

        private static List<BattleRunner.UnitSpawn> BuildSpawns(MapGrid grid)
        {
            int c = grid.Size / 2;
            var used = new HashSet<Vector2Int>();
            var list = new List<BattleRunner.UnitSpawn>();

            // NOTE: weapon base-hit (WeaponDef) isn't built yet, so HitChance = accuracy - evade.
            // Accuracy is set high here to fold in the future "武器基础命中" (e.g. sword 85) so melee
            // actually lands (~80%). Split it back out once WeaponDef exists. Magic ignores this (100%).
            // Allies on the left, foes on the right of centre.
            list.Add(Ally("LingShuang", Snap(grid, new Vector2Int(c - 3, c + 1), used),
                WeaponType.Sword, hp: 22, str: 11, def: 4, acc: 90, eva: 8, crit: 6, minR: 1, maxR: 1));
            list.Add(Ally("LuLi", Snap(grid, new Vector2Int(c - 3, c), used),
                WeaponType.Axe, hp: 26, str: 11, def: 6, acc: 85, eva: 4, crit: 4, minR: 1, maxR: 1));
            list.Add(Ally("SuYao", Snap(grid, new Vector2Int(c - 3, c - 1), used),
                WeaponType.Magic, hp: 16, str: 0, mag: 12, def: 2, res: 4, acc: 60, eva: 6, crit: 8, minR: 1, maxR: 2));

            list.Add(Foe("EmpireArcher", Snap(grid, new Vector2Int(c + 3, c - 1), used),
                WeaponType.Bow, hp: 18, str: 9, def: 3, acc: 85, eva: 6, crit: 6, minR: 1, maxR: 2));
            list.Add(Foe("EmpireAxeSoldier", Snap(grid, new Vector2Int(c + 3, c), used),
                WeaponType.Axe, hp: 24, str: 11, def: 4, acc: 82, eva: 4, crit: 5, minR: 1, maxR: 1));

            return list;
        }

        private static BattleRunner.UnitSpawn Ally(string id, Vector2Int cell, WeaponType weapon,
            int hp, int str = 0, int mag = 0, int def = 0, int res = 0,
            int acc = 0, int eva = 0, int crit = 0, int minR = 1, int maxR = 1)
            => Make(id, Team.Player, cell, weapon, hp, str, mag, def, res, acc, eva, crit, minR, maxR);

        private static BattleRunner.UnitSpawn Foe(string id, Vector2Int cell, WeaponType weapon,
            int hp, int str = 0, int mag = 0, int def = 0, int res = 0,
            int acc = 0, int eva = 0, int crit = 0, int minR = 1, int maxR = 1)
            => Make(id, Team.Enemy, cell, weapon, hp, str, mag, def, res, acc, eva, crit, minR, maxR);

        private static BattleRunner.UnitSpawn Make(string id, Team team, Vector2Int cell, WeaponType weapon,
            int hp, int str, int mag, int def, int res, int acc, int eva, int crit, int minR, int maxR)
        {
            return new BattleRunner.UnitSpawn
            {
                id = id,
                prefab = AssetDatabase.LoadAssetAtPath<GameObject>(CharDir + id + "/" + id + ".prefab"),
                team = team,
                cell = cell,
                weapon = weapon,
                maxHp = hp,
                strength = str,
                magic = mag,
                defense = def,
                resist = res,
                accuracy = acc,
                evade = eva,
                crit = crit,
                move = 4,
                minRange = minR,
                maxRange = maxR,
            };
        }

        /// <summary>Snap a preferred cell to the nearest free walkable cell (spiral search).</summary>
        private static Vector2Int Snap(MapGrid grid, Vector2Int preferred, HashSet<Vector2Int> used)
        {
            if (grid.IsWalkable(preferred) && used.Add(preferred)) return preferred;
            for (int r = 1; r < grid.Size; r++)
            {
                for (int dx = -r; dx <= r; dx++)
                for (int dy = -r; dy <= r; dy++)
                {
                    var cell = new Vector2Int(preferred.x + dx, preferred.y + dy);
                    if (grid.IsWalkable(cell) && !used.Contains(cell))
                    {
                        used.Add(cell);
                        return cell;
                    }
                }
            }
            used.Add(preferred);
            return preferred;
        }
    }
}
