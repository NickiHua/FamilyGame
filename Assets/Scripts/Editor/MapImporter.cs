using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Tilemaps;
using FantacyCentry.View;

namespace FantacyCentry.EditorTools
{
    /// <summary>
    /// Reverse of <see cref="MapExporter"/>: reads Assets/Art/Maps/stage1_map.json and PAINTS a
    /// Tilemap to match it, so the hand-painted authoring canvas can be re-synced when the JSON
    /// has drifted ahead of the tilemap (e.g. edited elsewhere / via DualGrid experiments).
    ///
    /// Letter -> tile asset (Assets/Art/Tiles/*.asset):
    ///   G=grass  R=road  I=dirt  W=water  D=bridge  S=sand  B=grass (building footprint = grass under it)
    ///
    /// Menu: Tools/Map/Import Stage1 JSON to Tilemap. Select the target Tilemap first (defaults to a
    /// GameObject named "Stage1", else the first Tilemap found). Fills every cell so the bounds are
    /// exact, then snaps bottom-left cell to world (0,0) to match what Export expects.
    /// </summary>
    public static class MapImporter
    {
        private const string MapJsonPath = "Assets/Art/Maps/stage1_map.json";
        private const string TileDir = "Assets/Art/Tiles/";

        // Non-water letters. 'W' is handled specially with the 2x2 water_base set below
        // (there is no single water.png; the blue water is water_base_1..4).
        private static readonly Dictionary<char, string> CharToTile = new()
        {
            { 'G', "grass" }, { 'B', "grass" }, { 'S', "sand" },
            { 'I', "dirt" }, { 'R', "road" }, { 'D', "bridge" },
        };

        [MenuItem("Tools/Map/Import Stage1 JSON to Tilemap")]
        public static void Import()
        {
            var textAsset = AssetDatabase.LoadAssetAtPath<TextAsset>(MapJsonPath);
            if (textAsset == null) { Debug.LogError("[MapImporter] Missing " + MapJsonPath); return; }

            Tilemap tm = null;
            if (Selection.activeGameObject != null)
                tm = Selection.activeGameObject.GetComponent<Tilemap>();
            if (tm == null)
            {
                var go = GameObject.Find("Stage1");
                if (go != null) tm = go.GetComponent<Tilemap>();
            }
            if (tm == null) tm = Object.FindAnyObjectByType<Tilemap>();
            if (tm == null) { Debug.LogError("[MapImporter] No Tilemap found (select Stage1 first)."); return; }

            // Parse the JSON with the SAME MapGrid the builder uses (no ad-hoc parser).
            var tmpGo = new GameObject("~MapImporterTmp") { hideFlags = HideFlags.HideAndDontSave };
            var grid = tmpGo.AddComponent<MapGrid>();
            grid.mapJson = textAsset;
            grid.Parse();
            int w = grid.Width, h = grid.Height;
            var rows = grid.RowsTopFirst;
            if (w <= 0 || h <= 0 || rows == null || rows.Count == 0)
            {
                Object.DestroyImmediate(tmpGo);
                Debug.LogError("[MapImporter] Failed to parse map JSON.");
                return;
            }

            var tiles = new Dictionary<char, TileBase>();
            foreach (var kv in CharToTile)
            {
                var t = AssetDatabase.LoadAssetAtPath<TileBase>($"{TileDir}{kv.Value}.asset");
                if (t != null) tiles[kv.Key] = t;
                else Debug.LogWarning($"[MapImporter] Missing tile asset {TileDir}{kv.Value}.asset (letter '{kv.Key}').");
            }
            tiles.TryGetValue('G', out var fallback);

            // Water uses the 2x2 seamless blue set (water_base_1..4), picked by cell parity.
            var water = new TileBase[4];
            for (int i = 0; i < 4; i++)
                water[i] = AssetDatabase.LoadAssetAtPath<TileBase>($"{TileDir}water_base_{i + 1}.asset");

            Undo.RegisterFullObjectHierarchyUndo(tm.gameObject, "Import Stage1 JSON");
            tm.ClearAllTiles();
            for (int r = 0; r < h; r++)              // r == 0 is the TOP row
            {
                string row = rows[r];
                int y = h - 1 - r;                   // bottom-left cell -> (0,0)
                for (int x = 0; x < w && x < row.Length; x++)
                {
                    char c = row[x];
                    TileBase tile;
                    if (c == 'W')
                        tile = water[(x & 1) + ((y & 1) << 1)] ?? fallback;
                    else
                        tile = tiles.TryGetValue(c, out var t) ? t : fallback;
                    tm.SetTile(new Vector3Int(x, y, 0), tile);
                }
            }
            // Match Export's snap: bottom-left painted cell sits at world (0,0).
            tm.transform.position = new Vector3(0f, 0f, tm.transform.position.z);
            EditorUtility.SetDirty(tm);
            Object.DestroyImmediate(tmpGo);
            Debug.Log($"[MapImporter] Painted {w}x{h} onto '{tm.name}' from {MapJsonPath}.");
        }
    }
}
