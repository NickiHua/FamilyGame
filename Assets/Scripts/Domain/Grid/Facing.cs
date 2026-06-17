namespace FantacyCentry.Domain.Grid
{
    /// <summary>
    /// Grid facing direction (Domain copy, mirrors the View enum). Kept here so the pure
    /// Domain assembly has no dependency on the UnityEngine-referencing View assembly.
    /// Convention (spec §5.2): only S/E/N are authored; West is the East sprite flipped.
    /// </summary>
    public enum Facing
    {
        South,
        East,
        North,
        West,
    }

    public static class FacingExtensions
    {
        /// <summary>Facing implied by moving from <paramref name="from"/> to <paramref name="to"/>.</summary>
        public static Facing ToFace(GridPos from, GridPos to)
        {
            int dx = to.X - from.X;
            int dy = to.Y - from.Y;
            // Prefer the dominant axis; ties favour horizontal (reads better for side sprites).
            if (System.Math.Abs(dx) >= System.Math.Abs(dy))
                return dx >= 0 ? Facing.East : Facing.West;
            return dy >= 0 ? Facing.North : Facing.South;
        }
    }
}
