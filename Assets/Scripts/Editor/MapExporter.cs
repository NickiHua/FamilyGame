using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Tilemaps;

namespace FantacyCentry.EditorTools
{
    /// <summary>
    /// Reads the painted Stage1 Tilemap and exports a terrain-letter map JSON
    /// (same schema as scripts/map/demo_map.json) -> Assets/Art/Maps/stage1_map.json.
    /// Tile asset name -> letter: grass=G road=R dirt=I water=W bridge=D sand=S.
    /// Empty cells fall back to grass (G). Rows are written TOP-FIRST (matches BattleMap).
    /// Menu: Tools/Map/Export Stage1 JSON. Select a Tilemap first, or it finds the first one.
    /// </summary>
    public static class MapExporter
    {
        private static readonly Dictionary<string, char> NameToChar = new()
        {
            { "grass", 'G' }, { "road", 'R' }, { "dirt", 'I' },
            { "water", 'W' }, { "bridge", 'D' }, { "sand", 'S' },
        };

        [MenuItem("Tools/Map/Export Stage1 JSON")]
        public static void Export()
        {
            Tilemap tm = null;
            if (Selection.activeGameObject != null)
                tm = Selection.activeGameObject.GetComponent<Tilemap>();
            if (tm == null) tm = Object.FindAnyObjectByType<Tilemap>();
            if (tm == null) { Debug.LogError("[MapExporter] No Tilemap found."); return; }

            tm.CompressBounds();
            BoundsInt b = tm.cellBounds;
            int w = b.size.x, h = b.size.y;

            // Snap the tilemap so its bottom-left painted cell sits at world (0,0) =
            // logic cell (0,0). This keeps visual == logic with NO offset bookkeeping,
            // so gizmos / units / camera always line up no matter where it was dragged.
            Vector3 want = new Vector3(-b.xMin, -b.yMin, tm.transform.position.z);
            if (tm.transform.position != want)
            {
                Undo.RecordObject(tm.transform, "Align Stage1 to origin");
                tm.transform.position = want;
                EditorUtility.SetDirty(tm);
            }
            float originX = 0.5f, originY = 0.5f; // tile anchor is 0.5 → cell centre sits at +0.5

            var grid = new List<char[]>(h);
            for (int y = b.yMax - 1; y >= b.yMin; y--) // top-first
            {
                var row = new char[w];
                for (int x = b.xMin; x < b.xMax; x++)
                {
                    var t = tm.GetTile(new Vector3Int(x, y, 0));
                    char c = 'G';
                    if (t != null)
                    {
                        if (NameToChar.TryGetValue(t.name, out var mapped)) c = mapped;
                        else if (t.name.StartsWith("water")) c = 'W'; // water / water_base_1..4 / water_big
                    }
                    row[x - b.xMin] = c;
                }
                grid.Add(row);
            }

            // Stamp map obstacles (houses / props with a MapObstacle component) as
            // Building 'B' (non-walkable) so the export and the movement blocking stay in
            // sync — no more hand-edited JSON that gets wiped on the next export.
            int obstacleCount = 0, obstacleCells = 0;
            foreach (var ob in Object.FindObjectsByType<FantacyCentry.View.MapObstacle>(FindObjectsInactive.Exclude))
            {
                ob.GetFootprint(out int leftCell, out int bottomCell, out int fw, out int fh);
                obstacleCount++;
                for (int cy = bottomCell; cy < bottomCell + fh; cy++)
                {
                    if (cy < 0 || cy >= h) continue;
                    int r = (h - 1) - cy; // rows are TOP-FIRST, cell y=0 is the bottom
                    for (int cx = leftCell; cx < leftCell + fw; cx++)
                    {
                        if (cx < 0 || cx >= w) continue;
                        grid[r][cx] = 'B';
                        obstacleCells++;
                    }
                }
            }

            var rowsJson = string.Join(",\n    ", grid.ConvertAll(r => $"\"{new string(r)}\""));
            string json = "{\n  \"name\": \"stage1_village\",\n" +
                          $"  \"grid_w\": {w}, \"grid_h\": {h}, \"cell_px\": 64,\n" +
                          $"  \"origin_x\": {originX}, \"origin_y\": {originY},\n" +
                          "  \"legend\": \"G=Grass R=Road I=Dirt W=Water D=Bridge S=Sand B=Building(house,blocked) .=Grass\",\n" +
                          $"  \"base\": [\n    {rowsJson}\n  ]\n}}\n";
            string outPath = "Assets/Art/Maps/stage1_map.json";
            File.WriteAllText(outPath, json);
            AssetDatabase.Refresh();
            Debug.Log($"[MapExporter] wrote {outPath} ({w}x{h}); stamped {obstacleCount} obstacle(s) = {obstacleCells} 'B' cell(s)");
        }

        /// <summary>Removes BROKEN tiles from the Stage1 Tilemap: cells whose tile resolves to a
        /// null sprite (e.g. the old water.asset after its water.png was deleted). These render
        /// nothing but still occupy cells, so they silently inflate the export bounds (the map
        /// looked 77-wide because of invisible stray "water" far to the right).</summary>
        [MenuItem("Tools/Map/Clean Stage1 (remove broken/invisible tiles)")]
        public static void CleanStage1()
        {
            Tilemap tm = null;
            var go = GameObject.Find("Stage1");
            if (go != null) tm = go.GetComponent<Tilemap>();
            if (tm == null && Selection.activeGameObject != null)
                tm = Selection.activeGameObject.GetComponent<Tilemap>();
            if (tm == null) tm = Object.FindAnyObjectByType<Tilemap>();
            if (tm == null) { Debug.LogError("[CleanStage1] No Stage1 Tilemap found."); return; }

            tm.CompressBounds();
            var before = tm.cellBounds;
            Undo.RecordObject(tm, "Clean Stage1 broken tiles");
            int removed = 0;
            foreach (var pos in before.allPositionsWithin)
            {
                if (tm.GetTile(pos) != null && tm.GetSprite(pos) == null)
                {
                    tm.SetTile(pos, null);
                    removed++;
                }
            }
            tm.CompressBounds();
            EditorUtility.SetDirty(tm);
            Debug.Log($"[CleanStage1] removed {removed} broken (null-sprite) tile(s). " +
                      $"Bounds {before.size.x}x{before.size.y} -> {tm.cellBounds.size.x}x{tm.cellBounds.size.y}. " +
                      "Now re-run Export Stage1 JSON.");
        }
    }
}
