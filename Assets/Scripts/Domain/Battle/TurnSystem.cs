using FantacyCentry.Domain.Units;

namespace FantacyCentry.Domain.Battle
{
    /// <summary>
    /// Drives the alternating phase loop (spec §4: player phase → enemy phase → next round). It does
    /// not decide WHAT units do — that is commands / AI — it only flips the active side and refreshes
    /// the acting team's per-turn state, raising <see cref="TurnPhaseChangedEvent"/> each time.
    ///
    /// Player phase controls Player + Ally units; enemy phase controls Enemy units. A full round is
    /// one player phase followed by one enemy phase; the round counter ticks when play returns to the
    /// player.
    /// </summary>
    public sealed class TurnSystem
    {
        private readonly BattleState _state;

        public TurnSystem(BattleState state) => _state = state;

        public BattleState State => _state;

        /// <summary>Begin the battle on round 1, player phase, with player units refreshed.</summary>
        public void StartBattle()
        {
            _state.RoundNumber = 1;
            _state.CurrentTurn = Team.Player;
            ResetActingTeam();
            _state.RaiseTurnPhaseChanged();
        }

        /// <summary>
        /// Advance to the next phase. Player → Enemy keeps the round; Enemy → Player starts a new
        /// round. No-op once the battle is over.
        /// </summary>
        public void NextPhase()
        {
            if (_state.IsOver) return;

            if (_state.CurrentTurn == Team.Player)
            {
                _state.CurrentTurn = Team.Enemy;
            }
            else
            {
                _state.CurrentTurn = Team.Player;
                _state.RoundNumber++;
            }

            ResetActingTeam();
            _state.RaiseTurnPhaseChanged();
        }

        /// <summary>True when every unit that acts this phase has finished (turn can auto-advance).</summary>
        public bool ActingTeamFinished()
        {
            foreach (Unit u in _state.AliveUnits)
                if (BattleState.ActsInPhase(_state.CurrentTurn, u.Team) && u.TurnState != TurnState.Done)
                    return false;
            return true;
        }

        private void ResetActingTeam()
        {
            foreach (Unit u in _state.AliveUnits)
                if (BattleState.ActsInPhase(_state.CurrentTurn, u.Team))
                    u.ResetForNewTurn();
        }
    }
}
