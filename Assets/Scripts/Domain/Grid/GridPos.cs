using System;

namespace FantacyCentry.Domain.Grid
{
    /// <summary>
    /// Integer cell coordinate on the battle grid. Pure value type (no UnityEngine).
    /// Convention matches the View layer: cell (0,0) is the BOTTOM-LEFT, +X right, +Y up.
    /// </summary>
    public readonly struct GridPos : IEquatable<GridPos>
    {
        public readonly int X;
        public readonly int Y;

        public GridPos(int x, int y)
        {
            X = x;
            Y = y;
        }

        public static readonly GridPos Zero = new(0, 0);

        /// <summary>The four orthogonal neighbours, in S/E/N/W order (grid SRPG has no diagonals).</summary>
        public static readonly GridPos[] Orthogonal =
        {
            new(0, -1), // South
            new(1, 0),  // East
            new(0, 1),  // North
            new(-1, 0), // West
        };

        /// <summary>Manhattan (taxicab) distance — the natural metric for 4-neighbour grids.</summary>
        public static int ManhattanDistance(GridPos a, GridPos b)
            => Math.Abs(a.X - b.X) + Math.Abs(a.Y - b.Y);

        public static GridPos operator +(GridPos a, GridPos b) => new(a.X + b.X, a.Y + b.Y);
        public static GridPos operator -(GridPos a, GridPos b) => new(a.X - b.X, a.Y - b.Y);

        public bool Equals(GridPos other) => X == other.X && Y == other.Y;
        public override bool Equals(object obj) => obj is GridPos other && Equals(other);
        public override int GetHashCode() => unchecked((X * 397) ^ Y);

        public static bool operator ==(GridPos a, GridPos b) => a.Equals(b);
        public static bool operator !=(GridPos a, GridPos b) => !a.Equals(b);

        public override string ToString() => $"({X},{Y})";
    }
}
