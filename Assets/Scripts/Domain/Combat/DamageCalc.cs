using System;
using FantacyCentry.Domain.Grid;
using FantacyCentry.Domain.Units;

namespace FantacyCentry.Domain.Combat
{
    /// <summary>Outcome of a single attack swing (one attacker hit attempt against one defender).</summary>
    public readonly struct AttackResult
    {
        public readonly bool IsHit;
        public readonly bool IsCrit;
        public readonly int Damage;        // HP actually removable (pre-clamp to defender Hp)
        public readonly int HitChance;     // computed %, for UI preview
        public readonly int CritChance;    // computed %, for UI preview
        public readonly float AffinityMult;

        public AttackResult(bool isHit, bool isCrit, int damage, int hitChance, int critChance, float affinityMult)
        {
            IsHit = isHit;
            IsCrit = isCrit;
            Damage = damage;
            HitChance = hitChance;
            CritChance = critChance;
            AffinityMult = affinityMult;
        }

        public static AttackResult Miss(int hitChance, int critChance, float affinityMult)
            => new(false, false, 0, hitChance, critChance, affinityMult);
    }

    /// <summary>
    /// Pure combat math (spec §4.4). All methods are static and side-effect free except
    /// <see cref="Resolve"/>, which rolls an injected <see cref="IRng"/> but still does NOT
    /// mutate units — applying damage is the caller's job (so events/animation can sequence it).
    /// </summary>
    public static class DamageCalc
    {
        public const float CritMultiplier = 1.5f;

        /// <summary>
        /// Base damage before affinity/crit/terrain. power = weapon/skill base added on top of the
        /// scaling stat; type selects physical (力 vs 防) or magical (魔 vs 魔抗). Floored at 1.
        /// </summary>
        public static int BaseDamage(Unit attacker, Unit defender, int power, DamageType type)
        {
            int atk = type == DamageType.Physical ? attacker.Stats.Strength : attacker.Stats.Magic;
            int def = type == DamageType.Physical ? defender.Stats.Defense : defender.Stats.Resist;
            int raw = atk + power - def;
            return raw < 1 ? 1 : raw;
        }

        /// <summary>Final damage = base × affinity × crit × terrain-defence, floored at 1.</summary>
        public static int FinalDamage(int baseDamage, float affinityMult, bool isCrit, float terrainDefMult)
        {
            float dmg = baseDamage * affinityMult * terrainDefMult;
            if (isCrit) dmg *= CritMultiplier;
            int result = (int)Math.Floor(dmg);
            return result < 1 ? 1 : result;
        }

        /// <summary>命中率 = clamp(速×2 + 武器命中 - 守速×2 - 地形闪避, 0, 100).</summary>
        public static int HitChance(Unit attacker, Unit defender, int weaponHit, int terrainEvade)
        {
            int chance = attacker.Stats.Speed * 2 + weaponHit - defender.Stats.Speed * 2 - terrainEvade;
            return Clamp(chance, 0, 100);
        }

        /// <summary>暴击率 = clamp(武器暴击 + 角色暴击 - 守方抗暴, 0, 50).</summary>
        public static int CritChance(int weaponCrit, int unitCrit, int defenderCritResist)
            => Clamp(weaponCrit + unitCrit - defenderCritResist, 0, 50);

        /// <summary>
        /// Roll a full attack against a defender standing on <paramref name="defenderTerrain"/>.
        /// Does not mutate either unit. weaponHit/weaponCrit/unitCrit/critResist default to 0 so a
        /// bare melee swing works; data layer fills them from WeaponDef/SkillDef later.
        /// </summary>
        public static AttackResult Resolve(
            Unit attacker, Unit defender, int power, DamageType type,
            AffinityTable affinity, TerrainType defenderTerrain, IRng rng,
            int weaponHit = 0, int weaponCrit = 0, int unitCrit = 0, int critResist = 0)
        {
            float affinityMult = affinity.GetMultiplier(attacker, defender);
            int hit = HitChance(attacker, defender, weaponHit, Terrain.EvadeBonus(defenderTerrain));
            int crit = CritChance(weaponCrit, unitCrit, critResist);

            if (rng.RollPercent() >= hit)
                return AttackResult.Miss(hit, crit, affinityMult);

            bool isCrit = crit > 0 && rng.RollPercent() < crit;
            int baseDmg = BaseDamage(attacker, defender, power, type);
            int dmg = FinalDamage(baseDmg, affinityMult, isCrit, Terrain.DefenseMultiplier(defenderTerrain));

            return new AttackResult(true, isCrit, dmg, hit, crit, affinityMult);
        }

        private static int Clamp(int v, int min, int max) => v < min ? min : (v > max ? max : v);
    }
}
