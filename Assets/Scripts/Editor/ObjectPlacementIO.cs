using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using FantacyCentry.View;

namespace FantacyCentry.EditorTools
{
    /// <summary>
    /// Round-trip for hand-PLACED map objects (houses / trees / bridges / farmland / stones).
    ///
    /// WHY: the ground/tiles come from stage1_map.json (MapExporter), but decorative +
    /// blocking OBJECT sprites are dragged into the scene by hand. Screenshots can't tell
    /// the builder where they are. This tool reads their EXACT <see cref="Transform"/>
    /// (position/scale/flip) + YSort + <see cref="MapObstacle"/> footprint and writes them
    /// to Assets/Art/Maps/stage1_objects.json, so <see cref="BattleSceneBuilder"/> can
    /// rebuild the same layout from code — no more keeping a pile of loose objects around.
    ///
    /// An "object" = any active <see cref="SpriteRenderer"/> whose sprite asset lives under
    /// Assets/Art/Objects/ (this naturally excludes characters, ground tiles, UI, the map
    /// background), and that is NOT inside the generated DualGrid/GroundTiles hierarchy.
    ///
    /// Menus:
    ///   Tools/FantacyCentry/Export Placed Objects  → scene → JSON (non-destructive)
    ///   Tools/FantacyCentry/Build Placed Objects   → JSON → scene (consolidates the pile)
    /// </summary>
    public static class ObjectPlacementIO
    {
        public const string JsonPath = "Assets/Art/Maps/stage1_objects.json";
        private const string ObjectsRoot = "Assets/Art/Objects/";
        public const string ContainerName = "PlacedObjects";

        // Generated hierarchies whose object sprites must NOT be captured (they're rebuilt
        // by their own tools each time, e.g. the dual-grid bridge).
        private static readonly HashSet<string> ExcludedAncestors = new()
        {
            "DualGrid", "GroundTiles", "MapGrid",
        };

        [System.Serializable]
        public class Entry
        {
            public string name;
            public string sprite;   // AssetDatabase path to the sprite PNG
            public float x, y, z;   // world position
            public float sx, sy;    // localScale
            public bool flipX;
            public int order;       // edit-time sortingOrder (YSort overrides at runtime)

            public bool ysort;
            public int layerBias;
            public float footOffset;
            public int unitsToOrder;

            public bool obstacle;
            public int obW, obH;    // MapObstacle.size (cells; 0 = auto)
            public int obOffX, obOffY;
        }

        [System.Serializable]
        public class Data
        {
            public string name = "stage1_objects";
            public List<Entry> objects = new();
        }

        // ----------------------------------------------------------------- EXPORT

        [MenuItem("Tools/FantacyCentry/Export Placed Objects")]
        public static void Export()
        {
            var data = new Data();
            foreach (var sr in Object.FindObjectsByType<SpriteRenderer>(FindObjectsInactive.Exclude))
            {
                if (sr.sprite == null) continue;
                string spritePath = AssetDatabase.GetAssetPath(sr.sprite);
                if (string.IsNullOrEmpty(spritePath) || !spritePath.StartsWith(ObjectsRoot)) continue;
                if (HasExcludedAncestor(sr.transform)) continue;

                var t = sr.transform;
                var e = new Entry
                {
                    name = sr.gameObject.name,
                    sprite = spritePath,
                    x = t.position.x, y = t.position.y, z = t.position.z,
                    sx = t.localScale.x, sy = t.localScale.y,
                    flipX = sr.flipX,
                    order = sr.sortingOrder,
                };

                var ys = sr.GetComponent<YSort>();
                if (ys != null)
                {
                    e.ysort = true;
                    e.layerBias = ys.layerBias;
                    e.footOffset = ys.footOffset;
                    e.unitsToOrder = ys.unitsToOrder;
                }

                var ob = sr.GetComponent<MapObstacle>();
                if (ob != null)
                {
                    e.obstacle = true;
                    e.obW = ob.size.x; e.obH = ob.size.y;
                    e.obOffX = ob.offset.x; e.obOffY = ob.offset.y;
                }

                data.objects.Add(e);
            }

            data.objects.Sort((a, b) => a.name.CompareTo(b.name));
            File.WriteAllText(JsonPath, JsonUtility.ToJson(data, true));
            AssetDatabase.Refresh();
            Debug.Log($"[ObjectPlacementIO] exported {data.objects.Count} object(s) → {JsonPath}");
        }

        // ----------------------------------------------------------------- SNAP

        /// <summary>
        /// OFF by default: the shipped boundary look (camera CONFINED to the map, so the view
        /// never shows past the edge — the FE / Langrisser-M standard) makes per-object edge
        /// clipping unnecessary. Flip true only if we later pick a "raw black void" style where
        /// objects must be visually cut at the border. Kept wired so it's a one-line switch.
        /// </summary>
        private static readonly bool EnableEdgeClip = false;

        /// <summary>
        /// Tidies every placed object in one pass: (1) snaps X/Y to the nearest half-cell so a
        /// rough drag lands on clean coordinates, (2) makes sure it has a <see cref="YSort"/> so
        /// overlap is correct live in the editor (lower Y / lower X draws in front). Z + scale
        /// untouched. (Edge CLIP is opt-in via <see cref="EnableEdgeClip"/> — deferred to the
        /// camera system.) Undo-able. Run this before Export.
        /// </summary>
        [MenuItem("Tools/FantacyCentry/Snap Placed Objects")]
        public static void SnapToGrid()
        {
            const float step = 0.5f;
            bool hasRect = TryGetMapRect(out float left, out float right, out float bottom, out float top);
            bool clip = EnableEdgeClip && hasRect;
            if (clip) EnsureClipMask(left, right, bottom, top);
            else RemoveClipMask(); // clip disabled → tear down any stale mask so nothing stays hidden
            int n = 0;
            foreach (var sr in Object.FindObjectsByType<SpriteRenderer>(FindObjectsInactive.Exclude))
            {
                if (sr.sprite == null) continue;
                string spritePath = AssetDatabase.GetAssetPath(sr.sprite);
                if (string.IsNullOrEmpty(spritePath) || !spritePath.StartsWith(ObjectsRoot)) continue;
                if (HasExcludedAncestor(sr.transform)) continue;

                var t = sr.transform;
                Undo.RecordObject(t, "Snap Placed Objects");
                Undo.RecordObject(sr, "Snap Placed Objects");
                Vector3 p = t.position;
                p.x = Mathf.Round(p.x / step) * step;
                p.y = Mathf.Round(p.y / step) * step;
                t.position = p;

                // Always set the mask state explicitly so turning clip OFF actively RESETS any
                // VisibleInsideMask left by an earlier clip run (which would hide the object).
                sr.maskInteraction = clip ? SpriteMaskInteraction.VisibleInsideMask
                                          : SpriteMaskInteraction.None;
                if (sr.GetComponent<YSort>() == null)
                    Undo.AddComponent<YSort>(sr.gameObject); // bottom-centre foot → footOffset 0
                EditorUtility.SetDirty(sr);
                n++;
            }
            Debug.Log($"[ObjectPlacementIO] snapped {n} object(s){(clip ? " + edge-clipped" : " (mask cleared)")}.");
        }

        /// <summary>Emergency fix: removes the clip mask AND resets every placed object's
        /// Mask Interaction back to None. Use this if objects went invisible after an old
        /// "Snap + Clip" run (the SpriteMask hid them). Undo-able.</summary>
        [MenuItem("Tools/FantacyCentry/Clear Edge-Clip (restore hidden objects)")]
        public static void ClearEdgeClip()
        {
            RemoveClipMask();
            int n = 0;
            foreach (var sr in Object.FindObjectsByType<SpriteRenderer>(FindObjectsInactive.Exclude))
            {
                if (sr.sprite == null) continue;
                string spritePath = AssetDatabase.GetAssetPath(sr.sprite);
                if (string.IsNullOrEmpty(spritePath) || !spritePath.StartsWith(ObjectsRoot)) continue;
                if (HasExcludedAncestor(sr.transform)) continue;
                if (sr.maskInteraction == SpriteMaskInteraction.None) continue;
                Undo.RecordObject(sr, "Clear Edge-Clip");
                sr.maskInteraction = SpriteMaskInteraction.None;
                EditorUtility.SetDirty(sr);
                n++;
            }
            Debug.Log($"[ObjectPlacementIO] cleared edge-clip on {n} object(s) — hidden objects restored.");
        }

        /// <summary>Map world rectangle from the scene's MapGrid. Cell (0,0) centre = Origin,
        /// each cell is 1 world unit, so the rect is [Origin-0.5 .. Origin-0.5+size].</summary>
        private static bool TryGetMapRect(out float left, out float right, out float bottom, out float top)
        {
            left = right = bottom = top = 0f;
            var grid = Object.FindAnyObjectByType<MapGrid>();
            if (grid == null) return false;
            if (grid.Width == 0) grid.Parse();
            if (grid.Width == 0) return false;
            left = grid.Origin.x - 0.5f; right = left + grid.Width;
            bottom = grid.Origin.y - 0.5f; top = bottom + grid.Height;
            return true;
        }

        private const string MaskName = "MapClipMask";
        private const string MaskSpritePath = "Assets/_gen/clip_mask_white.png";

        /// <summary>Destroys any MapClipMask GameObject in the scene.</summary>
        private static void RemoveClipMask()
        {
            foreach (GameObject root in EditorSceneManager.GetActiveScene().GetRootGameObjects())
            {
                string bn = root.name;
                int paren = bn.IndexOf(" (");
                if (paren >= 0) bn = bn.Substring(0, paren);
                if (bn == MaskName) Object.DestroyImmediate(root);
            }
        }
        /// <summary>Creates (or repositions) a rectangular SpriteMask covering exactly the map
        /// rect. Objects set to VisibleInsideMask are clipped to it — anything hanging over the
        /// edge is masked away. Objects keep their real position (no clamp).</summary>
        private static void EnsureClipMask(float left, float right, float bottom, float top)
        {
            RemoveClipMask(); // never stack duplicates

            var sprite = LoadOrCreateMaskSprite();
            var go = new GameObject(MaskName);
            var mask = go.AddComponent<SpriteMask>();
            mask.sprite = sprite;
            mask.isCustomRangeActive = false;   // affect ALL sorting layers/orders
            go.transform.position = new Vector3((left + right) * 0.5f, (bottom + top) * 0.5f, 0f);
            go.transform.localScale = new Vector3(right - left, top - bottom, 1f); // 1-unit sprite → map size
        }

        /// <summary>A tiny solid-white square sprite (1 world unit) used as the clip mask shape.
        /// Lives under Assets/_gen (outside Assets/Art so the pixel-art postprocessor ignores it).</summary>
        private static Sprite LoadOrCreateMaskSprite()
        {
            var existing = AssetDatabase.LoadAssetAtPath<Sprite>(MaskSpritePath);
            if (existing != null) return existing;

            Directory.CreateDirectory(Path.GetDirectoryName(MaskSpritePath));
            var tex = new Texture2D(4, 4, TextureFormat.RGBA32, false);
            var px = new Color32[16];
            for (int i = 0; i < px.Length; i++) px[i] = new Color32(255, 255, 255, 255);
            tex.SetPixels32(px);
            tex.Apply();
            File.WriteAllBytes(MaskSpritePath, tex.EncodeToPNG());
            Object.DestroyImmediate(tex);
            AssetDatabase.ImportAsset(MaskSpritePath);

            var ti = (TextureImporter)AssetImporter.GetAtPath(MaskSpritePath);
            ti.textureType = TextureImporterType.Sprite;
            ti.spritePixelsPerUnit = 4;         // 4px sprite → 1 world unit; scaled to map size
            ti.filterMode = FilterMode.Point;
            ti.mipmapEnabled = false;
            ti.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Sprite>(MaskSpritePath);
        }

        // ----------------------------------------------------------------- RENAME

        /// <summary>Set false for uniform "object_N" names; true keeps a readable type
        /// prefix derived from the sprite ("tree_1" / "house_1"), still uniform + no " (n)".</summary>
        private static readonly bool RenameByType = true;

        /// <summary>
        /// Cleans up the ugly Unity " (1)" / " (2)" clone suffixes: renames every placed
        /// object to a tidy sequential name. Run BEFORE Export so the JSON stores clean
        /// names. Deterministic order (top-to-bottom, then left-to-right) so re-running is
        /// stable. Undo-able. Names are cosmetic only — the sprite path identifies the type.
        /// </summary>
        [MenuItem("Tools/FantacyCentry/Rename Placed Objects")]
        public static void RenameObjects()
        {
            var srs = new List<SpriteRenderer>();
            foreach (var sr in Object.FindObjectsByType<SpriteRenderer>(FindObjectsInactive.Exclude))
            {
                if (sr.sprite == null) continue;
                string spritePath = AssetDatabase.GetAssetPath(sr.sprite);
                if (string.IsNullOrEmpty(spritePath) || !spritePath.StartsWith(ObjectsRoot)) continue;
                if (HasExcludedAncestor(sr.transform)) continue;
                srs.Add(sr);
            }

            // Stable order: higher on the map first, then left-to-right.
            srs.Sort((a, b) =>
            {
                int cy = b.transform.position.y.CompareTo(a.transform.position.y);
                return cy != 0 ? cy : a.transform.position.x.CompareTo(b.transform.position.x);
            });

            var counters = new Dictionary<string, int>();
            int global = 0;
            foreach (var sr in srs)
            {
                Undo.RecordObject(sr.gameObject, "Rename Placed Objects");
                if (RenameByType)
                {
                    string type = TypeKeyFromSprite(AssetDatabase.GetAssetPath(sr.sprite));
                    counters.TryGetValue(type, out int idx);
                    idx++;
                    counters[type] = idx;
                    sr.gameObject.name = $"{type}_{idx}";
                }
                else
                {
                    sr.gameObject.name = $"object_{++global}";
                }
                EditorUtility.SetDirty(sr.gameObject);
            }
            Debug.Log($"[ObjectPlacementIO] renamed {srs.Count} object(s).");
        }

        /// <summary>Derives a short readable type key from a sprite path, e.g.
        /// ".../Objects/Trees/ref_green_tree_0.png" -> "tree", ".../Houses/village_house1.png"
        /// -> "house". Falls back to the parent folder name.</summary>
        private static string TypeKeyFromSprite(string spritePath)
        {
            string lower = spritePath.ToLowerInvariant();
            if (lower.Contains("/trees/") || lower.Contains("tree")) return "tree";
            if (lower.Contains("/houses/") || lower.Contains("house")) return "house";
            if (lower.Contains("/bridges/") || lower.Contains("bridge")) return "bridge";
            if (lower.Contains("farmland") || lower.Contains("/farm")) return "farm";
            if (lower.Contains("stone") || lower.Contains("rock")) return "stone";
            if (lower.Contains("fence")) return "fence";
            // fallback: the immediate parent folder, lower-cased & singular-ish.
            string dir = Path.GetFileName(Path.GetDirectoryName(spritePath) ?? "obj");
            return string.IsNullOrEmpty(dir) ? "obj" : dir.ToLowerInvariant();
        }

        // ----------------------------------------------------------------- BUILD

        [MenuItem("Tools/FantacyCentry/Build Placed Objects")]
        public static void BuildMenu()
        {
            int n = Build();
            if (n >= 0) Debug.Log($"[ObjectPlacementIO] rebuilt {n} object(s) from {JsonPath}");
        }

        /// <summary>Rebuilds placed objects from JSON. Returns count, or -1 if no JSON.
        /// Destroys the old container + any loose object sprites first (consolidation).</summary>
        public static int Build()
        {
            if (!File.Exists(JsonPath))
            {
                Debug.LogWarning($"[ObjectPlacementIO] no {JsonPath} — run Export Placed Objects first.");
                return -1;
            }

            var data = JsonUtility.FromJson<Data>(File.ReadAllText(JsonPath));
            if (data == null || data.objects == null) return -1;

            ClearExisting();
            bool hasRect = TryGetMapRect(out float left, out float right, out float bottom, out float top);
            bool clip = EnableEdgeClip && hasRect;
            if (clip) EnsureClipMask(left, right, bottom, top);

            var container = new GameObject(ContainerName);
            int built = 0;
            foreach (var e in data.objects)
            {
                var sprite = AssetDatabase.LoadAssetAtPath<Sprite>(e.sprite);
                if (sprite == null)
                {
                    Debug.LogWarning($"[ObjectPlacementIO] sprite missing, skipping '{e.name}': {e.sprite}");
                    continue;
                }

                var go = new GameObject(e.name);
                go.transform.SetParent(container.transform, worldPositionStays: true);
                go.transform.position = new Vector3(e.x, e.y, e.z);
                go.transform.localScale = new Vector3(e.sx, e.sy, 1f);

                var sr = go.AddComponent<SpriteRenderer>();
                sr.sprite = sprite;
                sr.flipX = e.flipX;
                sr.sortingOrder = e.order;

                if (e.ysort)
                {
                    var ys = go.AddComponent<YSort>();
                    ys.layerBias = e.layerBias;
                    ys.footOffset = e.footOffset;
                    ys.unitsToOrder = e.unitsToOrder > 0 ? e.unitsToOrder : 100;
                }

                if (e.obstacle)
                {
                    var ob = go.AddComponent<MapObstacle>();
                    ob.size = new Vector2Int(e.obW, e.obH);
                    ob.offset = new Vector2Int(e.obOffX, e.obOffY);
                }

                if (clip) sr.maskInteraction = SpriteMaskInteraction.VisibleInsideMask; // clip to map edge

                built++;
            }
            return built;
        }

        /// <summary>Removes the previous PlacedObjects container AND any loose object sprites
        /// (same filter as Export) so a rebuild never duplicates the hand-placed pile.</summary>
        public static void ClearExisting()
        {
            foreach (GameObject root in EditorSceneManager.GetActiveScene().GetRootGameObjects())
            {
                string baseName = root.name;
                int paren = baseName.IndexOf(" (");
                if (paren >= 0) baseName = baseName.Substring(0, paren);
                if (baseName == ContainerName || baseName == "ScatteredProps")
                {
                    Object.DestroyImmediate(root);
                    continue;
                }
            }

            // Loose object-sprite GameObjects that live at/near the scene root.
            var doomed = new List<GameObject>();
            foreach (var sr in Object.FindObjectsByType<SpriteRenderer>(FindObjectsInactive.Exclude))
            {
                if (sr.sprite == null) continue;
                string spritePath = AssetDatabase.GetAssetPath(sr.sprite);
                if (string.IsNullOrEmpty(spritePath) || !spritePath.StartsWith(ObjectsRoot)) continue;
                if (HasExcludedAncestor(sr.transform)) continue;
                doomed.Add(sr.gameObject);
            }
            foreach (var go in doomed)
                if (go != null) Object.DestroyImmediate(go);
        }

        private static bool HasExcludedAncestor(Transform t)
        {
            for (Transform p = t; p != null; p = p.parent)
            {
                string n = p.name;
                int paren = n.IndexOf(" (");
                if (paren >= 0) n = n.Substring(0, paren);
                if (ExcludedAncestors.Contains(n)) return true;
            }
            return false;
        }
    }
}
