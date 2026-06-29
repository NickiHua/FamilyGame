using System.Collections.Generic;
using System.IO;
using System.Text;
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

            var rows = new List<string>(h);
            for (int y = b.yMax - 1; y >= b.yMin; y--) // top-first
            {
                var sb = new StringBuilder(w);
                for (int x = b.xMin; x < b.xMax; x++)
                {
                    var t = tm.GetTile(new Vector3Int(x, y, 0));
                    char c = 'G';
                    if (t != null && NameToChar.TryGetValue(t.name, out var mapped)) c = mapped;
                    sb.Append(c);
                }
                rows.Add(sb.ToString());
            }

            var rowsJson = string.Join(",\n    ", rows.ConvertAll(r => $"\"{r}\""));
            string json = "{\n  \"name\": \"stage1_village\",\n" +
                          $"  \"grid_w\": {w}, \"grid_h\": {h}, \"cell_px\": 64,\n" +
                          $"  \"origin_x\": {originX}, \"origin_y\": {originY},\n" +
                          "  \"legend\": \"G=Grass R=Road I=Dirt W=Water D=Bridge S=Sand .=Grass\",\n" +
                          $"  \"base\": [\n    {rowsJson}\n  ]\n}}\n";
            string outPath = "Assets/Art/Maps/stage1_map.json";
            File.WriteAllText(outPath, json);
            AssetDatabase.Refresh();
            Debug.Log($"[MapExporter] wrote {outPath} ({w}x{h})");
        }
    }
}
