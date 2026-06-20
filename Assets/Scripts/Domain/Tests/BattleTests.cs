using System.Collections.Generic;
using NUnit.Framework;
using FantacyCentry.Domain.Battle;
using FantacyCentry.Domain.Combat;
using FantacyCentry.Domain.Grid;
using FantacyCentry.Domain.Units;

namespace FantacyCentry.Domain.Tests
{
    public class BattleTests
    {
        /// <summary>Deterministic RNG returning a scripted queue of percent rolls (0 = always hit).</summary>
        private sealed class ScriptedRng : IRng
        {
            private readonly int[] _rolls;
            private int _i;
            public ScriptedRng(params int[] rolls) => _rolls = rolls.Length == 0 ? new[] { 0 } : rolls;
            public int RollPercent() => _rolls[_i++ % _rolls.Length];
        }

        // 5×5 all-grass arena.
        private static BattleMap Grass5() => BattleMap.FromRows(new[]
        {
            "GGGGG",
            "GGGGG",
            "GGGGG",
            "GGGGG",
            "GGGGG",
        });

        private static Unit Make(string id, Team team, GridPos pos,
            int hp = 20, int str = 10, int def = 0, int move = 5,
            int min = 1, int max = 1)
        {
            return new Unit(id, team, new Stats(hp, 0, str, 0, def, 0, 0, 0, 0, move))
            {
                Position = pos,
                MinRange = min,
                MaxRange = max,
            };
        }

        private static AttackCommand AlwaysHit(Unit a, Unit d) =>
            new(a, d, AffinityTable.Default, new ScriptedRng(0));

        // --- BattleState queries ---

        [Test]
        public void UnitAt_FindsLivingOccupant_AndDeadDoNotBlock()
        {
            var hero = Make("H", Team.Player, new GridPos(1, 1));
            var foe = Make("F", Team.Enemy, new GridPos(2, 2), hp: 1);
            var state = new BattleState(Grass5(), new[] { hero, foe });

            Assert.AreSame(hero, state.UnitAt(new GridPos(1, 1)));
            Assert.IsTrue(state.IsOccupied(new GridPos(2, 2)));
            Assert.AreEqual(Team.Enemy, state.OccupantTeam(new GridPos(2, 2)));

            foe.TakeDamage(1); // dead
            Assert.IsNull(state.UnitAt(new GridPos(2, 2)));
            Assert.IsFalse(state.IsOccupied(new GridPos(2, 2)));
        }

        [Test]
        public void AreEnemies_PlayerAndAllyAreFriends_EnemyIsFoe()
        {
            Assert.IsTrue(BattleState.AreEnemies(Team.Player, Team.Enemy));
            Assert.IsTrue(BattleState.AreEnemies(Team.Ally, Team.Enemy));
            Assert.IsFalse(BattleState.AreEnemies(Team.Player, Team.Ally));
        }

        // --- MoveCommand ---

        [Test]
        public void MoveCommand_MovesWithinBudget_RaisesEvent_SetsFacingAndState()
        {
            var hero = Make("H", Team.Player, new GridPos(1, 1), move: 5);
            var state = new BattleState(Grass5(), new[] { hero });

            UnitMovedEvent? captured = null;
            state.UnitMoved += e => captured = e;

            bool ok = new MoveCommand(hero, new GridPos(3, 1)).Execute(state);

            Assert.IsTrue(ok);
            Assert.AreEqual(new GridPos(3, 1), hero.Position);
            Assert.AreEqual(Facing.East, hero.Facing);
            Assert.AreEqual(TurnState.Moved, hero.TurnState);
            Assert.IsTrue(captured.HasValue);
            Assert.AreEqual(new GridPos(1, 1), captured.Value.From);
            Assert.AreEqual(new GridPos(3, 1), captured.Value.To);
        }

        [Test]
        public void MoveCommand_RejectsCellOutOfBudget()
        {
            var hero = Make("H", Team.Player, new GridPos(0, 0), move: 1);
            var state = new BattleState(Grass5(), new[] { hero });

            bool ok = new MoveCommand(hero, new GridPos(3, 3)).Execute(state);

            Assert.IsFalse(ok);
            Assert.AreEqual(new GridPos(0, 0), hero.Position);
            Assert.AreEqual(TurnState.Idle, hero.TurnState);
        }

        [Test]
        public void MoveCommand_RejectsSecondMove()
        {
            var hero = Make("H", Team.Player, new GridPos(0, 0), move: 5);
            var state = new BattleState(Grass5(), new[] { hero });

            Assert.IsTrue(new MoveCommand(hero, new GridPos(1, 0)).Execute(state));
            Assert.IsFalse(new MoveCommand(hero, new GridPos(2, 0)).Execute(state));
            Assert.AreEqual(new GridPos(1, 0), hero.Position);
        }

        // --- WaitCommand ---

        [Test]
        public void WaitCommand_EndsTurn_WithoutMovingOrAttacking()
        {
            var hero = Make("H", Team.Player, new GridPos(0, 0), move: 5);
            var state = new BattleState(Grass5(), new[] { hero });

            bool ok = new WaitCommand(hero).Execute(state);

            Assert.IsTrue(ok);
            Assert.AreEqual(TurnState.Done, hero.TurnState);
            Assert.AreEqual(new GridPos(0, 0), hero.Position);
        }

        [Test]
        public void WaitCommand_RejectsAlreadyDoneUnit()
        {
            var hero = Make("H", Team.Player, new GridPos(0, 0), move: 5);
            var state = new BattleState(Grass5(), new[] { hero });
            Assert.IsTrue(new WaitCommand(hero).Execute(state));

            Assert.IsFalse(new WaitCommand(hero).Execute(state));
        }

        // --- AttackCommand ---

        [Test]
        public void AttackCommand_Hit_DealsDamage_RaisesEvent_EndsTurn()
        {
            var hero = Make("H", Team.Player, new GridPos(1, 1), str: 10);
            var foe = Make("F", Team.Enemy, new GridPos(2, 1), hp: 20, def: 0);
            var state = new BattleState(Grass5(), new[] { hero, foe });

            UnitDamagedEvent? dmg = null;
            state.UnitDamaged += e => dmg = e;

            bool ok = AlwaysHit(hero, foe).Execute(state);

            Assert.IsTrue(ok);
            Assert.AreEqual(10, foe.Hp); // 20 - (10 str - 0 def)
            Assert.AreEqual(TurnState.Done, hero.TurnState);
            Assert.AreEqual(Facing.East, hero.Facing);
            Assert.IsTrue(dmg.HasValue);
            Assert.AreEqual(10, dmg.Value.DefenderHpAfter);
        }

        [Test]
        public void AttackCommand_RejectsOutOfRange()
        {
            var hero = Make("H", Team.Player, new GridPos(0, 0), min: 1, max: 1);
            var foe = Make("F", Team.Enemy, new GridPos(3, 0));
            var state = new BattleState(Grass5(), new[] { hero, foe });

            Assert.IsFalse(AlwaysHit(hero, foe).Execute(state));
            Assert.AreEqual(TurnState.Idle, hero.TurnState);
        }

        [Test]
        public void AttackCommand_RejectsFriendlyFire()
        {
            var hero = Make("H", Team.Player, new GridPos(0, 0));
            var ally = Make("A", Team.Ally, new GridPos(1, 0));
            var state = new BattleState(Grass5(), new[] { hero, ally });

            Assert.IsFalse(AlwaysHit(hero, ally).Execute(state));
        }

        [Test]
        public void AttackCommand_Kill_RaisesDied_AndPlayerWins()
        {
            var hero = Make("H", Team.Player, new GridPos(1, 1), str: 10);
            var foe = Make("F", Team.Enemy, new GridPos(2, 1), hp: 5);
            var state = new BattleState(Grass5(), new[] { hero, foe });

            Unit died = null;
            state.UnitDied += e => died = e.Unit;
            BattleOutcome ended = BattleOutcome.Ongoing;
            state.BattleEnded += e => ended = e.Outcome;

            AlwaysHit(hero, foe).Execute(state);

            Assert.IsFalse(foe.IsAlive);
            Assert.AreSame(foe, died);
            Assert.AreEqual(BattleOutcome.PlayerWin, state.Outcome);
            Assert.AreEqual(BattleOutcome.PlayerWin, ended);
        }

        [Test]
        public void Defeat_WhenAllPlayerSideDead()
        {
            var hero = Make("H", Team.Player, new GridPos(1, 1), hp: 5);
            var foe = Make("F", Team.Enemy, new GridPos(2, 1), str: 10);
            var state = new BattleState(Grass5(), new[] { hero, foe });

            AlwaysHit(foe, hero).Execute(state);

            Assert.IsFalse(hero.IsAlive);
            Assert.AreEqual(BattleOutcome.PlayerLose, state.Outcome);
        }

        // --- TurnSystem ---

        [Test]
        public void TurnSystem_StartBattle_PlayerPhaseRoundOne_RaisesPhase()
        {
            var hero = Make("H", Team.Player, new GridPos(0, 0));
            var state = new BattleState(Grass5(), new[] { hero });
            var turns = new TurnSystem(state);

            TurnPhaseChangedEvent? phase = null;
            state.TurnPhaseChanged += e => phase = e;

            turns.StartBattle();

            Assert.AreEqual(Team.Player, state.CurrentTurn);
            Assert.AreEqual(1, state.RoundNumber);
            Assert.IsTrue(phase.HasValue);
            Assert.AreEqual(Team.Player, phase.Value.Team);
        }

        [Test]
        public void TurnSystem_NextPhase_AlternatesAndTicksRound()
        {
            var hero = Make("H", Team.Player, new GridPos(0, 0));
            var foe = Make("F", Team.Enemy, new GridPos(4, 4));
            var state = new BattleState(Grass5(), new[] { hero, foe });
            var turns = new TurnSystem(state);

            turns.StartBattle();
            turns.NextPhase(); // -> enemy, same round
            Assert.AreEqual(Team.Enemy, state.CurrentTurn);
            Assert.AreEqual(1, state.RoundNumber);

            turns.NextPhase(); // -> player, round 2
            Assert.AreEqual(Team.Player, state.CurrentTurn);
            Assert.AreEqual(2, state.RoundNumber);
        }

        [Test]
        public void TurnSystem_ActingTeamFinished_TracksDoneState()
        {
            var hero = Make("H", Team.Player, new GridPos(1, 1), str: 10);
            var foe = Make("F", Team.Enemy, new GridPos(2, 1), hp: 50);
            var state = new BattleState(Grass5(), new[] { hero, foe });
            var turns = new TurnSystem(state);
            turns.StartBattle();

            Assert.IsFalse(turns.ActingTeamFinished());
            AlwaysHit(hero, foe).Execute(state); // hero -> Done
            Assert.IsTrue(turns.ActingTeamFinished());
        }

        // --- EnemyAI ---

        [Test]
        public void EnemyAI_MovesIntoRange_AndAttacks()
        {
            var hero = Make("H", Team.Player, new GridPos(2, 0), hp: 5);
            var foe = Make("F", Team.Enemy, new GridPos(0, 0), str: 10, move: 5);
            var state = new BattleState(Grass5(), new[] { hero, foe });

            new EnemyAI(AffinityTable.Default, new ScriptedRng(0)).TakeTurn(state);

            Assert.AreEqual(new GridPos(1, 0), foe.Position); // stepped adjacent
            Assert.IsFalse(hero.IsAlive);                     // and killed the 5-HP hero
            Assert.AreEqual(BattleOutcome.PlayerLose, state.Outcome);
        }

        [Test]
        public void EnemyAI_ApproachesWhenOutOfReach()
        {
            var hero = Make("H", Team.Player, new GridPos(4, 0), hp: 20);
            var foe = Make("F", Team.Enemy, new GridPos(0, 0), move: 1);
            var state = new BattleState(Grass5(), new[] { hero, foe });

            new EnemyAI(AffinityTable.Default, new ScriptedRng(0)).TakeTurn(state);

            Assert.AreEqual(new GridPos(1, 0), foe.Position); // closed distance by 1
            Assert.AreEqual(20, hero.Hp);                     // no attack landed
            Assert.AreEqual(TurnState.Done, foe.TurnState);
        }
    }
}
