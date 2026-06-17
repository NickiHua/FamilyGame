namespace FantacyCentry.Domain.Grid
{
    /// <summary>
    /// An inclusive rectangle of cells. Used by <c>LevelDef.BattleBounds</c> (spec §4.8):
    /// the full logic map can be 35×35 but a battle is framed to a sub-region so spawns,
    /// movement, AI and camera all clamp to a sensible ~16×16 arena (spec §8 / 2026-06-15).
    /// </summary>
    public readonly struct GridRect
    {
        public readonly int MinX;
        public readonly int MinY;
        public readonly int MaxX; // inclusive
        public readonly int MaxY; // inclusive

        public GridRect(int minX, int minY, int maxX, int maxY)
        {
            MinX = minX;
            MinY = minY;
            MaxX = maxX;
            MaxY = maxY;
        }

        public int Width => MaxX - MinX + 1;
        public int Height => MaxY - MinY + 1;

        public bool Contains(GridPos p) => p.X >= MinX && p.X <= MaxX && p.Y >= MinY && p.Y <= MaxY;

        /// <summary>A rect covering the whole map (no battle framing).</summary>
        public static GridRect Full(int width, int height) => new(0, 0, width - 1, height - 1);
    }
}
