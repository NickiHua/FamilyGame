using System.Collections.Generic;
using FantacyCentry.Domain.Combat;
using FantacyCentry.Domain.Grid;
using FantacyCentry.Domain.Units;

namespace FantacyCentry.Domain.Battle
{
    /// <summary>
    /// How a battle ended (spec §6 victory/defeat). <see cref="Ongoing"/> while it is still being
    /// fought. The player side = Player + Ally units; the foe side = Enemy units.
    /// </summary>
    public enum BattleOutcome
    {
        Ongoing,
        PlayerWin,  // every enemy is dead
        PlayerLose, // every player/ally unit is dead
    }

    /// <summary>
    /// Domain events are immutable value notifications raised by <see cref="BattleState"/> when the
    /// rules change something. The View layer subscribes and plays animation; the Domain stays free
    /// of UnityEngine (spec architecture: "resolution is a Domain EVENT, the view is a subscriber").
    /// A future battle-scene transition is just another subscriber — the Domain never changes.
    /// </summary>
    public readonly struct UnitMovedEvent
    {
        public readonly Unit Unit;
        public readonly GridPos From;
        public readonly GridPos To;

        /// <summary>Full cell path start→destination inclusive, so the view can walk it step by step.</summary>
        public readonly IReadOnlyList<GridPos> Path;

        public UnitMovedEvent(Unit unit, GridPos from, GridPos to, IReadOnlyList<GridPos> path)
        {
            Unit = unit;
            From = from;
            To = to;
            Path = path;
        }
    }

    /// <summary>Raised once per resolved attack swing (hit OR miss).</summary>
    public readonly struct UnitDamagedEvent
    {
        public readonly Unit Attacker;
        public readonly Unit Defender;
        public readonly AttackResult Result;
        public readonly int DefenderHpAfter;

        public UnitDamagedEvent(Unit attacker, Unit defender, AttackResult result, int defenderHpAfter)
        {
            Attacker = attacker;
            Defender = defender;
            Result = result;
            DefenderHpAfter = defenderHpAfter;
        }
    }

    /// <summary>Raised when a unit's HP reaches 0 (fired after the matching <see cref="UnitDamagedEvent"/>).</summary>
    public readonly struct UnitDiedEvent
    {
        public readonly Unit Unit;
        public UnitDiedEvent(Unit unit) => Unit = unit;
    }

    /// <summary>Raised whenever the active side changes (start of player phase / enemy phase).</summary>
    public readonly struct TurnPhaseChangedEvent
    {
        public readonly Team Team;
        public readonly int RoundNumber;

        public TurnPhaseChangedEvent(Team team, int roundNumber)
        {
            Team = team;
            RoundNumber = roundNumber;
        }
    }

    /// <summary>Raised exactly once when the battle reaches a win/lose state.</summary>
    public readonly struct BattleEndedEvent
    {
        public readonly BattleOutcome Outcome;
        public BattleEndedEvent(BattleOutcome outcome) => Outcome = outcome;
    }
}
