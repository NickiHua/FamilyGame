using FantacyCentry.Domain.Grid;

namespace FantacyCentry.Domain.Units
{
    /// <summary>
    /// A combat unit at runtime. Pure logic: no sprites, no GameObjects. The View layer holds
    /// a reference to one of these and renders it. Stats come from data (ScriptableObject in
    /// the Unity layer); here we only keep what battle rules need (spec §4.1).
    /// </summary>
    public sealed class Unit
    {
        public string Id;
        public string DisplayName;

        public Team Team;
        public UnitClass Class;
        public WeaponType Weapon;

        public Stats Stats;
        public int Hp;
        public int Mp;

        public GridPos Position;
        public Facing Facing;
        public TurnState TurnState;

        /// <summary>Weapon/attack reach in cells. Melee = 1; bow/magic set min/max (spec §4.6).</summary>
        public int MinRange = 1;
        public int MaxRange = 1;

        /// <summary>Castable skills / spells this unit owns (剑气, 闪电术, 治疗, ...).</summary>
        public System.Collections.Generic.List<Ability> Abilities = new();

        public Unit(string id, Team team, Stats stats)
        {
            Id = id;
            DisplayName = id;
            Team = team;
            Stats = stats;
            Hp = stats.MaxHp;
            Mp = stats.MaxMp;
            Facing = Facing.South;
            TurnState = TurnState.Idle;
        }

        public bool IsAlive => Hp > 0;

        /// <summary>Apply damage, clamped so Hp never drops below 0. Returns actual HP lost.</summary>
        public int TakeDamage(int amount)
        {
            if (amount < 0) amount = 0;
            int before = Hp;
            Hp = before - amount;
            if (Hp < 0) Hp = 0;
            return before - Hp;
        }

        /// <summary>Heal, clamped to MaxHp. Returns actual HP restored.</summary>
        public int Heal(int amount)
        {
            if (amount < 0) amount = 0;
            int before = Hp;
            Hp = before + amount;
            if (Hp > Stats.MaxHp) Hp = Stats.MaxHp;
            return Hp - before;
        }

        public void ResetForNewTurn() => TurnState = TurnState.Idle;
    }
}
