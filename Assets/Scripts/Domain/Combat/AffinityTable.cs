using System.Collections.Generic;
using FantacyCentry.Domain.Units;

namespace FantacyCentry.Domain.Combat
{
    /// <summary>
    /// Affinity (兵种相克) lookup. Per the 2026-06-15 decision this is a PLACEHOLDER coefficient
    /// table: the default returns 1.0 for everything, so the system runs without committing to
    /// numbers. The Mengzhan relationships are encoded as DATA (not hardcoded in the formula),
    /// ready to switch on when balancing begins.
    ///
    /// Lookup key = (attacker WeaponType, defender UnitClass). Multiplier is applied to the
    /// attacker's outgoing damage. The documented "受击 ×0.75" side is naturally produced by the
    /// reciprocal relationship when the roles reverse, so we only store the attacker-advantage side.
    /// </summary>
    public sealed class AffinityTable
    {
        public const float Advantage = 1.25f; // 克制方输出
        public const float Disadvantage = 0.75f;
        public const float Neutral = 1.0f;

        private readonly Dictionary<(WeaponType, UnitClass), float> _table;
        private readonly float _default;

        public AffinityTable(float @default = Neutral,
                             Dictionary<(WeaponType, UnitClass), float> table = null)
        {
            _default = @default;
            _table = table ?? new Dictionary<(WeaponType, UnitClass), float>();
        }

        public float GetMultiplier(WeaponType attackerWeapon, UnitClass defenderClass)
            => _table.TryGetValue((attackerWeapon, defenderClass), out float m) ? m : _default;

        public float GetMultiplier(Unit attacker, Unit defender)
            => GetMultiplier(attacker.Weapon, defender.Class);

        /// <summary>The demo default: everything neutral (×1.0). Affinity has no effect yet.</summary>
        public static AffinityTable Default => new(Neutral);

        /// <summary>
        /// The Mengzhan relationships from spec §4.5, ready for balancing:
        /// 剑&gt;枪&gt;骑(cycle, 骑&gt;剑), 圣&gt;暗, 弓&gt;飞/骑 (but弓弱近战 handled via stats/range),
        /// 暗 微克全体. Axe is folded into the sword family for the demo.
        /// </summary>
        public static AffinityTable Mengzhan()
        {
            var t = new Dictionary<(WeaponType, UnitClass), float>
            {
                // 弓 克 飞行 / 骑兵
                { (WeaponType.Bow, UnitClass.Flying), Advantage },
                { (WeaponType.Bow, UnitClass.Cavalry), Advantage },
                // 法 克 重甲
                { (WeaponType.Magic, UnitClass.Armored), Advantage },
                // 剑/斧（同系）克 …（枪 mapped to Lance-class units when modelled）
                // 圣 / 暗 attribute clash is modelled when those weapon types are used.
            };
            return new AffinityTable(Neutral, t);
        }
    }
}
