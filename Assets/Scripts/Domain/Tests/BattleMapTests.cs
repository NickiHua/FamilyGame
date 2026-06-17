using NUnit.Framework;
using FantacyCentry.Domain.Grid;

namespace FantacyCentry.Domain.Tests
{
    public class BattleMapTests
    {
        // 3×3 map. Rows are TOP-FIRST (image/JSON order).
        //   row0 (top,    y=2): G W G
        //   row1 (middle, y=1): R D R
        //   row2 (bottom, y=0): G G B
        private static BattleMap Make3x3() => BattleMap.FromRows(new[]
        {
            "GWG",
            "RDR",
            "GGB",
        });

        [Test]
        public void FromRows_MapsTopFirstRowsToBottomLeftOrigin()
        {
            var map = Make3x3();
            // bottom-left (0,0) is the first char of the LAST row = 'G'
            Assert.AreEqual(TerrainType.Grass, map.TerrainAt(new GridPos(0, 0)));
            // bottom-right (2,0) = 'B'
            Assert.AreEqual(TerrainType.Building, map.TerrainAt(new GridPos(2, 0)));
            // top-middle (1,2) = 'W'
            Assert.AreEqual(TerrainType.Water, map.TerrainAt(new GridPos(1, 2)));
        }

        [Test]
        public void Walkable_GRD_True_OthersFalse()
        {
            var map = Make3x3();
            Assert.IsTrue(map.IsWalkable(new GridPos(0, 1)));  // R
            Assert.IsTrue(map.IsWalkable(new GridPos(1, 1)));  // D
            Assert.IsFalse(map.IsWalkable(new GridPos(1, 2))); // W
            Assert.IsFalse(map.IsWalkable(new GridPos(2, 0))); // B
        }

        [Test]
        public void OutOfBounds_IsNoneAndBlocked()
        {
            var map = Make3x3();
            Assert.AreEqual(TerrainType.None, map.TerrainAt(new GridPos(-1, 0)));
            Assert.IsFalse(map.IsWalkable(new GridPos(3, 3)));
            Assert.AreEqual(int.MaxValue, map.MoveCost(new GridPos(5, 5)));
        }

        [Test]
        public void Bounds_RestrictWalkability()
        {
            var inner = new GridRect(0, 0, 1, 1); // exclude column x=2 and row y=2
            var map = BattleMap.FromRows(new[] { "GGG", "GGG", "GGG" }, inner);
            Assert.IsTrue(map.IsWalkable(new GridPos(1, 1)));
            Assert.IsFalse(map.IsWalkable(new GridPos(2, 1))); // walkable terrain but outside bounds
        }

        [Test]
        public void FromRows_RejectsRaggedRows()
        {
            Assert.Throws<System.ArgumentException>(() => BattleMap.FromRows(new[] { "GGG", "GG" }));
        }
    }
}
