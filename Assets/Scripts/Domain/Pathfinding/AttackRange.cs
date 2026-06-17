using System.Collections.Generic;
using FantacyCentry.Domain.Grid;

namespace FantacyCentry.Domain.Pathfinding
{
    /// <summary>
    /// Derives the set of cells a unit could ATTACK (spec §4.3): the union, over every cell the
    /// unit can stop on, of the ring [minRange, maxRange] in Manhattan distance. Cells the unit
    /// itself can stand on are excluded from the threat set by default.
    /// </summary>
    public static class AttackRange
    {
        public static HashSet<GridPos> Compute(
            IEnumerable<GridPos> reachableStops, int minRange, int maxRange, int mapWidth, int mapHeight)
        {
            var targets = new HashSet<GridPos>();
            var stops = new HashSet<GridPos>(reachableStops);

            foreach (GridPos from in stops)
            {
                for (int dx = -maxRange; dx <= maxRange; dx++)
                {
                    int remaining = maxRange - System.Math.Abs(dx);
                    for (int dy = -remaining; dy <= remaining; dy++)
                    {
                        int dist = System.Math.Abs(dx) + System.Math.Abs(dy);
                        if (dist < minRange || dist > maxRange) continue;

                        var cell = new GridPos(from.X + dx, from.Y + dy);
                        if (cell.X < 0 || cell.X >= mapWidth || cell.Y < 0 || cell.Y >= mapHeight) continue;
                        if (stops.Contains(cell)) continue; // can't attack a cell you'd just move to

                        targets.Add(cell);
                    }
                }
            }

            return targets;
        }
    }
}
