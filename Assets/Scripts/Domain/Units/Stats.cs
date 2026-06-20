namespace FantacyCentry.Domain.Units
{
    /// <summary>
    /// Combat attributes for a unit. Plain value type, copied by value. Names map to the
    /// damage/hit formulas in spec §4.4. MaxHp/MaxMp live here; current Hp/Mp live on Unit.
    /// Turn order is NOT speed-based (traditional turn system: every unit acts once per phase),
    /// so there is no Speed stat — hit/dodge are their own attributes.
    /// </summary>
    public struct Stats
    {
        public int MaxHp;
        public int MaxMp;
        public int Strength; // 力 — physical attack
        public int Magic;    // 魔 — magical attack
        public int Defense;  // 防 — physical defence
        public int Resist;   // 魔抗 — magical defence
        public int Accuracy; // 命中 — added to weapon base hit
        public int Evade;    // 闪避 — subtracted from the attacker's hit chance
        public int Crit;     // 会心 — drives crit rate (attacker adds, defender subtracts)
        public int Move;     // 移动 — movement-point budget per turn

        public Stats(int maxHp, int maxMp, int strength, int magic,
                     int defense, int resist, int accuracy, int evade, int crit, int move)
        {
            MaxHp = maxHp;
            MaxMp = maxMp;
            Strength = strength;
            Magic = magic;
            Defense = defense;
            Resist = resist;
            Accuracy = accuracy;
            Evade = evade;
            Crit = crit;
            Move = move;
        }
    }
}
