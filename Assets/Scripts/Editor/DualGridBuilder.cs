using UnityEditor;
using UnityEngine;
using UnityEngine.Tilemaps;
using FantacyCentry.View;

namespace FantacyCentry.EditorTools
{
    /// <summary>
    /// Builds the visual map from the parsed JSON as a stack of dual-grid layers:
    ///   1) a flat per-cell BASE ground (water/under-bridge cells use a 2x2 water_base set),
    ///   2) for each terrain in ASCENDING priority, an organic dual-grid EDGE layer that
    ///      overhangs everything below it, then
    ///   3) the bridge on top.
    /// Every terrain shares ONE 16-tile dual set generated from the same 3 masks
    /// (scripts/tiles/gen_dual_tiles.py) filled with that terrain's texture.
    ///
    /// Priority (low -> high): Water(0) &lt; Road(1) &lt; Dirt(2) &lt; Grass(3). The higher
    /// terrain's edge always presses over the lower one; water is the base (no edge layer).
    /// ROAD is deliberately the LOWEST non-water terrain: roads are the through-lines that run
    /// past grass then dirt, so if road out-ranked dirt its edge would flip direction (grass eats
    /// road above, road eats dirt below) and jump 2x the overhang = a hard right-angle step at
    /// every grass->dirt transition. Making everything overhang the road keeps its edge crossing
    /// constant (no step); grass/dirt simply encroach organically on the path.
    /// </summary>
    public static class DualGridBuilder
    {
        private const string TileDir = "Assets/Art/Tiles/";
        private const string WaterSurfacePath = "Assets/Art/Maps/stage1_water_surface.png";
        private const string ShoreLandPath = "Assets/Art/Maps/stage1_shore_land.png";
        private const string Stage1OverlayPath = "Assets/Art/Maps/stage1_b.png";
        private const string BridgeSpritePath = "Assets/Art/Objects/Bridges/bridge_horizon_wood_128X256.png";

        // Terrain letter -> flat base tile asset (interior fill). Water/bridge cells are filled
        // specially with the 2x2 water_base set. 'B' (building) & 'S' (sand) render as grass.
        private static readonly System.Collections.Generic.Dictionary<char, string> BaseAsset = new()
        {
            { 'G', "grass" }, { 'B', "grass" }, { 'S', "grass" },
            { 'I', "dirt" }, { 'R', "road" },
        };

        // Dual-grid EDGE layers, drawn ASCENDING (higher priority = later = on top).
        private static readonly (string name, int priority, int sortingOrder)[] DualLayers =
        {
            ("road",  1, -4995),
            ("dirt",  2, -4990),
            ("grass", 3, -4985),
        };

        private static int Priority(char c) => c switch
        {
            'W' => 0, 'D' => 0,   // water & under-bridge sit at water level
            'R' => 1,             // road (lowest non-water: everything overhangs it so its edge never steps)
            'I' => 2,             // dirt
            _ => 3,               // grass / building / sand / unknown
        };

        public static void Build(MapGrid grid)
        {
            Cleanup();
            var root = new GameObject("DualGrid");
            root.AddComponent<UnityEngine.Grid>();

            BuildMapSprite(root.transform, grid, "water_surface", WaterSurfacePath, -5010);
            BuildMapSprite(root.transform, grid, "shore_land", ShoreLandPath, -5009);
            BuildBaseGround(root.transform, grid);
            foreach (var (name, priority, order) in DualLayers)
                BuildDualLayer(root.transform, grid, name, priority, order);
            BuildMapSprite(root.transform, grid, "stage1_ground_overlay", Stage1OverlayPath, -4981);
            BuildBridge(root.transform, grid);
            AssetDatabase.SaveAssets();
        }

        /// <summary>Rebuild ONLY the dual-grid ground from the Stage1 JSON, without touching the rest
        /// of the battle scene. Disables the hand-painted Tilemap so the flat base doesn't double up.
        /// Use this to preview map/tile/priority changes quickly.</summary>
        [MenuItem("Tools/FantacyCentry/Build DualGrid Only")]
        private static void BuildDualGridOnly()
        {
            const string mapJson = "Assets/Art/Maps/stage1_map.json";
            var json = AssetDatabase.LoadAssetAtPath<TextAsset>(mapJson);
            if (json == null) { Debug.LogError("[DualGridBuilder] Missing map json at " + mapJson); return; }

            var existing = GameObject.Find("MapGrid");
            var gridGo = existing != null ? existing : new GameObject("MapGrid");
            var grid = gridGo.GetComponent<MapGrid>() ?? gridGo.AddComponent<MapGrid>();
            grid.mapJson = json;
            grid.Parse();
            if (grid.Size <= 0) { Debug.LogError("[DualGridBuilder] Failed to parse map grid."); return; }

            // Disable any existing Tilemap renderers so the hand-painted authoring canvas and
            // previous generated layers don't double up. Build() destroys the old DualGrid before
            // creating the fresh runtime layers below.
            foreach (var tmr in Object.FindObjectsByType<TilemapRenderer>(FindObjectsInactive.Exclude))
                tmr.enabled = false;

            Build(grid);
            Debug.Log("[DualGridBuilder] DualGrid rebuilt from " + mapJson + " (" + grid.Size + " wide).");
        }

        /// <summary>Flat per-cell land base ground. Water and under-bridge cells are skipped because
        /// the map-sized baked water sprite sits underneath this Tilemap.</summary>
        private static void BuildBaseGround(Transform parent, MapGrid grid)
        {
            var byLetter = new System.Collections.Generic.Dictionary<char, TileBase>();
            foreach (var kv in BaseAsset)
            {
                var t = AssetDatabase.LoadAssetAtPath<TileBase>($"{TileDir}{kv.Value}.asset");
                if (t != null) byLetter[kv.Key] = t;
            }
            var grassVariants = LoadVariantTiles("grass_v1", "G", 5);
            var roadVariants = LoadVariantTiles("road_v1", "R", 5);

            var go = new GameObject("ground");
            go.transform.SetParent(parent, false);
            go.transform.localPosition = new Vector3(grid.Origin.x - 0.5f, grid.Origin.y - 0.5f, 0f);
            var tm = go.AddComponent<Tilemap>();
            var rend = go.AddComponent<TilemapRenderer>();
            rend.sortingOrder = -5000;

            byLetter.TryGetValue('G', out var grassFallback);
            byLetter.TryGetValue('R', out var roadFallback);
            for (int y = 0; y < grid.Height; y++)
            for (int x = 0; x < grid.Width; x++)
            {
                char c = grid.TerrainAt(new Vector2Int(x, y));
                TileBase tile;
                if (c == 'W' || c == 'D')
                    continue;
                if (c == 'G' || c == 'B' || c == 'S')
                    tile = PickWeightedVariant(grassVariants, x, y, 17, grassFallback);
                else if (c == 'R')
                    tile = PickWeightedVariant(roadVariants, x, y, 31, roadFallback != null ? roadFallback : grassFallback);
                else if (!byLetter.TryGetValue(c, out tile))
                    tile = grassFallback;
                if (tile != null) tm.SetTile(new Vector3Int(x, y, 0), tile);
            }
        }

        private static void BuildMapSprite(Transform parent, MapGrid grid, string name, string path, int order)
        {
            var sprite = LoadSprite(path);
            if (sprite == null)
            {
                Debug.LogWarning($"[DualGridBuilder] Missing map sprite {path}; '{name}' layer skipped.");
                return;
            }

            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = new Vector3(grid.CenterWorld.x, grid.CenterWorld.y, 0f);
            var sr = go.AddComponent<SpriteRenderer>();
            sr.sprite = sprite;
            sr.sortingOrder = order;
        }

        private static TileBase[] LoadVariantTiles(string subdir, string prefix, int count)
        {
            var tiles = new TileBase[count];
            for (int i = 0; i < count; i++)
                tiles[i] = GetOrCreateTile(subdir, $"{prefix}{i}");
            return tiles;
        }

        private static TileBase PickWeightedVariant(TileBase[] variants, int x, int y, int salt, TileBase fallback)
        {
            int index = WeightedVariantIndex(x, y, salt);
            return index >= 0 && index < variants.Length && variants[index] != null ? variants[index] : fallback;
        }

        private static int WeightedVariantIndex(int x, int y, int salt)
        {
            unchecked
            {
                uint h = (uint)(x * 73856093) ^ (uint)(y * 19349663) ^ (uint)(salt * 83492791);
                h ^= h >> 13;
                h *= 1274126177u;
                h ^= h >> 16;
                uint roll = h % 100u;
                if (roll < 60u) return 0;
                if (roll < 70u) return 1;
                if (roll < 80u) return 2;
                if (roll < 90u) return 3;
                return 4;
            }
        }

        /// <summary>One dual-grid EDGE layer for a terrain: half-cell offset, samples the 4 base
        /// cells at each corner, and draws the terrain's 16-tile dual set where the corner terrain's
        /// priority &gt;= this layer's priority (so it overhangs everything lower). Out-of-bounds
        /// samples are CLAMPED to the nearest edge cell so the map BORDER blends its terrain changes
        /// (grass pressing over road/water at the very edge) instead of a hard straight cut; bits
        /// 0/15 skipped (empty / full interior).</summary>
        private static void BuildDualLayer(Transform parent, MapGrid grid, string name, int priority, int order)
        {
            var tiles = new TileBase[16];
            for (int b = 1; b < 15; b++)
                tiles[b] = GetOrCreateTile($"{name}_dual", $"{b:00}");

            var go = new GameObject($"{name}_edges");
            go.transform.SetParent(parent, false);
            go.transform.localPosition = new Vector3(grid.Origin.x, grid.Origin.y, 0f);
            var tm = go.AddComponent<Tilemap>();
            var rend = go.AddComponent<TilemapRenderer>();
            rend.sortingOrder = order;

            int w = grid.Width, h = grid.Height;
            // Clamp out-of-bounds samples to the nearest edge cell so the map BORDER blends its
            // terrain transitions instead of a hard straight cut, without injecting a phantom
            // terrain from beyond the map.
            bool On(int x, int y)
            {
                x = Mathf.Clamp(x, 0, w - 1);
                y = Mathf.Clamp(y, 0, h - 1);
                return Priority(grid.TerrainAt(new Vector2Int(x, y))) >= priority;
            }

            // Border-ring dual tiles lap half a cell PAST the map rectangle. To keep a clean
            // rectangular edge we swap in HALF-CLIPPED tile variants (the overhanging half erased)
            // for the outer ring: left edge -> "L" clip, right -> "R", top -> "T", bottom -> "B".
            // Clamping makes border cells only ever use bits 3/12 (L/R) or 5/10 (T/B), so only those
            // clipped PNGs exist; anything else falls back to the full tile.
            TileBase Clip(int b, string dir)
            {
                var t = GetOrCreateTile($"{name}_dual", $"{b:00}{dir}");
                if (t == null)
                    Debug.LogWarning($"[DualGridBuilder] Missing clipped border tile {name}_dual/{b:00}{dir}.png " +
                                     "— border will overhang here. Run gen_dual_tiles.py then reimport.");
                return t != null ? t : tiles[b];
            }

            // Full ring incl. the outer border (x/y from -1). Uniform edges -> bits 0/15 -> skipped.
            for (int y = -1; y < h; y++)
            for (int x = -1; x < w; x++)
            {
                int bits = (On(x, y + 1) ? 1 : 0) | (On(x + 1, y + 1) ? 2 : 0)
                         | (On(x, y) ? 4 : 0) | (On(x + 1, y) ? 8 : 0);
                if (bits == 0 || bits == 15 || tiles[bits] == null) continue;

                TileBase tile = tiles[bits];
                // Unity tilemaps are Y-UP (cell y=0 at the bottom of the screen), so the outer
                // ring's bottom edge is y=-1 (overhangs downward) and the top edge is y=h-1
                // (overhangs upward). Clip the overhanging half accordingly: bottom edge -> erase
                // the PNG's bottom half ("B"), top edge -> erase the top half ("T"). (X is not
                // flipped: x=-1 is the left edge, x=w-1 the right.)
                if (x == -1) tile = Clip(bits, "L");
                else if (x == w - 1) tile = Clip(bits, "R");
                else if (y == -1) tile = Clip(bits, "B");
                else if (y == h - 1) tile = Clip(bits, "T");
                tm.SetTile(new Vector3Int(x, y, 0), tile);
            }
        }

        /// <summary>Load or (re)create a Tile asset wrapping Assets/Art/Tiles/[subdir/]file.png.</summary>
        private static TileBase GetOrCreateTile(string subdir, string file)
        {
            string baseDir = string.IsNullOrEmpty(subdir) ? "Assets/Art/Tiles" : $"Assets/Art/Tiles/{subdir}";
            string pngPath = $"{baseDir}/{file}.png";
            string assetPath = $"{baseDir}/t_{file}.asset";
            var sprite = AssetDatabase.LoadAssetAtPath<Sprite>(pngPath);
            // The clipped border PNGs (03L/05B/...) are generated externally; if Unity hasn't
            // imported one yet, LoadAssetAtPath returns null. Force-import it so a freshly generated
            // tile is picked up without the user having to manually Reimport the folder.
            if (sprite == null && System.IO.File.Exists(pngPath))
            {
                AssetDatabase.ImportAsset(pngPath, ImportAssetOptions.ForceSynchronousImport);
                sprite = AssetDatabase.LoadAssetAtPath<Sprite>(pngPath);
            }
            var existing = AssetDatabase.LoadAssetAtPath<Tile>(assetPath);
            if (sprite == null) return existing;
            if (existing == null)
            {
                existing = ScriptableObject.CreateInstance<Tile>();
                existing.sprite = sprite;
                AssetDatabase.CreateAsset(existing, assetPath);
            }
            else if (existing.sprite != sprite) { existing.sprite = sprite; EditorUtility.SetDirty(existing); }
            return existing;
        }

        /// <summary>Bridge objects on top of the ground (units still sort above them).</summary>
        private static void BuildBridge(Transform parent, MapGrid grid)
        {
            var bridge = LoadSprite(BridgeSpritePath);
            if (bridge == null) return;

            int w = grid.Width, h = grid.Height;
            var visited = new bool[w, h];
            for (int y = 0; y < h; y++)
            for (int x = 0; x < w; x++)
            {
                if (visited[x, y] || grid.TerrainAt(new Vector2Int(x, y)) != 'D') continue;
                BuildBridgeComponent(parent, grid, bridge, visited, x, y);
            }
        }

        private static void BuildBridgeComponent(Transform parent, MapGrid grid, Sprite bridge,
                                                 bool[,] visited, int startX, int startY)
        {
            int minX = startX, maxX = startX, minY = startY, maxY = startY;
            var open = new System.Collections.Generic.Queue<Vector2Int>();
            open.Enqueue(new Vector2Int(startX, startY));
            visited[startX, startY] = true;

            while (open.Count > 0)
            {
                Vector2Int c = open.Dequeue();
                minX = Mathf.Min(minX, c.x); maxX = Mathf.Max(maxX, c.x);
                minY = Mathf.Min(minY, c.y); maxY = Mathf.Max(maxY, c.y);
                TryBridgeNeighbor(grid, visited, open, c.x + 1, c.y);
                TryBridgeNeighbor(grid, visited, open, c.x - 1, c.y);
                TryBridgeNeighbor(grid, visited, open, c.x, c.y + 1);
                TryBridgeNeighbor(grid, visited, open, c.x, c.y - 1);
            }

            float centerX = grid.Origin.x + (minX + maxX) * 0.5f;
            float bottomY = grid.Origin.y + minY - 0.5f;
            var go = new GameObject($"bridge_{minX}_{minY}");
            go.transform.SetParent(parent, false);
            go.transform.position = new Vector3(centerX, bottomY, 0f);
            var sr = go.AddComponent<SpriteRenderer>();
            sr.sprite = bridge;
            sr.sortingOrder = -4980;
        }

        private static void TryBridgeNeighbor(MapGrid grid, bool[,] visited,
                                              System.Collections.Generic.Queue<Vector2Int> open,
                                              int x, int y)
        {
            if (x < 0 || x >= grid.Width || y < 0 || y >= grid.Height || visited[x, y]) return;
            if (grid.TerrainAt(new Vector2Int(x, y)) != 'D') return;
            visited[x, y] = true;
            open.Enqueue(new Vector2Int(x, y));
        }

        private static Sprite LoadSprite(string path)
        {
            var sprite = AssetDatabase.LoadAssetAtPath<Sprite>(path);
            if (sprite == null && System.IO.File.Exists(path))
            {
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
                sprite = AssetDatabase.LoadAssetAtPath<Sprite>(path);
            }
            return sprite;
        }

        public static void Cleanup()
        {
            var existing = GameObject.Find("DualGrid");
            if (existing != null) Object.DestroyImmediate(existing);
            var ground = GameObject.Find("GroundTiles");
            if (ground != null) Object.DestroyImmediate(ground);
        }
    }
}
