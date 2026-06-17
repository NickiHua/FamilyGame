using NUnit.Framework;
using FantacyCentry.Domain.Combat;
using FantacyCentry.Domain.Units;

namespace FantacyCentry.Domain.Tests
{
    public class DamageCalcTests
    {
        /// <summary>Deterministic RNG that returns a scripted queue of percent rolls.</summary>
        private sealed class ScriptedRng : IRng
        {
            private readonly int[] _rolls;
            private int _i;
            public ScriptedRng(params int[] rolls) => _rolls = rolls;
            public int RollPercent() => _rolls[_i++];
        }

        private static Unit Attacker(int str = 10, int spd = 8) =>
            new("ATK", Team.Player, new Stats(20, 0, str, 0, 0, 0, spd, 5));

        private static Unit Defender(int def = 4, int spd = 5, int hp = 20) =>
            new("DEF", Team.Enemy, new Stats(hp, 0, 0, 0, def, 0, spd, 5));

        [Test]
        public void BaseDamage_PhysicalSubtractsDefense()
        {
            // 10 str + 2 power - 4 def = 8
            Assert.AreEqual(8, DamageCalc.BaseDamage(Attacker(10), Defender(4), 2, DamageType.Physical));
        }

        [Test]
        public void BaseDamage_FlooredAtOne()
        {
            Assert.AreEqual(1, DamageCalc.BaseDamage(Attacker(2), Defender(99), 0, DamageType.Physical));
        }

        [Test]
        public void FinalDamage_AppliesAffinityCritAndFloors()
        {
            // base 8 × 1.25 affinity = 10, × 1.5 crit = 15
            Assert.AreEqual(15, DamageCalc.FinalDamage(8, AffinityTable.Advantage, isCrit: true, terrainDefMult: 1f));
            // base 8 × 0.75 = 6 (no crit)
            Assert.AreEqual(6, DamageCalc.FinalDamage(8, AffinityTable.Disadvantage, isCrit: false, terrainDefMult: 1f));
        }

        [Test]
        public void HitChance_FollowsSpeedFormula_AndClamps()
        {
            // 8*2 + 0 - 5*2 - 0 = 6
            Assert.AreEqual(6, DamageCalc.HitChance(Attacker(spd: 8), Defender(spd: 5), 0, 0));
            // huge defender speed clamps to 0
            Assert.AreEqual(0, DamageCalc.HitChance(Attacker(spd: 1), Defender(spd: 99), 0, 0));
        }

        [Test]
        public void Resolve_Miss_WhenRollAtOrAboveHitChance()
        {
            var atk = Attacker(spd: 8);  // hit = 6
            var def = Defender(spd: 5);
            var result = DamageCalc.Resolve(atk, def, 2, DamageType.Physical,
                AffinityTable.Default, Grid.TerrainType.Grass, new ScriptedRng(6)); // 6 >= 6 -> miss
            Assert.IsFalse(result.IsHit);
            Assert.AreEqual(0, result.Damage);
        }

        [Test]
        public void Resolve_Hit_NoAffinity_DealsBaseDamage()
        {
            var atk = Attacker(str: 10, spd: 50); // hit high
            var def = Defender(def: 4, spd: 5);
            // weaponCrit/unitCrit = 0 -> never crit; one roll consumed for hit
            var result = DamageCalc.Resolve(atk, def, 2, DamageType.Physical,
                AffinityTable.Default, Grid.TerrainType.Grass, new ScriptedRng(0));
            Assert.IsTrue(result.IsHit);
            Assert.IsFalse(result.IsCrit);
            Assert.AreEqual(8, result.Damage); // 10 + 2 - 4
        }

        [Test]
        public void Resolve_Crit_WhenSecondRollUnderCritChance()
        {
            var atk = Attacker(str: 10, spd: 50);
            var def = Defender(def: 4, spd: 5);
            // first roll 0 -> hit; second roll 0 < critChance(20) -> crit
            var result = DamageCalc.Resolve(atk, def, 2, DamageType.Physical,
                AffinityTable.Default, Grid.TerrainType.Grass, new ScriptedRng(0, 0),
                weaponCrit: 20);
            Assert.IsTrue(result.IsCrit);
            Assert.AreEqual(12, result.Damage); // 8 × 1.5
        }

        [Test]
        public void Affinity_BowVsCavalry_IsAdvantage()
        {
            var bow = new Unit("BOW", Team.Player, new Stats(20, 0, 10, 0, 0, 0, 8, 5)) { Weapon = WeaponType.Bow };
            var horse = new Unit("HORSE", Team.Enemy, new Stats(20, 0, 0, 0, 4, 0, 5, 7)) { Class = UnitClass.Cavalry };
            Assert.AreEqual(AffinityTable.Advantage, AffinityTable.Mengzhan().GetMultiplier(bow, horse));
            Assert.AreEqual(AffinityTable.Neutral, AffinityTable.Default.GetMultiplier(bow, horse));
        }
    }
}
