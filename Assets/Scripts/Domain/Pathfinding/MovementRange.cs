using System.Collections.Generic;
using FantacyCentry.Domain.Grid;

namespace FantacyCentry.Domain.Pathfinding
{
    /// <summary>
    /// Computes a unit's reachable cells within a movement-point budget (spec §4.3). Uniform-cost
    /// search (Dijkstra) over the 4-neighbour grid, honouring terrain enter-cost and passability.
    /// "Reachable" = cells the unit could STOP on; a separate set of "passed-through" costs is kept
    /// so attack-range can extend from any cell the unit can occupy.
    /// </summary>
    public static class MovementRange
    {
        /// <summary>
        /// Returns every cell the unit can stop on, mapped to the minimum movement cost to get there
        /// (always includes the origin at cost 0, even if currently "occupied" by the mover itself).
        /// </summary>
        public static Dictionary<GridPos, int> Compute(GridPos origin, int moveBudget, IPassability passability)
        {
            var bestCost = new Dictionary<GridPos, int> { [origin] = 0 };
            var reachable = new Dictionary<GridPos, int>();

            // Simple priority by repeatedly expanding the lowest-cost frontier node.
            // Grid SRPG ranges are tiny, so a sorted-scan frontier is more than fast enough.
            var frontier = new List<GridPos> { origin };

            while (frontier.Count > 0)
            {
                int bestIdx = 0;
                for (int i = 1; i < frontier.Count; i++)
                    if (bestCost[frontier[i]] < bestCost[frontier[bestIdx]]) bestIdx = i;

                GridPos current = frontier[bestIdx];
                frontier.RemoveAt(bestIdx);
                int curCost = bestCost[current];

                // Origin is always a valid "stop" (stay put); other cells need CanStop.
                if (current == origin || passability.CanStop(current))
                    reachable[current] = curCost;

                foreach (GridPos dir in GridPos.Orthogonal)
                {
                    GridPos next = current + dir;
                    if (!passability.CanEnter(next)) continue;

                    int stepCost = passability.EnterCost(next);
                    if (stepCost == int.MaxValue) continue;

                    int newCost = curCost + stepCost;
                    if (newCost > moveBudget) continue;
                    if (bestCost.TryGetValue(next, out int known) && known <= newCost) continue;

                    bestCost[next] = newCost;
                    frontier.Add(next);
                }
            }

            return reachable;
        }
    }
}
