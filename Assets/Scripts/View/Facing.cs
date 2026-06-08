namespace FantacyCentry.View
{
    /// <summary>
    /// Grid facing directions. West is rendered by horizontally flipping the East sprites
    /// (spec §5.2 / §5.7: only S/E/N clips are stored, W = flipX of E).
    /// </summary>
    public enum Facing
    {
        South,
        East,
        North,
        West
    }
}
