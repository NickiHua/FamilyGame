using System;
using System.Collections.Generic;
using System.Linq;
using FantacyCentry.Domain.Grid;
using FantacyCentry.Domain.Pathfinding;
using FantacyCentry.Domain.Units;

namespace FantacyCentry.Domain.Battle
{
    /// <summary>
    /// The battle aggregate root (pure logic, no UnityEngine). Owns the map and every unit, tracks
    /// whose phase it is, and is the single place that raises Domain events. Commands and the turn
    /// system mutate the battle THROUGH this object so the event stream stays authoritative.
    ///
    /// Occupancy rule: a cell is "occupied" only by a LIVING unit, so dead units stop blocking and
    /// stop being valid targets without being removed from the roster (the View may still want them
    /// to play a death animation before disappearing).
    /// </summary>
    public sealed class BattleState
    {
        private readonly List<Unit> _units;

        public BattleMap Map { get; }
        public Team CurrentTurn { get; internal set; }
        public int RoundNumber { get; internal set; }
        public BattleOutcome Outcome { get; private set; } = BattleOutcome.Ongoing;
        public bool IsOver => Outcome != BattleOutcome.Ongoing;

        /// <summary>The full roster, living and dead, in spawn order.</summary>
        public IReadOnlyList<Unit> Roster => _units;

        public BattleState(BattleMap map, IEnumerable<Unit> units)
        {
            Map = map ?? throw new ArgumentNullException(nameof(map));
            _units = new List<Unit>(units ?? throw new ArgumentNullException(nameof(units)));
            CurrentTurn = Team.Player;
            RoundNumber = 1;
        }

        // --- Events (only BattleState may raise them; commands call the internal Raise* helpers) ---
        public event Action<UnitMovedEvent> UnitMoved;
        public event Action<UnitDamagedEvent> UnitDamaged;
        public event Action<UnitDiedEvent> UnitDied;
        public event Action<TurnPhaseChangedEvent> TurnPhaseChanged;
        public event Action<BattleEndedEvent> BattleEnded;

        // --- Queries ---

        /// <summary>The living unit standing on a cell, or null if it is empty.</summary>
        public Unit UnitAt(GridPos cell)
        {
            foreach (Unit u in _units)
                if (u.IsAlive && u.Position == cell) return u;
            return null;
        }

        public bool IsOccupied(GridPos cell) => UnitAt(cell) != null;

        /// <summary>Team of the living occupant of a cell, or null if empty (feeds <see cref="MapPassability"/>).</summary>
        public Team? OccupantTeam(GridPos cell)
        {
            Unit u = UnitAt(cell);
            return u == null ? (Team?)null : u.Team;
        }

        public IEnumerable<Unit> AliveUnits => _units.Where(u => u.IsAlive);
        public IEnumerable<Unit> UnitsOf(Team team) => AliveUnits.Where(u => u.Team == team);

        /// <summary>Living units on the opposing side of <paramref name="team"/> (Player+Ally vs Enemy).</summary>
        public IEnumerable<Unit> FoesOf(Team team) => AliveUnits.Where(u => AreEnemies(team, u.Team));

        /// <summary>Two teams are enemies iff exactly one of them is <see cref="Team.Enemy"/>.</summary>
        public static bool AreEnemies(Team a, Team b) => (a == Team.Enemy) != (b == Team.Enemy);

        /// <summary>Whether a unit on <paramref name="unitTeam"/> acts during the given phase.</summary>
        public static bool ActsInPhase(Team phase, Team unitTeam)
            => phase == Team.Enemy ? unitTeam == Team.Enemy : unitTeam != Team.Enemy;

        /// <summary>
        /// Passability for a mover of the given team: enemies block, friendlies can be passed
        /// through but not stopped on, only living units count (dead bodies don't block).
        /// </summary>
        public IPassability PassabilityFor(Team moverTeam)
            => new MapPassability(Map, moverTeam, OccupantTeam);

        // --- Internal mutators / event raisers (used by commands and the turn system) ---

        internal void RaiseUnitMoved(in UnitMovedEvent e) => UnitMoved?.Invoke(e);

        internal void RaiseUnitDamaged(in UnitDamagedEvent e) => UnitDamaged?.Invoke(e);

        internal void RaiseUnitDied(in UnitDiedEvent e) => UnitDied?.Invoke(e);

        internal void RaiseTurnPhaseChanged()
            => TurnPhaseChanged?.Invoke(new TurnPhaseChangedEvent(CurrentTurn, RoundNumber));

        /// <summary>
        /// Re-evaluate victory/defeat and, the first time a terminal state is reached, latch it and
        /// raise <see cref="BattleEnded"/> once. Called by commands after any unit may have died.
        /// </summary>
        internal void CheckEndConditions()
        {
            if (IsOver) return;

            bool enemyAlive = _units.Any(u => u.IsAlive && u.Team == Team.Enemy);
            bool playerAlive = _units.Any(u => u.IsAlive && u.Team != Team.Enemy);

            if (!enemyAlive) SetOutcome(BattleOutcome.PlayerWin);
            else if (!playerAlive) SetOutcome(BattleOutcome.PlayerLose);
        }

        private void SetOutcome(BattleOutcome outcome)
        {
            Outcome = outcome;
            BattleEnded?.Invoke(new BattleEndedEvent(outcome));
        }
    }
}
