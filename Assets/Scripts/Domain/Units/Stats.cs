namespace FantacyCentry.Domain.Units
{
    /// <summary>
    /// Combat attributes for a unit. Plain value type, copied by value. Names map to the
    /// damage/hit formulas in spec §4.4. MaxHp/MaxMp live here; current Hp/Mp live on Unit.
    /// </summary>
    public struct Stats
    {
        public int MaxHp;
        public int MaxMp;
        public int Strength; // 力 — physical attack
        public int Magic;    // 魔 — magical attack
        public int Defense;  // 防 — physical defence
        public int Resist;   // 魔抗 — magical defence
        public int Speed;    // 速 — hit / evade / turn order
        public int Move;     // 移动 — movement-point budget per turn

        public Stats(int maxHp, int maxMp, int strength, int magic,
                     int defense, int resist, int speed, int move)
        {
            MaxHp = maxHp;
            MaxMp = maxMp;
            Strength = strength;
            Magic = magic;
            Defense = defense;
            Resist = resist;
            Speed = speed;
            Move = move;
        }
    }
}
