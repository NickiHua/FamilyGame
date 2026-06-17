using System;
using System.Collections.Generic;

namespace FantacyCentry.Domain.Grid
{
    /// <summary>
    /// Pure-logic battle map: a rectangular grid of <see cref="TerrainType"/>.
    /// This is the Domain truth source for walkability and movement cost; it knows nothing
    /// about pixels, sprites or the background image. It is built from the same letter rows
    /// the map pipeline produces (and the View-side MapGrid parses), so art and logic cannot drift.
    /// </summary>
    public sealed class BattleMap
    {
        private readonly TerrainType[,] _terrain; // [x, y], (0,0) bottom-left

        public int Width { get; }
        public int Height { get; }

        /// <summary>The active battle arena (spec §4.8). Defaults to the whole map.</summary>
        public GridRect Bounds { get; }

        public BattleMap(TerrainType[,] terrain, GridRect? bounds = null)
        {
            _terrain = terrain ?? throw new ArgumentNullException(nameof(terrain));
            Width = terrain.GetLength(0);
            Height = terrain.GetLength(1);
            Bounds = bounds ?? GridRect.Full(Width, Height);
        }

        /// <summary>
        /// Build from terrain-letter rows. Rows are given TOP-FIRST (JSON/image order), so
        /// the last row is the bottom of the world — matching the View-side MapGrid convention
        /// (terrain at world (x,y) = rows[height-1-y][x]).
        /// </summary>
        public static BattleMap FromRows(IReadOnlyList<string> rowsTopFirst, GridRect? bounds = null)
        {
            if (rowsTopFirst == null || rowsTopFirst.Count == 0)
                throw new ArgumentException("rows must be non-empty", nameof(rowsTopFirst));

            int height = rowsTopFirst.Count;
            int width = rowsTopFirst[0].Length;
            var terrain = new TerrainType[width, height];

            for (int row = 0; row < height; row++)
            {
                string line = rowsTopFirst[row];
                if (line.Length != width)
                    throw new ArgumentException(
                        $"row {row} has length {line.Length}, expected {width} (all rows must be equal width)");

                int y = height - 1 - row; // top row -> highest y
                for (int x = 0; x < width; x++)
                    terrain[x, y] = Terrain.FromChar(line[x]);
            }

            return new BattleMap(terrain, bounds);
        }

        public bool InBounds(GridPos p) => p.X >= 0 && p.X < Width && p.Y >= 0 && p.Y < Height;

        public TerrainType TerrainAt(GridPos p) => InBounds(p) ? _terrain[p.X, p.Y] : TerrainType.None;

        /// <summary>Walkable AND inside the active battle arena.</summary>
        public bool IsWalkable(GridPos p) => Bounds.Contains(p) && Terrain.IsWalkable(TerrainAt(p));

        public int MoveCost(GridPos p) => Bounds.Contains(p) ? Terrain.MoveCost(TerrainAt(p)) : int.MaxValue;
    }
}
