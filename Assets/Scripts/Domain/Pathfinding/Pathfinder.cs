using System.Collections.Generic;
using FantacyCentry.Domain.Grid;

namespace FantacyCentry.Domain.Pathfinding
{
    /// <summary>
    /// A* shortest path over the 4-neighbour grid, using terrain enter-cost and the Manhattan
    /// heuristic (admissible because the minimum step cost is 1). Returns the cell sequence from
    /// start to goal INCLUSIVE, or an empty list if no path exists within passability rules.
    /// </summary>
    public static class Pathfinder
    {
        public static List<GridPos> FindPath(GridPos start, GridPos goal, IPassability passability)
        {
            if (start == goal) return new List<GridPos> { start };

            var gScore = new Dictionary<GridPos, int> { [start] = 0 };
            var cameFrom = new Dictionary<GridPos, GridPos>();
            var open = new List<GridPos> { start };
            var fScore = new Dictionary<GridPos, int> { [start] = GridPos.ManhattanDistance(start, goal) };

            while (open.Count > 0)
            {
                int bestIdx = 0;
                for (int i = 1; i < open.Count; i++)
                    if (fScore[open[i]] < fScore[open[bestIdx]]) bestIdx = i;

                GridPos current = open[bestIdx];
                if (current == goal) return Reconstruct(cameFrom, current);
                open.RemoveAt(bestIdx);

                foreach (GridPos dir in GridPos.Orthogonal)
                {
                    GridPos next = current + dir;

                    // The goal must be stoppable; intermediate cells only need to be enterable.
                    bool isGoal = next == goal;
                    if (isGoal ? !passability.CanStop(next) : !passability.CanEnter(next)) continue;

                    int stepCost = passability.EnterCost(next);
                    if (stepCost == int.MaxValue) continue;

                    int tentative = gScore[current] + stepCost;
                    if (gScore.TryGetValue(next, out int known) && known <= tentative) continue;

                    cameFrom[next] = current;
                    gScore[next] = tentative;
                    fScore[next] = tentative + GridPos.ManhattanDistance(next, goal);
                    if (!open.Contains(next)) open.Add(next);
                }
            }

            return new List<GridPos>(); // no path
        }

        private static List<GridPos> Reconstruct(Dictionary<GridPos, GridPos> cameFrom, GridPos current)
        {
            var path = new List<GridPos> { current };
            while (cameFrom.TryGetValue(current, out GridPos prev))
            {
                current = prev;
                path.Add(current);
            }
            path.Reverse();
            return path;
        }
    }
}
