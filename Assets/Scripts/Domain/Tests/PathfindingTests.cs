using System.Collections.Generic;
using NUnit.Framework;
using FantacyCentry.Domain.Grid;
using FantacyCentry.Domain.Pathfinding;
using FantacyCentry.Domain.Units;

namespace FantacyCentry.Domain.Tests
{
    public class PathfindingTests
    {
        // 5×5 all-grass map with no occupants unless specified.
        private static BattleMap Grass5() => BattleMap.FromRows(new[]
        {
            "GGGGG",
            "GGGGG",
            "GGGGG",
            "GGGGG",
            "GGGGG",
        });

        private static IPassability Open(BattleMap map, Dictionary<GridPos, Team> occupants = null)
        {
            occupants ??= new Dictionary<GridPos, Team>();
            return new MapPassability(map, Team.Player,
                cell => occupants.TryGetValue(cell, out Team t) ? t : (Team?)null);
        }

        [Test]
        public void MovementRange_BudgetOne_ReachesOrthogonalNeighboursPlusOrigin()
        {
            var map = Grass5();
            var reach = MovementRange.Compute(new GridPos(2, 2), 1, Open(map));
            // origin + 4 neighbours
            Assert.AreEqual(5, reach.Count);
            Assert.AreEqual(0, reach[new GridPos(2, 2)]);
            Assert.AreEqual(1, reach[new GridPos(3, 2)]);
            Assert.IsFalse(reach.ContainsKey(new GridPos(4, 2))); // distance 2, out of budget
        }

        [Test]
        public void MovementRange_BudgetTwo_FormsDiamondOf13()
        {
            var map = Grass5();
            var reach = MovementRange.Compute(new GridPos(2, 2), 2, Open(map));
            // Manhattan diamond radius 2 = 13 cells
            Assert.AreEqual(13, reach.Count);
        }

        [Test]
        public void MovementRange_EnemyBlocks_AllyPassThroughButCannotStop()
        {
            var map = Grass5();
            var occ = new Dictionary<GridPos, Team>
            {
                [new GridPos(3, 2)] = Team.Enemy, // blocks path east
                [new GridPos(2, 3)] = Team.Player, // ally: passable, not stoppable
            };
            var reach = MovementRange.Compute(new GridPos(2, 2), 2, Open(map, occ));
            Assert.IsFalse(reach.ContainsKey(new GridPos(3, 2))); // enemy cell never reachable
            Assert.IsFalse(reach.ContainsKey(new GridPos(2, 3))); // ally cell: can't stop
            Assert.IsTrue(reach.ContainsKey(new GridPos(2, 4)));  // but can pass through ally to here
        }

        [Test]
        public void Pathfinder_FindsShortestLength()
        {
            var map = Grass5();
            var path = Pathfinder.FindPath(new GridPos(0, 0), new GridPos(2, 1), Open(map));
            Assert.AreEqual(new GridPos(0, 0), path[0]);
            Assert.AreEqual(new GridPos(2, 1), path[^1]);
            Assert.AreEqual(4, path.Count); // 3 steps inclusive of both ends
        }

        [Test]
        public void Pathfinder_RoutesAroundWater()
        {
            // Wall of water across the middle row except a gap at x=4.
            var map = BattleMap.FromRows(new[]
            {
                "GGGGG",
                "GGGGG",
                "WWWWG",
                "GGGGG",
                "GGGGG",
            });
            var path = Pathfinder.FindPath(new GridPos(0, 0), new GridPos(0, 4), Open(map));
            Assert.IsNotEmpty(path);
            Assert.AreEqual(new GridPos(0, 4), path[^1]);
            // must detour through the x=4 gap, so longer than the straight-line 5
            Assert.Greater(path.Count, 5);
        }

        [Test]
        public void Pathfinder_ReturnsEmptyWhenBlocked()
        {
            var map = BattleMap.FromRows(new[]
            {
                "GGGGG",
                "GGGGG",
                "WWWWW", // full water wall, no gap
                "GGGGG",
                "GGGGG",
            });
            var path = Pathfinder.FindPath(new GridPos(0, 0), new GridPos(0, 4), Open(map));
            Assert.IsEmpty(path);
        }

        [Test]
        public void AttackRange_Melee_RingAroundReachable()
        {
            var stops = new HashSet<GridPos> { new(2, 2) };
            var targets = AttackRange.Compute(stops, minRange: 1, maxRange: 1, 5, 5);
            Assert.AreEqual(4, targets.Count);
            Assert.Contains(new GridPos(3, 2), new List<GridPos>(targets));
            Assert.IsFalse(targets.Contains(new GridPos(2, 2))); // own cell excluded
        }
    }
}
