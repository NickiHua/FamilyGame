namespace FantacyCentry.Domain.Units
{
    /// <summary>Which side a unit fights for.</summary>
    public enum Team
    {
        Player,
        Enemy,
        Ally, // NPC fighting alongside the player
    }

    /// <summary>Per-turn action progress for a unit (spec §4.1).</summary>
    public enum TurnState
    {
        Idle,  // hasn't acted this turn
        Moved, // moved but hasn't taken an action (can still act, or undo move)
        Acted, // took an action but turn machinery may still finalize
        Done,  // finished for this turn
    }

    /// <summary>
    /// Weapon family — drives the affinity (相克) table (spec §4.5). The Axe entry is kept as
    /// an interface point even though the demo treats axes as part of the sword family.
    /// </summary>
    public enum WeaponType
    {
        Sword,
        Lance,
        Axe,
        Bow,
        Magic, // arcane / elemental
        Holy,  // 圣
        Dark,  // 暗
        None,  // unarmed / placeholder
    }

    /// <summary>
    /// Combat class / mobility archetype — the DEFENDER side of the affinity table
    /// (弓 &gt; 飞/骑, 法 &gt; 重甲). Mengzhan cycle 剑&gt;枪&gt;骑 mixes weapon and class.
    /// </summary>
    public enum UnitClass
    {
        Infantry,
        Cavalry, // 骑
        Flying,  // 飞
        Armored, // 重甲
        Mage,
    }

    /// <summary>Whether an attack scales off physical (力/防) or magical (魔/魔抗) stats.</summary>
    public enum DamageType
    {
        Physical,
        Magical,
    }
}
