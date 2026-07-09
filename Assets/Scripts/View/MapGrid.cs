using System.Collections.Generic;
using System.Text.RegularExpressions;
using UnityEngine;

namespace FantacyCentry.View
{
    /// <summary>
    /// Runtime logic grid for a demo battlefield. Parses the JSON produced by
    /// scripts/map/build_demo_map.py (the single source of truth that also drove the
    /// AI background art) and answers walkability queries by cell.
    ///
    /// Coordinate convention (matches <see cref="GridMover"/>, 1 unit = 1 cell):
    ///   cell (x, y) -> world (x, y). Cell (0,0) is the BOTTOM-LEFT.
    ///   JSON row 0 is the TOP of the image, so world y = (size-1 - jsonRow).
    ///   terrain at world cell (x, y) = base[size-1 - y][x].
    ///
    /// Walkability mirrors the Python PALETTE: G/R/D walkable, F/W/C/B/L blocked.
    /// (Hardcoded here because Unity's JsonUtility can't parse the string-keyed
    /// palette dict; the legal terrain letters are stable from our generator.)
    /// </summary>
    public class MapGrid : MonoBehaviour
    {
        [Tooltip("demo_map.json copied into Assets (Assets/Art/Maps/demo_map.json).")]
        public TextAsset mapJson;

        [Header("Debug")]
        [Tooltip("Draw red cells over blocked tiles (Scene view gizmos) to check the " +
                 "logic grid against the painted art.")]
        public bool drawBlockedGizmos = true;

        private const string Walkable = "GRDIS"; // Grass, Road, Bridge, Dirt, Sand (Forest/Water/Cliff blocked)

        private string[] _rows;   // indexed by JSON row (0 = top)

        /// <summary>Grid dimensions in cells. Square maps keep Width == Height == Size.</summary>
        public int Width { get; private set; }
        public int Height { get; private set; }
        public int Size => Width; // back-compat: callers that assumed a square map

        /// <summary>World position of cell (0,0)'s centre — matches the painted tilemap's offset.</summary>
        public Vector2 Origin { get; private set; }

        /// <summary>
        /// Terrain rows in TOP-FIRST order (JSON/image order), ready to feed
        /// <c>BattleMap.FromRows</c> so the View grid and Domain map share one source.
        /// Null until <see cref="Parse"/> has run (Awake does it automatically).
        /// </summary>
        public IReadOnlyList<string> RowsTopFirst => _rows;

        /// <summary>World position of the map centre (for placing the background sprite / camera).</summary>
        public Vector2 CenterWorld => Origin + new Vector2((Width - 1) * 0.5f, (Height - 1) * 0.5f);

        private void Awake() => Parse();

        /// <summary>Parse on demand so editor gizmos work without entering Play mode.</summary>
        private void EnsureParsed()
        {
            if (_rows == null) Parse();
        }

        [ContextMenu("Reparse JSON (refresh gizmos)")]
        public void Parse()
        {
            if (mapJson == null)
            {
                Debug.LogError("[MapGrid] mapJson is not assigned.");
                return;
            }

            string text = mapJson.text;

            // New exporter writes grid_w/grid_h; old maps used a square grid_size.
            Match wMatch = Regex.Match(text, "\"grid_w\"\\s*:\\s*(\\d+)");
            Match hMatch = Regex.Match(text, "\"grid_h\"\\s*:\\s*(\\d+)");
            Match sizeMatch = Regex.Match(text, "\"grid_size\"\\s*:\\s*(\\d+)");
            Width = wMatch.Success ? int.Parse(wMatch.Groups[1].Value)
                  : sizeMatch.Success ? int.Parse(sizeMatch.Groups[1].Value) : 0;
            Height = hMatch.Success ? int.Parse(hMatch.Groups[1].Value)
                   : sizeMatch.Success ? int.Parse(sizeMatch.Groups[1].Value) : 0;

            Match oxMatch = Regex.Match(text, "\"origin_x\"\\s*:\\s*(-?\\d+(?:\\.\\d+)?)");
            Match oyMatch = Regex.Match(text, "\"origin_y\"\\s*:\\s*(-?\\d+(?:\\.\\d+)?)");
            Origin = new Vector2(
                oxMatch.Success ? float.Parse(oxMatch.Groups[1].Value) : 0f,
                oyMatch.Success ? float.Parse(oyMatch.Groups[1].Value) : 0f);

            // The base rows are the only quoted strings made purely of terrain letters.
            var rows = new List<string>();
            foreach (Match m in Regex.Matches(text, "\"([GRFWCBLDIS]+)\""))
            {
                string row = m.Groups[1].Value;
                if (Width == 0 || row.Length == Width) rows.Add(row);
            }

            if (Width == 0 && rows.Count > 0) Width = rows[0].Length;
            if (Height == 0) Height = rows.Count;
            _rows = InferBridgeCells(rows.ToArray());

            if (_rows.Length != Height)
                Debug.LogWarning($"[MapGrid] Parsed {_rows.Length} rows but grid_h is {Height}.");
        }

        private string[] InferBridgeCells(string[] rows)
        {
            if (rows == null || rows.Length == 0 || Width <= 0) return rows;

            var chars = new char[rows.Length][];
            for (int i = 0; i < rows.Length; i++)
                chars[i] = rows[i].ToCharArray();

            for (int r = 0; r < chars.Length; r++)
            for (int x = 0; x < Width; x++)
            {
                if (chars[r][x] != 'W') continue;
                if (HasRoadAcrossWater(chars[r], x, -1) && HasRoadAcrossWater(chars[r], x, 1))
                    chars[r][x] = 'D';
            }

            var inferred = new string[rows.Length];
            for (int i = 0; i < rows.Length; i++)
                inferred[i] = new string(chars[i]);
            return inferred;
        }

        private static bool HasRoadAcrossWater(char[] row, int x, int step)
        {
            for (int nx = x + step; nx >= 0 && nx < row.Length; nx += step)
            {
                char c = row[nx];
                if (c == 'R' || c == 'D') return true;
                if (c == 'W') continue;
                return false;
            }
            return false;
        }

        public bool InBounds(Vector2Int cell) =>
            cell.x >= 0 && cell.x < Width && cell.y >= 0 && cell.y < Height;

        /// <summary>Terrain letter at a world cell, or '\0' if out of bounds.</summary>
        public char TerrainAt(Vector2Int cell)
        {
            if (_rows == null || !InBounds(cell)) return '\0';
            return _rows[Height - 1 - cell.y][cell.x];
        }

        public bool IsWalkable(Vector2Int cell)
        {
            char t = TerrainAt(cell);
            return t != '\0' && Walkable.IndexOf(t) >= 0;
        }

#if UNITY_EDITOR
        private void OnDrawGizmos()
        {
            if (!drawBlockedGizmos) return;
            EnsureParsed();
            if (_rows == null || Width <= 0) return;

            for (int y = 0; y < Height; y++)
            for (int x = 0; x < Width; x++)
            {
                var cell = new Vector2Int(x, y);
                if (IsWalkable(cell)) continue;
                Gizmos.color = new Color(1f, 0f, 0f, 0.35f);
                Gizmos.DrawCube(new Vector3(Origin.x + x, Origin.y + y, 0f), new Vector3(0.95f, 0.95f, 0f));
            }
        }
#endif
    }
}
