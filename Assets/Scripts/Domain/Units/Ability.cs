using System.Collections.Generic;

namespace FantacyCentry.Domain.Units
{
    /// <summary>Which command-panel bucket an ability lives under.</summary>
    public enum AbilityKind { Skill, Magic }

    /// <summary>Who an ability may target.</summary>
    public enum AbilityTarget { Enemy, Ally }

    /// <summary>Area of effect footprint (Manhattan-centred).</summary>
    public enum AbilityAoe { Single, Plus }   // Plus = centre + 4 orthogonal cells (5 total)

    /// <summary>
    /// A castable skill / spell a unit owns. Pure data (Domain). Damage abilities resolve through
    /// <see cref="Combat.DamageCalc"/> using <see cref="Power"/>/<see cref="DamageType"/>; heal
    /// abilities restore HP. Abilities never provoke a counter (ranged energy attacks).
    /// </summary>
    public sealed class Ability
    {
        public string Id;
        public string Name;
        public AbilityKind Kind = AbilityKind.Skill;
        public AbilityTarget Target = AbilityTarget.Enemy;

        /// <summary>Cast reach in cells (Manhattan). Cast from the unit's current position.</summary>
        public int MinRange = 1;
        public int MaxRange = 2;

        /// <summary>Extra power added on top of the caster's stat in DamageCalc, or the heal amount.</summary>
        public int Power = 0;
        public DamageType DamageType = DamageType.Magical;
        public bool IsHeal = false;

        public int MpCost = 0;

        /// <summary>VFX bank key played in the battle stage ("swordwave","lightning","heal",...).</summary>
        public string VfxKey;

        /// <summary>When true the effect plays ON THE MAP (no battle-stage cut) — for AOE spells and
        /// heals so the battlefield / friendly target stays in view.</summary>
        public bool MapCast = false;

        /// <summary>AOE footprint. Plus abilities target a CELL and hit every enemy in the footprint.</summary>
        public AbilityAoe Aoe = AbilityAoe.Single;

        /// <summary>VFX playback speed multiplier (0.5 = half speed / twice as long).</summary>
        public float VfxSpeedMul = 1f;
    }

    /// <summary>Factory for the demo's fixed ability set.</summary>
    public static class Abilities
    {
        /// <summary>剑气 — a 2-range physical sword-energy wave (no counter). LuLi / LingShuang.</summary>
        public static Ability SwordWave() => new()
        {
            Id = "swordwave", Name = "剑气",
            Kind = AbilityKind.Skill, Target = AbilityTarget.Enemy,
            MinRange = 1, MaxRange = 2, Power = 4, DamageType = DamageType.Physical,
            MpCost = 0, VfxKey = "swordwave",
        };

        /// <summary>闪电术 — a 2-range magical lightning strike (no counter). SuYao.</summary>
        public static Ability Lightning() => new()
        {
            Id = "lightning", Name = "闪电术",
            Kind = AbilityKind.Magic, Target = AbilityTarget.Enemy,
            MinRange = 1, MaxRange = 2, Power = 6, DamageType = DamageType.Magical,
            MpCost = 3, VfxKey = "lightning", VfxSpeedMul = 0.5f,
        };

        /// <summary>冰锥术 — a 2-range magical ice spike (no counter). SuYao.</summary>
        public static Ability IceSpike() => new()
        {
            Id = "icespike", Name = "冰锥术",
            Kind = AbilityKind.Magic, Target = AbilityTarget.Enemy,
            MinRange = 1, MaxRange = 2, Power = 5, DamageType = DamageType.Magical,
            MpCost = 3, VfxKey = "icespike",
        };

        /// <summary>火球术 — MAP AOE: plus footprint (5 cells), range 3, hits all enemies. SuYao.</summary>
        public static Ability Fireball() => new()
        {
            Id = "fireball", Name = "火球术",
            Kind = AbilityKind.Magic, Target = AbilityTarget.Enemy,
            MinRange = 1, MaxRange = 3, Power = 5, DamageType = DamageType.Magical,
            MpCost = 5, VfxKey = "fireball", MapCast = true, Aoe = AbilityAoe.Plus,
        };

        /// <summary>治疗 — restore HP to an ally within 2 cells (or self), cast ON THE MAP. SuYao.</summary>
        public static Ability Heal() => new()
        {
            Id = "heal", Name = "治疗术",
            Kind = AbilityKind.Magic, Target = AbilityTarget.Ally,
            MinRange = 0, MaxRange = 2, Power = 12, IsHeal = true,
            MpCost = 2, VfxKey = "heal", MapCast = true,
        };

        /// <summary>The abilities a given spawn id starts with.</summary>
        public static List<Ability> For(string unitId)
        {
            var list = new List<Ability>();
            switch (unitId)
            {
                case "LuLi":
                case "LingShuang":
                    list.Add(SwordWave());
                    break;
                case "SuYao":
                    list.Add(Lightning());
                    list.Add(IceSpike());
                    list.Add(Fireball());
                    list.Add(Heal());
                    break;
            }
            return list;
        }
    }
}
