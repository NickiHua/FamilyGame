using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using FantacyCentry.View;

namespace FantacyCentry.EditorTools
{
    /// <summary>
    /// Scatters decorative TREE and STONE sprites across the stage1 map, following the
    /// concept image (art/uiconcept/map/stage1): a forest down the LEFT side, a few trees
    /// on the right bank of the river and around the houses, and stones mostly in the
    /// BOTTOM-RIGHT plus a light sprinkle elsewhere.
    ///
    /// Every prop gets a <see cref="YSort"/> (layerBias 0) so one lower on screen draws in
    /// FRONT of one higher up (top-down occlusion). Props are purely visual (no
    /// MapObstacle) so they never change battle pathfinding/walkability.
    ///
    /// All props are parented under a single "ScatteredProps" object so the whole batch is
    /// easy to delete or regenerate. Re-run for a new random layout; Ctrl+Z undoes it.
    ///
    /// Menu: Tools/FantacyCentry/Scatter Props (Trees + Stones)  and  Clear Scattered Props.
    /// </summary>
    public static class PropScatterTool
    {
        private const string MapJsonPath = "Assets/Art/Maps/stage1_map.json";
        private const string TreeDir = "Assets/Art/Objects/Trees/";
        private const string StoneDir = "Assets/Art/Objects/Stones/";
        private const string ContainerName = "ScatteredProps";

        [MenuItem("Tools/FantacyCentry/Scatter Props (Trees + Stones)")]
        public static void Scatter()
        {
            MapGrid grid = GetOrCreateGrid();
            if (grid == null) return;

            Sprite[] trees = LoadSprites(TreeDir, "tree", 1, 8);
            Sprite[] stones = LoadSprites(StoneDir, "stone", 1, 30);
            if (trees.Length == 0 || stones.Length == 0)
            {
                Debug.LogError("[PropScatter] No tree/stone sprites found under " + TreeDir + " / " + StoneDir);
                return;
            }

            ClearInternal();

            var container = new GameObject(ContainerName);
            Undo.RegisterCreatedObjectUndo(container, "Scatter Props");

            // Fresh seed each run so re-running gives a new layout the player can re-roll.
            Random.InitState(System.Environment.TickCount);

            int w = grid.Width, h = grid.Height;
            var used = new HashSet<Vector2Int>();
            int treeCount = 0, stoneCount = 0;

            for (int y = 0; y < h; y++)
            for (int x = 0; x < w; x++)
            {
                var cell = new Vector2Int(x, y);
                char t = grid.TerrainAt(cell);
                bool grass = t == 'G';
                bool dirt = t == 'I';
                bool road = t == 'R';
                bool sand = t == 'S';
                if (t == '\0' || t == 'W' || t == 'B' || t == 'D') continue; // skip void/water/building/bridge

                // ---- TREES ----
                float treeProb = 0f;
                if (grass)
                {
                    if (x <= 5) treeProb = 0.60f;                    // dense left forest
                    else if (x == 6) treeProb = 0.30f;               // forest thinning to river
                    else if (x >= 8 && x <= 16) treeProb = 0.07f;    // scattered right bank
                    // a few clustered near the houses (house zone ~x10-15, y16-21)
                    if (x >= 8 && x <= 17 && y >= 13 && y <= 24) treeProb = Mathf.Max(treeProb, 0.12f);
                }

                if (grass && !used.Contains(cell) && Random.value < treeProb)
                {
                    if (PlaceTree(container.transform, grid, cell, trees)) { used.Add(cell); treeCount++; }
                    continue;
                }

                // ---- STONES ----
                float stoneProb = 0f;
                if (dirt || grass || road || sand)
                {
                    if (x >= 18 && y <= 8) stoneProb = 0.22f;        // heavy bottom-right
                    else stoneProb = 0.025f;                          // light sprinkle everywhere
                }

                if (!used.Contains(cell) && Random.value < stoneProb)
                {
                    if (PlaceStone(container.transform, grid, cell, stones)) { used.Add(cell); stoneCount++; }
                }
            }

            Selection.activeGameObject = container;
            Debug.Log($"[PropScatter] Placed {treeCount} trees + {stoneCount} stones under '{ContainerName}'. " +
                      "Re-run for a new layout, or Ctrl+Z to undo.");
        }

        [MenuItem("Tools/FantacyCentry/Clear Scattered Props")]
        public static void Clear()
        {
            ClearInternal();
            Debug.Log("[PropScatter] Cleared scattered props.");
        }

        // ------------------------------------------------------------------
        private static bool PlaceTree(Transform parent, MapGrid grid, Vector2Int cell, Sprite[] pool)
        {
            Sprite sprite = pool[Random.Range(0, pool.Length)];
            float targetW = Random.Range(0.7f, 1.1f);              // smaller
            return MakeProp("tree", sprite, grid, cell, targetW, 0f, parent) != null; // 0 jitter = exact tile
        }

        private static bool PlaceStone(Transform parent, MapGrid grid, Vector2Int cell, Sprite[] pool)
        {
            Sprite sprite = pool[Random.Range(0, pool.Length)];
            float targetW = Random.Range(0.45f, 0.95f);            // small
            return MakeProp("stone", sprite, grid, cell, targetW, 0.35f, parent) != null;
        }

        private static GameObject MakeProp(string kind, Sprite sprite, MapGrid grid,
                                           Vector2Int cell, float targetWidthUnits, float jitter,
                                           Transform parent)
        {
            float jx = Random.Range(-jitter, jitter);
            float jy = Random.Range(-jitter, jitter);
            float px = grid.Origin.x + cell.x + jx;
            float py = grid.Origin.y + cell.y + jy;

            // World size of the sprite (BottomCenter pivot: foot at py, canopy extends UP).
            float spriteW = sprite.bounds.size.x;
            float spriteH = sprite.bounds.size.y;
            float worldW = targetWidthUnits;
            float worldH = spriteW > 0f ? targetWidthUnits * (spriteH / spriteW) : targetWidthUnits;

            // Map rectangle in world units (ground tiles span cell +-0.5).
            float minX = grid.Origin.x - 0.5f;
            float maxX = grid.Origin.x + (grid.Width - 1) + 0.5f;
            float minY = grid.Origin.y - 0.5f;
            float maxY = grid.Origin.y + (grid.Height - 1) + 0.5f;

            // Reject if the sprite would spill outside the map rectangle (so nothing pokes into the void).
            if (px - worldW * 0.5f < minX || px + worldW * 0.5f > maxX ||
                py < minY || py + worldH > maxY)
                return null;

            var go = new GameObject($"{kind}_{cell.x}_{cell.y}");
            go.transform.SetParent(parent, false);
            go.transform.position = new Vector3(px, py, 0f);

            float scale = spriteW > 0f ? targetWidthUnits / spriteW : 1f;
            go.transform.localScale = new Vector3(scale, scale, 1f);

            var sr = go.AddComponent<SpriteRenderer>();
            sr.sprite = sprite;
            // Bake an edit-mode sorting order matching YSort's runtime formula so it looks
            // correct before Play (YSort keeps it updated at runtime).
            sr.sortingOrder = Mathf.RoundToInt(-py * 100f);

            var ys = go.AddComponent<YSort>();
            ys.layerBias = 0;
            ys.footOffset = 0f;

            return go;
        }

        // ------------------------------------------------------------------
        private static MapGrid GetOrCreateGrid()
        {
            var grid = Object.FindAnyObjectByType<MapGrid>();
            if (grid != null)
            {
                grid.Parse();
                return grid;
            }

            var json = AssetDatabase.LoadAssetAtPath<TextAsset>(MapJsonPath);
            if (json == null)
            {
                Debug.LogError("[PropScatter] MapGrid not in scene and " + MapJsonPath + " not found. " +
                               "Run Build Battle Scene / Build DualGrid Only first.");
                return null;
            }
            var go = new GameObject("MapGrid(temp-scatter)");
            grid = go.AddComponent<MapGrid>();
            grid.mapJson = json;
            grid.Parse();
            return grid;
        }

        private static Sprite[] LoadSprites(string dir, string prefix, int lo, int hi)
        {
            var list = new List<Sprite>();
            for (int i = lo; i <= hi; i++)
            {
                var s = AssetDatabase.LoadAssetAtPath<Sprite>($"{dir}{prefix}{i}.png");
                if (s != null) list.Add(s);
            }
            return list.ToArray();
        }

        private static void ClearInternal()
        {
            foreach (var go in Object.FindObjectsByType<GameObject>(FindObjectsInactive.Exclude))
            {
                if (go != null && go.name == ContainerName)
                    Undo.DestroyObjectImmediate(go);
            }
        }
    }
}
