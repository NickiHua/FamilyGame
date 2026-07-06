using FantacyCentry.Domain.Combat;
using FantacyCentry.Domain.Grid;
using FantacyCentry.Domain.Units;
using System.Collections.Generic;

namespace FantacyCentry.Domain.Battle
{
    /// <summary>
    /// Cast a damaging ability (剑气 / 闪电术) at an enemy within the ability's range. Like
    /// <see cref="AttackCommand"/> but uses the ability's power/type and NEVER provokes a counter
    /// (energy attacks from range). Ends the caster's turn and spends MP.
    /// </summary>
    public sealed class AbilityAttackCommand : IBattleCommand
    {
        public Unit Caster { get; }
        public Unit Target { get; }
        private readonly Ability _ability;
        private readonly AffinityTable _affinity;
        private readonly IRng _rng;

        public AbilityAttackCommand(Unit caster, Unit target, Ability ability,
                                    AffinityTable affinity = null, IRng rng = null)
        {
            Caster = caster;
            Target = target;
            _ability = ability;
            _affinity = affinity ?? AffinityTable.Default;
            _rng = rng ?? new SystemRng();
        }

        public bool Execute(BattleState state)
        {
            if (state == null || Caster == null || Target == null || _ability == null) return false;
            if (_ability.IsHeal) return false;
            if (!Caster.IsAlive || !Target.IsAlive) return false;
            if (Caster.TurnState == TurnState.Done) return false;
            if (!BattleState.AreEnemies(Caster.Team, Target.Team)) return false;
            if (Caster.Mp < _ability.MpCost) return false;

            int dist = GridPos.ManhattanDistance(Caster.Position, Target.Position);
            if (dist < _ability.MinRange || dist > _ability.MaxRange) return false;

            Caster.Facing = FacingExtensions.ToFace(Caster.Position, Target.Position);
            TerrainType terrain = state.Map.TerrainAt(Target.Position);
            AttackResult result = DamageCalc.Resolve(
                Caster, Target, _ability.Power, _ability.DamageType, _affinity, terrain, _rng);

            if (result.IsHit && result.Damage > 0) Target.TakeDamage(result.Damage);

            Caster.Mp -= _ability.MpCost;
            if (Caster.Mp < 0) Caster.Mp = 0;
            Caster.TurnState = TurnState.Done;

            state.RaiseUnitDamaged(new UnitDamagedEvent(Caster, Target, result, Target.Hp));
            if (!Target.IsAlive)
                state.RaiseUnitDied(new UnitDiedEvent(Target));

            state.CheckEndConditions();
            return true; // no counterattack
        }
    }

    /// <summary>
    /// Cast a heal (治疗) on an ally within range. Restores HP, spends MP, ends the caster's turn.
    /// Raises no Domain event — the view reads <see cref="Healed"/> and plays the heal演出 itself.
    /// </summary>
    public sealed class HealCommand : IBattleCommand
    {
        public Unit Caster { get; }
        public Unit Target { get; }
        private readonly Ability _ability;

        /// <summary>HP actually restored (set by Execute).</summary>
        public int Healed { get; private set; }

        public HealCommand(Unit caster, Unit target, Ability ability)
        {
            Caster = caster;
            Target = target;
            _ability = ability;
        }

        public bool Execute(BattleState state)
        {
            if (state == null || Caster == null || Target == null || _ability == null) return false;
            if (!_ability.IsHeal) return false;
            if (!Caster.IsAlive || !Target.IsAlive) return false;
            if (Caster.TurnState == TurnState.Done) return false;
            if (BattleState.AreEnemies(Caster.Team, Target.Team)) return false; // allies only
            if (Caster.Mp < _ability.MpCost) return false;

            int dist = GridPos.ManhattanDistance(Caster.Position, Target.Position);
            if (dist < _ability.MinRange || dist > _ability.MaxRange) return false;

            Healed = Target.Heal(_ability.Power);
            Caster.Mp -= _ability.MpCost;
            if (Caster.Mp < 0) Caster.Mp = 0;
            Caster.TurnState = TurnState.Done;
            return true;
        }
    }

    /// <summary>
    /// A MAP AOE spell (火球术): targets a CELL and hits every enemy in a plus footprint (centre +
    /// 4 orthogonal cells). Raises UnitDied for kills so the view can play deaths, but does NOT raise
    /// UnitDamaged — the view reads <see cref="Results"/> and plays the map演出 itself. No counter.
    /// </summary>
    public sealed class AoeFireballCommand : IBattleCommand
    {
        public readonly struct Hit
        {
            public readonly Unit Unit;
            public readonly bool Landed;
            public readonly int Dmg;
            public readonly bool Crit;
            public readonly int HpAfter;
            public Hit(Unit u, bool landed, int dmg, bool crit, int hpAfter)
            { Unit = u; Landed = landed; Dmg = dmg; Crit = crit; HpAfter = hpAfter; }
        }

        public Unit Caster { get; }
        public GridPos Center { get; }
        private readonly Ability _ability;
        private readonly AffinityTable _affinity;
        private readonly IRng _rng;

        public List<Hit> Results { get; } = new();

        public AoeFireballCommand(Unit caster, GridPos center, Ability ability,
                                  AffinityTable affinity = null, IRng rng = null)
        {
            Caster = caster;
            Center = center;
            _ability = ability;
            _affinity = affinity ?? AffinityTable.Default;
            _rng = rng ?? new SystemRng();
        }

        public bool Execute(BattleState state)
        {
            if (state == null || Caster == null || _ability == null) return false;
            if (!Caster.IsAlive || Caster.TurnState == TurnState.Done) return false;
            if (Caster.Mp < _ability.MpCost) return false;

            int dist = GridPos.ManhattanDistance(Caster.Position, Center);
            if (dist < _ability.MinRange || dist > _ability.MaxRange) return false;
            if (Center.X < 0 || Center.Y < 0 || Center.X >= state.Map.Width || Center.Y >= state.Map.Height) return false;

            // Plus footprint: centre + 4 orthogonal neighbours.
            var cells = new List<GridPos>
            {
                Center,
                new(Center.X + 1, Center.Y), new(Center.X - 1, Center.Y),
                new(Center.X, Center.Y + 1), new(Center.X, Center.Y - 1),
            };

            var killed = new List<Unit>();
            foreach (GridPos c in cells)
            {
                Unit u = state.UnitAt(c);
                if (u == null || !u.IsAlive || !BattleState.AreEnemies(Caster.Team, u.Team)) continue;
                TerrainType terrain = state.Map.TerrainAt(u.Position);
                AttackResult r = DamageCalc.Resolve(Caster, u, _ability.Power, _ability.DamageType, _affinity, terrain, _rng);
                if (r.IsHit && r.Damage > 0) u.TakeDamage(r.Damage);
                Results.Add(new Hit(u, r.IsHit, r.Damage, r.IsCrit, u.Hp));
                if (!u.IsAlive) killed.Add(u);
            }

            Caster.Mp -= _ability.MpCost;
            if (Caster.Mp < 0) Caster.Mp = 0;
            Caster.TurnState = TurnState.Done;

            foreach (Unit u in killed) state.RaiseUnitDied(new UnitDiedEvent(u));
            state.CheckEndConditions();
            return true;
        }
    }
}
