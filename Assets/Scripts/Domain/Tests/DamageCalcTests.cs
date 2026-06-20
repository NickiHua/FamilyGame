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

        private static Unit Attacker(int str = 10, int acc = 30, int crit = 0) =>
            new("ATK", Team.Player, new Stats(20, 0, str, 0, 0, 0, acc, 0, crit, 5));

        private static Unit Defender(int def = 4, int evade = 0, int crit = 0, int hp = 20) =>
            new("DEF", Team.Enemy, new Stats(hp, 0, 0, 0, def, 0, 0, evade, crit, 5));

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
            // base 8 × 1.25 affinity = 10, × 1.3 crit = 13
            Assert.AreEqual(13, DamageCalc.FinalDamage(8, AffinityTable.Advantage, isCrit: true, terrainDefMult: 1f));
            // base 8 × 0.75 = 6 (no crit)
            Assert.AreEqual(6, DamageCalc.FinalDamage(8, AffinityTable.Disadvantage, isCrit: false, terrainDefMult: 1f));
        }

        [Test]
        public void HitChance_WeaponPlusAccuracyMinusEvade_AndClamps()
        {
            // sword base 85 + acc 31 - evade 20 = 96 -> capped at 95
            Assert.AreEqual(95, DamageCalc.HitChance(Attacker(acc: 31), Defender(evade: 20), 85, 0));
            // 70 + 10 - 20 - 0 = 60 (mid-band, unclamped)
            Assert.AreEqual(60, DamageCalc.HitChance(Attacker(acc: 10), Defender(evade: 20), 70, 0));
            // huge evade floors at 10
            Assert.AreEqual(10, DamageCalc.HitChance(Attacker(acc: 0), Defender(evade: 99), 0, 0));
        }

        [Test]
        public void Resolve_Miss_WhenRollAtOrAboveHitChance()
        {
            var atk = Attacker(acc: 0);
            var def = Defender(evade: 0);
            // weaponHit 50 + 0 - 0 = 50 hit; roll 50 >= 50 -> miss
            var result = DamageCalc.Resolve(atk, def, 2, DamageType.Physical,
                AffinityTable.Default, Grid.TerrainType.Grass, new ScriptedRng(50), weaponHit: 50);
            Assert.IsFalse(result.IsHit);
            Assert.AreEqual(0, result.Damage);
        }

        [Test]
        public void Resolve_Magic_AlwaysHits_IgnoringEvade()
        {
            var atk = Attacker(acc: 0);
            var def = Defender(evade: 99); // would floor physical hit to 10%
            // magical attack: hit forced to 100, roll 99 still connects
            var result = DamageCalc.Resolve(atk, def, 6, DamageType.Magical,
                AffinityTable.Default, Grid.TerrainType.Grass, new ScriptedRng(99));
            Assert.IsTrue(result.IsHit);
            Assert.AreEqual(100, result.HitChance);
            Assert.AreEqual(6, result.Damage); // magic 0 + power 6 - resist 0
        }

        [Test]
        public void CritChance_WeaponPlusZealMinusDefenderZeal_AndClamps()
        {
            // weapon 10 + attacker会心 25 - defender会心 5 = 30
            Assert.AreEqual(30, DamageCalc.CritChance(10, 25, 5));
            // negative floors at 0
            Assert.AreEqual(0, DamageCalc.CritChance(0, 5, 99));
            // over-50 caps at 50
            Assert.AreEqual(50, DamageCalc.CritChance(40, 30, 0));
        }

        [Test]
        public void Resolve_Hit_NoAffinity_DealsBaseDamage()
        {
            var atk = Attacker(str: 10);
            var def = Defender(def: 4);
            // roll 0 < hit (>=10 floor) -> hit; no weaponCrit + 0 会心 -> never crit
            var result = DamageCalc.Resolve(atk, def, 2, DamageType.Physical,
                AffinityTable.Default, Grid.TerrainType.Grass, new ScriptedRng(0));
            Assert.IsTrue(result.IsHit);
            Assert.IsFalse(result.IsCrit);
            Assert.AreEqual(8, result.Damage); // 10 + 2 - 4
        }

        [Test]
        public void Resolve_Crit_WhenSecondRollUnderCritChance()
        {
            var atk = Attacker(str: 10);
            var def = Defender(def: 4);
            // first roll 0 -> hit; second roll 0 < critChance(20) -> crit
            var result = DamageCalc.Resolve(atk, def, 2, DamageType.Physical,
                AffinityTable.Default, Grid.TerrainType.Grass, new ScriptedRng(0, 0),
                weaponCrit: 20);
            Assert.IsTrue(result.IsCrit);
            Assert.AreEqual(10, result.Damage); // 8 × 1.3 = 10.4 -> floor 10
        }

        [Test]
        public void Affinity_BowVsCavalry_IsAdvantage()
        {
            var bow = new Unit("BOW", Team.Player, new Stats(20, 0, 10, 0, 0, 0, 30, 0, 0, 5)) { Weapon = WeaponType.Bow };
            var horse = new Unit("HORSE", Team.Enemy, new Stats(20, 0, 0, 0, 4, 0, 0, 0, 0, 7)) { Class = UnitClass.Cavalry };
            Assert.AreEqual(AffinityTable.Advantage, AffinityTable.Mengzhan().GetMultiplier(bow, horse));
            Assert.AreEqual(AffinityTable.Neutral, AffinityTable.Default.GetMultiplier(bow, horse));
        }
    }
}
