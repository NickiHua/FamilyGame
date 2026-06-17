namespace FantacyCentry.Domain.Grid
{
    /// <summary>
    /// Terrain kinds, mapped 1:1 to the single-letter codes used by the map pipeline
    /// (scripts/map/build_demo_map.py and Assets/Art/Maps/demo_map.json).
    /// Walkability mirrors <see cref="View"/>-side MapGrid: only G/R/D are passable;
    /// Forest is BLOCKED per the 2026-06-14 decision.
    /// </summary>
    public enum TerrainType
    {
        Grass,    // G
        Road,     // R
        Bridge,   // D
        Forest,   // F  (blocked, kept as cover/border)
        Water,    // W
        Cliff,    // C
        Building, // B
        Wall,     // L
        None,     // out of bounds / unknown
    }

    public static class Terrain
    {
        public static TerrainType FromChar(char c) => c switch
        {
            'G' => TerrainType.Grass,
            'R' => TerrainType.Road,
            'D' => TerrainType.Bridge,
            'F' => TerrainType.Forest,
            'W' => TerrainType.Water,
            'C' => TerrainType.Cliff,
            'B' => TerrainType.Building,
            'L' => TerrainType.Wall,
            _ => TerrainType.None,
        };

        public static bool IsWalkable(TerrainType t) => t switch
        {
            TerrainType.Grass => true,
            TerrainType.Road => true,
            TerrainType.Bridge => true,
            _ => false,
        };

        /// <summary>
        /// Movement-point cost to ENTER a cell of this terrain. All walkable demo terrain
        /// costs 1 for now; the field exists so future terrain (mud, hills) can cost more
        /// without touching the pathfinder. Non-walkable returns int.MaxValue.
        /// </summary>
        public static int MoveCost(TerrainType t) => IsWalkable(t) ? 1 : int.MaxValue;

        /// <summary>Defence multiplier applied to damage taken on this terrain (spec §4.4).</summary>
        public static float DefenseMultiplier(TerrainType t) => 1f; // placeholder: no defensive terrain in demo yet

        /// <summary>Evade bonus (percent) granted to a unit standing on this terrain (spec §4.4).</summary>
        public static int EvadeBonus(TerrainType t) => 0; // placeholder; forest is blocked so no +15% in demo
    }
}
