namespace FantacyCentry.Domain.Combat
{
    /// <summary>
    /// Deterministic random source so combat resolution is unit-testable. Production wraps
    /// System.Random / UnityEngine.Random; tests inject a scripted sequence.
    /// </summary>
    public interface IRng
    {
        /// <summary>Returns an int in [0, 100). Used for hit / crit percentage rolls.</summary>
        int RollPercent();
    }

    /// <summary>System.Random-backed RNG for production use.</summary>
    public sealed class SystemRng : IRng
    {
        private readonly System.Random _random;
        public SystemRng(int? seed = null) => _random = seed.HasValue ? new System.Random(seed.Value) : new System.Random();
        public int RollPercent() => _random.Next(0, 100);
    }
}
