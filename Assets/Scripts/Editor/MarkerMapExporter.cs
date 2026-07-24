using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Tilemaps;

namespace FantacyCentry.EditorTools
{
    /// <summary>
    /// Exports a MARKER tilemap (a Stage1 copy where object placeholders were painted with the
    /// marker tiles house_H/tree_T/stone_S/bridge_B) to Assets/Art/Maps/stage1_marker_map.json.
    /// This is a RENDER-ONLY layout for the Seedream redraw — it does NOT touch stage1_map.json
    /// (walkability/collider stays the real map's source of truth).
    ///
    /// Tile name -> letter:
    ///   terrain  grass=G road=R dirt=I water=W bridge=D sand=S
    ///   markers  house(_H)=H  tree(_T)=T  stone(_S)=K  bridge_B=P   (K/P avoid clashing with S/B/D)
    ///
    /// Menu: Tools/Map/Export Marker Map. Select the marker Tilemap first (defaults to a GameObject
    /// named "Stage1_marker", else the current selection, else the first Tilemap found).
    /// </summary>
    public static class MarkerMapExporter
    {
        private const string OutPath = "Assets/Art/Maps/stage1_marker_map.json";

        [MenuItem("Tools/Map/Export Marker Map")]
        public static void Export()
        {
            Tilemap tm = null;
            if (Selection.activeGameObject != null)
                tm = Selection.activeGameObject.GetComponent<Tilemap>();
            if (tm == null)
            {
                var byName = GameObject.Find("Stage1_marker");
                if (byName != null) tm = byName.GetComponent<Tilemap>();
            }
            if (tm == null) tm = Object.FindAnyObjectByType<Tilemap>();
            if (tm == null) { Debug.LogError("[MarkerMapExporter] No Tilemap found (select your marker tilemap)."); return; }

            tm.CompressBounds();
            BoundsInt b = tm.cellBounds;
            int w = b.size.x, h = b.size.y;

            var grid = new List<char[]>(h);
            for (int y = b.yMax - 1; y >= b.yMin; y--) // top-first rows
            {
                var row = new char[w];
                for (int x = b.xMin; x < b.xMax; x++)
                {
                    var t = tm.GetTile(new Vector3Int(x, y, 0));
                    row[x - b.xMin] = t != null ? Letter(t.name) : 'G';
                }
                grid.Add(row);
            }

            var rowsJson = string.Join(",\n    ", grid.ConvertAll(r => $"\"{new string(r)}\""));
            string json = "{\n  \"name\": \"stage1_marker\",\n" +
                          $"  \"grid_w\": {w}, \"grid_h\": {h}, \"cell_px\": 64,\n" +
                          "  \"origin_x\": 0.5, \"origin_y\": 0.5,\n" +
                          "  \"legend\": \"G=Grass R=Road I=Dirt W=Water D=Bridge S=Sand | H=house T=tree K=stone P=bridge(marker)\",\n" +
                          $"  \"base\": [\n    {rowsJson}\n  ]\n}}\n";

            var full = Path.Combine(Directory.GetCurrentDirectory(), OutPath);
            File.WriteAllText(full, json);
            AssetDatabase.ImportAsset(OutPath);
            Debug.Log($"[MarkerMapExporter] Exported {w}x{h} from '{tm.name}' -> {OutPath}");
        }

        private static char Letter(string name)
        {
            switch (name)
            {
                case "house": case "house_H": return 'H';
                case "tree": case "tree_T": return 'T';
                case "stone": case "stone_S": return 'K';
                case "bridge_B": return 'P';
                case "grass": return 'G';
                case "road": return 'R';
                case "dirt": return 'I';
                case "sand": return 'S';
                case "bridge": return 'D';
            }
            if (name.StartsWith("water")) return 'W';
            return 'G';
        }
    }
}
