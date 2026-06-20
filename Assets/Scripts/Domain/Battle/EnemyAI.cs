using System.Collections.Generic;
using System.Linq;
using FantacyCentry.Domain.Combat;
using FantacyCentry.Domain.Grid;
using FantacyCentry.Domain.Pathfinding;
using FantacyCentry.Domain.Units;

namespace FantacyCentry.Domain.Battle
{
    /// <summary>
    /// The demo's deliberately simple enemy brain (spec phase 5). For each enemy, in roster order:
    /// pick the nearest living foe, and if any reachable cell lets it attack that foe this turn,
    /// move there and strike; otherwise close the distance as much as its movement allows. All
    /// choices use deterministic tie-breaks (lowest cost, then lowest coordinate) so the AI is
    /// unit-testable. It drives the battle purely through <see cref="MoveCommand"/>/<see cref="AttackCommand"/>.
    /// </summary>
    public sealed class EnemyAI
    {
        private readonly AffinityTable _affinity;
        private readonly IRng _rng;

        public EnemyAI(AffinityTable affinity = null, IRng rng = null)
        {
            _affinity = affinity ?? AffinityTable.Default;
            _rng = rng ?? new SystemRng();
        }

        /// <summary>Run the whole enemy phase: every living enemy acts once.</summary>
        public void TakeTurn(BattleState state)
        {
            foreach (Unit enemy in state.UnitsOf(Team.Enemy).ToList())
            {
                if (state.IsOver) break;
                if (!enemy.IsAlive || enemy.TurnState == TurnState.Done) continue;

                ActFor(state, enemy);
                enemy.TurnState = TurnState.Done; // covers the "moved only / did nothing" cases
            }
        }

        private void ActFor(BattleState state, Unit enemy)
        {
            Unit target = NearestFoe(state, enemy);
            if (target == null) return;

            IPassability passability = state.PassabilityFor(enemy.Team);
            Dictionary<GridPos, int> reachable =
                MovementRange.Compute(enemy.Position, enemy.Stats.Move, passability);

            // 1. Prefer a cell we can stop on AND attack the target from this turn.
            if (TryPickAttackStop(reachable, enemy, target.Position, out GridPos attackStop))
            {
                if (attackStop != enemy.Position)
                    new MoveCommand(enemy, attackStop).Execute(state);
                new AttackCommand(enemy, target, _affinity, _rng).Execute(state);
                return;
            }

            // 2. Otherwise advance toward the target as far as movement allows.
            GridPos approach = PickApproach(reachable, enemy.Position, target.Position);
            if (approach != enemy.Position)
                new MoveCommand(enemy, approach).Execute(state);
        }

        private static Unit NearestFoe(BattleState state, Unit enemy)
        {
            Unit best = null;
            int bestDist = int.MaxValue;
            foreach (Unit foe in state.FoesOf(enemy.Team))
            {
                int d = GridPos.ManhattanDistance(enemy.Position, foe.Position);
                if (d < bestDist || (d == bestDist && best != null && Before(foe.Position, best.Position)))
                {
                    best = foe;
                    bestDist = d;
                }
            }
            return best;
        }

        /// <summary>Lowest-cost reachable cell from which <paramref name="targetPos"/> is in weapon range.</summary>
        private static bool TryPickAttackStop(
            Dictionary<GridPos, int> reachable, Unit enemy, GridPos targetPos, out GridPos result)
        {
            bool found = false;
            result = enemy.Position;
            int bestCost = int.MaxValue;

            foreach (KeyValuePair<GridPos, int> kv in reachable)
            {
                int d = GridPos.ManhattanDistance(kv.Key, targetPos);
                if (d < enemy.MinRange || d > enemy.MaxRange) continue;

                if (!found || kv.Value < bestCost || (kv.Value == bestCost && Before(kv.Key, result)))
                {
                    result = kv.Key;
                    bestCost = kv.Value;
                    found = true;
                }
            }
            return found;
        }

        /// <summary>Reachable cell minimising Manhattan distance to the target (tie: lower coordinate).</summary>
        private static GridPos PickApproach(
            Dictionary<GridPos, int> reachable, GridPos origin, GridPos targetPos)
        {
            GridPos best = origin;
            int bestDist = GridPos.ManhattanDistance(origin, targetPos);

            foreach (GridPos cell in reachable.Keys)
            {
                int d = GridPos.ManhattanDistance(cell, targetPos);
                if (d < bestDist || (d == bestDist && Before(cell, best)))
                {
                    best = cell;
                    bestDist = d;
                }
            }
            return best;
        }

        /// <summary>Deterministic ordering: by X, then Y. Keeps AI choices reproducible for tests.</summary>
        private static bool Before(GridPos a, GridPos b) => a.X != b.X ? a.X < b.X : a.Y < b.Y;
    }
}
