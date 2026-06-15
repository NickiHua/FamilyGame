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

        private const string Walkable = "GRD"; // Grass, Road, Bridge (Forest blocked)

        private string[] _rows;   // indexed by JSON row (0 = top)
        public int Size { get; private set; }

        /// <summary>World position of the map centre (for placing the background sprite / camera).</summary>
        public Vector2 CenterWorld => new((Size - 1) * 0.5f, (Size - 1) * 0.5f);

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

            Match sizeMatch = Regex.Match(text, "\"grid_size\"\\s*:\\s*(\\d+)");
            Size = sizeMatch.Success ? int.Parse(sizeMatch.Groups[1].Value) : 0;

            // The base rows are the only quoted strings made purely of terrain letters.
            var rows = new List<string>();
            foreach (Match m in Regex.Matches(text, "\"([GRFWCBLD]+)\""))
            {
                string row = m.Groups[1].Value;
                if (Size == 0 || row.Length == Size) rows.Add(row);
            }

            if (Size == 0 && rows.Count > 0) Size = rows[0].Length;
            _rows = rows.ToArray();

            if (_rows.Length != Size)
                Debug.LogWarning($"[MapGrid] Parsed {_rows.Length} rows but grid_size is {Size}.");
        }

        public bool InBounds(Vector2Int cell) =>
            cell.x >= 0 && cell.x < Size && cell.y >= 0 && cell.y < Size;

        /// <summary>Terrain letter at a world cell, or '\0' if out of bounds.</summary>
        public char TerrainAt(Vector2Int cell)
        {
            if (_rows == null || !InBounds(cell)) return '\0';
            return _rows[Size - 1 - cell.y][cell.x];
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
            if (_rows == null || Size <= 0) return;

            for (int y = 0; y < Size; y++)
            for (int x = 0; x < Size; x++)
            {
                var cell = new Vector2Int(x, y);
                if (IsWalkable(cell)) continue;
                Gizmos.color = new Color(1f, 0f, 0f, 0.35f);
                Gizmos.DrawCube(new Vector3(x, y, 0f), new Vector3(0.95f, 0.95f, 0f));
            }
        }
#endif
    }
}
