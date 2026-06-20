using System.Collections.Generic;
using FantacyCentry.Domain.Combat;
using FantacyCentry.Domain.Grid;
using FantacyCentry.Domain.Pathfinding;
using FantacyCentry.Domain.Units;

namespace FantacyCentry.Domain.Battle
{
    /// <summary>
    /// A validated, undoable-in-principle action a unit takes during its turn (Command pattern,
    /// spec architecture). <see cref="Execute"/> returns false and changes nothing if the action is
    /// illegal, so the input/AI layers can probe freely. Successful commands mutate the units and
    /// raise the matching Domain events through <see cref="BattleState"/>.
    /// </summary>
    public interface IBattleCommand
    {
        bool Execute(BattleState state);
    }

    /// <summary>
    /// Move a unit to a cell within its movement budget. Validates reachability with the same
    /// <see cref="MovementRange"/>/<see cref="Pathfinder"/> the UI uses to draw the blue overlay, so
    /// what the player can click is exactly what the rules accept.
    /// </summary>
    public sealed class MoveCommand : IBattleCommand
    {
        public Unit Mover { get; }
        public GridPos Destination { get; }

        public MoveCommand(Unit mover, GridPos destination)
        {
            Mover = mover;
            Destination = destination;
        }

        public bool Execute(BattleState state)
        {
            if (state == null || Mover == null || !Mover.IsAlive) return false;
            // A unit may move at most once per turn, and not after it has finished acting.
            if (Mover.TurnState == TurnState.Moved || Mover.TurnState == TurnState.Done) return false;

            IPassability passability = state.PassabilityFor(Mover.Team);

            // Staying put is a legal "spend my move" choice.
            if (Destination == Mover.Position)
            {
                Mover.TurnState = TurnState.Moved;
                return true;
            }

            Dictionary<GridPos, int> reachable =
                MovementRange.Compute(Mover.Position, Mover.Stats.Move, passability);
            if (!reachable.ContainsKey(Destination)) return false;

            List<GridPos> path = Pathfinder.FindPath(Mover.Position, Destination, passability);
            if (path.Count < 2) return false; // no route (shouldn't happen if reachable, but stay safe)

            GridPos from = Mover.Position;
            Mover.Facing = FacingExtensions.ToFace(path[path.Count - 2], path[path.Count - 1]);
            Mover.Position = Destination;
            Mover.TurnState = TurnState.Moved;

            state.RaiseUnitMoved(new UnitMovedEvent(Mover, from, Destination, path));
            return true;
        }
    }

    /// <summary>
    /// Resolve one attack against a foe within weapon range. Delegates the math to
    /// <see cref="DamageCalc.Resolve"/> (which does not mutate), then applies HP loss here so the
    /// damage and any death are reported as ordered Domain events. Ends the attacker's turn.
    /// </summary>
    public sealed class AttackCommand : IBattleCommand
    {
        public Unit Attacker { get; }
        public Unit Defender { get; }

        private readonly int _power;
        private readonly DamageType _type;
        private readonly AffinityTable _affinity;
        private readonly IRng _rng;

        public AttackCommand(Unit attacker, Unit defender,
                             AffinityTable affinity = null, IRng rng = null,
                             int power = 0, DamageType? type = null)
        {
            Attacker = attacker;
            Defender = defender;
            _affinity = affinity ?? AffinityTable.Default;
            _rng = rng ?? new SystemRng();
            _power = power;
            _type = type ?? DefaultDamageType(attacker?.Weapon ?? WeaponType.None);
        }

        public bool Execute(BattleState state)
        {
            if (state == null || Attacker == null || Defender == null) return false;
            if (!Attacker.IsAlive || !Defender.IsAlive) return false;
            if (Attacker.TurnState == TurnState.Done) return false;
            if (!BattleState.AreEnemies(Attacker.Team, Defender.Team)) return false; // no friendly fire

            int dist = GridPos.ManhattanDistance(Attacker.Position, Defender.Position);
            if (dist < Attacker.MinRange || dist > Attacker.MaxRange) return false;

            Attacker.Facing = FacingExtensions.ToFace(Attacker.Position, Defender.Position);

            TerrainType defenderTerrain = state.Map.TerrainAt(Defender.Position);
            AttackResult result = DamageCalc.Resolve(
                Attacker, Defender, _power, _type, _affinity, defenderTerrain, _rng);

            if (result.IsHit && result.Damage > 0)
                Defender.TakeDamage(result.Damage);

            Attacker.TurnState = TurnState.Done;

            state.RaiseUnitDamaged(new UnitDamagedEvent(Attacker, Defender, result, Defender.Hp));
            if (!Defender.IsAlive)
            {
                state.RaiseUnitDied(new UnitDiedEvent(Defender));
                state.CheckEndConditions();
                return true;
            }

            // Counterattack: a surviving defender strikes back once if the attacker is still alive
            // and standing within the defender's own weapon range (classic FE reprisal).
            if (Attacker.IsAlive && CanCounter(Defender, Attacker))
            {
                Defender.Facing = FacingExtensions.ToFace(Defender.Position, Attacker.Position);
                TerrainType attackerTerrain = state.Map.TerrainAt(Attacker.Position);
                DamageType counterType = DefaultDamageType(Defender.Weapon);
                AttackResult counter = DamageCalc.Resolve(
                    Defender, Attacker, 0, counterType, _affinity, attackerTerrain, _rng);

                if (counter.IsHit && counter.Damage > 0)
                    Attacker.TakeDamage(counter.Damage);

                state.RaiseUnitDamaged(new UnitDamagedEvent(Defender, Attacker, counter, Attacker.Hp));
                if (!Attacker.IsAlive)
                    state.RaiseUnitDied(new UnitDiedEvent(Attacker));
            }

            state.CheckEndConditions();
            return true;
        }

        /// <summary>A defender may counter only with a real weapon and only when the foe sits within
        /// its own min/max attack range.</summary>
        private static bool CanCounter(Unit defender, Unit attacker)
        {
            if (defender.Weapon == WeaponType.None) return false;
            int dist = GridPos.ManhattanDistance(defender.Position, attacker.Position);
            return dist >= defender.MinRange && dist <= defender.MaxRange;
        }

        private static DamageType DefaultDamageType(WeaponType weapon)
            => weapon == WeaponType.Magic || weapon == WeaponType.Holy || weapon == WeaponType.Dark
                ? DamageType.Magical
                : DamageType.Physical;
    }

    /// <summary>
    /// End a unit's turn without attacking ("待机"/Wait). Legal whenever the unit is still able to
    /// act this turn; simply marks it <see cref="TurnState.Done"/> so the input/AI layer skips it.
    /// </summary>
    public sealed class WaitCommand : IBattleCommand
    {
        public Unit Unit { get; }

        public WaitCommand(Unit unit)
        {
            Unit = unit;
        }

        public bool Execute(BattleState state)
        {
            if (state == null || Unit == null || !Unit.IsAlive) return false;
            if (Unit.TurnState == TurnState.Done) return false;

            Unit.TurnState = TurnState.Done;
            return true;
        }
    }
}
