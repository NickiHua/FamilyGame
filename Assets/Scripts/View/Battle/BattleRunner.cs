using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using FantacyCentry.Domain.Battle;
using FantacyCentry.Domain.Combat;
using FantacyCentry.Domain.Grid;
using FantacyCentry.Domain.Units;

namespace FantacyCentry.View.Battle
{
    /// <summary>
    /// The bridge between the pure-C# Domain battle and the Unity scene. At runtime it builds a
    /// <see cref="BattleState"/> from serialized spawn data, instantiates a <see cref="UnitView"/>
    /// per unit, and runs the player ↔ enemy turn loop. Domain events are buffered into a visual
    /// queue and replayed one step at a time (walk, swing, react, die) so the action is watchable
    /// and input stays locked while it plays.
    /// </summary>
    public sealed class BattleRunner : MonoBehaviour
    {
        [Serializable]
        public sealed class UnitSpawn
        {
            public string id = "Unit";
            public GameObject prefab;
            public Team team = Team.Player;
            public Vector2Int cell;
            public WeaponType weapon = WeaponType.Sword;

            [Header("Stats")]
            public int maxHp = 20;
            public int strength = 10;
            public int magic = 0;
            public int defense = 3;
            public int resist = 0;
            public int accuracy = 30;
            public int evade = 5;
            public int crit = 5;
            public int move = 4;
            public int minRange = 1;
            public int maxRange = 1;
        }

        [Header("Map (built into the Domain BattleMap at Play)")]
        public MapGrid mapGrid;

        [Header("Units to spawn")]
        public List<UnitSpawn> spawns = new();

        [Header("Overlay (optional, for the input controller)")]
        public RangeOverlay overlay;

        [Header("HUD (optional; gates turn flow on the turn banner)")]
        public BattleHud hud;

        [Header("Pacing")]
        [Tooltip("Pause (seconds) inserted between buffered visual steps so the action reads clearly.")]
        public float stepPause = 0.15f;

        [Header("Combat text")]
        [Tooltip("Camera used to place floating damage / MISS text. Defaults to Camera.main.")]
        public Camera worldCamera;

        public BattleState State { get; private set; }
        public bool IsBusy => _busy || (hud != null && hud.IsBannerPlaying);
        public bool IsOver => State != null && State.IsOver;
        public Team CurrentTurn => State != null ? State.CurrentTurn : Team.Player;
        public bool Ready { get; private set; }

        private bool _busy;
        private TurnSystem _turns;
        private EnemyAI _ai;
        private AffinityTable _affinity;
        private IRng _rng;

        private readonly Dictionary<Unit, UnitView> _views = new();
        private readonly Queue<VisualStep> _queue = new();

        /// <summary>HP as the *visuals* currently show it. The Domain mutates Unit.Hp the instant a
        /// command resolves (so during an enemy phase every hit has already landed before a single
        /// swing plays). HP bars read this lagged value instead, and DrainQueue advances it one hit
        /// at a time as each swing connects — so a bar drops per attack, not all at once.</summary>
        private readonly Dictionary<Unit, int> _displayHp = new();

        /// <summary>Raised after the turn flow changes so input/HUD can refresh.</summary>
        public event Action StateChanged;

        /// <summary>Raised when the active side changes (start of a player or enemy phase),
        /// forwarding the Domain phase event so the HUD can show a turn banner.</summary>
        public event Action<Team, int> PhaseChanged;

        public UnitView ViewFor(Unit unit) =>
            unit != null && _views.TryGetValue(unit, out UnitView v) ? v : null;

        /// <summary>Every spawned unit view (alive or dead). The HUD iterates these each frame to
        /// draw world-following HP bars. Typed as the dictionary value collection so the per-frame
        /// foreach allocates nothing.</summary>
        public Dictionary<Unit, UnitView>.ValueCollection Views => _views.Values;

        /// <summary>HP as the playback currently shows it (lags the Domain during multi-hit phases).
        /// Falls back to the live value for units that have never been damaged.</summary>
        public int DisplayHpOf(Unit unit) =>
            unit != null && _displayHp.TryGetValue(unit, out int hp) ? hp : (unit?.Hp ?? 0);

        private void Start() => Build();

        private void Build()
        {
            if (mapGrid == null || mapGrid.RowsTopFirst == null || mapGrid.RowsTopFirst.Count == 0)
            {
                Debug.LogError("[BattleRunner] mapGrid is missing or unparsed; cannot build the battle.");
                return;
            }

            BattleMap map = BattleMap.FromRows(mapGrid.RowsTopFirst);
            _affinity = AffinityTable.Default;
            _rng = new SystemRng();

            var units = new List<Unit>(spawns.Count);
            foreach (UnitSpawn s in spawns)
            {
                Unit unit = BuildUnit(s);
                UnitView view = SpawnView(s, unit);
                if (view == null) continue;
                units.Add(unit);
                _views[unit] = view;
                _displayHp[unit] = unit.Hp;
            }

            State = new BattleState(map, units);
            State.UnitMoved += OnMoved;
            State.UnitDamaged += OnDamaged;
            State.UnitDied += OnDied;
            State.TurnPhaseChanged += OnPhase;
            State.BattleEnded += OnEnded;

            _turns = new TurnSystem(State);
            _ai = new EnemyAI(_affinity, _rng);
            _turns.StartBattle();

            Ready = true;
            StateChanged?.Invoke();
        }

        private static Unit BuildUnit(UnitSpawn s)
        {
            var stats = new Stats(
                s.maxHp, 0, s.strength, s.magic, s.defense, s.resist,
                s.accuracy, s.evade, s.crit, s.move);
            return new Unit(s.id, s.team, stats)
            {
                Position = new GridPos(s.cell.x, s.cell.y),
                Weapon = s.weapon,
                MinRange = s.minRange,
                MaxRange = s.maxRange,
            };
        }

        private UnitView SpawnView(UnitSpawn s, Unit unit)
        {
            if (s.prefab == null)
            {
                Debug.LogWarning("[BattleRunner] Spawn '" + s.id + "' has no prefab; skipped.");
                return null;
            }

            GameObject go = Instantiate(s.prefab);
            go.name = s.id;
            go.transform.position = new Vector3(s.cell.x, s.cell.y, 0f);

            // The demo arrow-key driver would fight our input; strip it from battle units.
            var demo = go.GetComponent<CharacterDemoController>();
            if (demo != null) Destroy(demo);
            if (go.GetComponent<YSort>() == null) go.AddComponent<YSort>();

            var view = go.GetComponent<UnitView>();
            if (view == null) view = go.AddComponent<UnitView>();
            view.Bind(unit);
            return view;
        }

        // --- Public command surface (used by BattleInputController) ---

        public bool CanAct() =>
            Ready && State != null && !State.IsOver && !IsBusy && State.CurrentTurn == Team.Player;

        public bool SubmitMove(Unit mover, GridPos destination)
        {
            if (!CanAct()) return false;
            if (!new MoveCommand(mover, destination).Execute(State)) return false;
            StartCoroutine(PlayQueued());
            return true;
        }

        public bool SubmitAttack(Unit attacker, Unit defender)
        {
            if (!CanAct()) return false;
            if (!new AttackCommand(attacker, defender, _affinity, _rng).Execute(State)) return false;
            StartCoroutine(PlayQueued());
            return true;
        }

        /// <summary>
        /// Move to <paramref name="destination"/> and then attack <paramref name="defender"/> in one
        /// committed action (the FE-style "move into range and strike"). The walk and the swing are
        /// queued so they play back-to-back. Returns true only if both steps were legal.
        /// </summary>
        public bool SubmitMoveThenAttack(Unit attacker, GridPos destination, Unit defender)
        {
            if (!CanAct()) return false;
            if (!new MoveCommand(attacker, destination).Execute(State)) return false;
            // The move already happened; even if the attack is somehow illegal we still play the walk.
            new AttackCommand(attacker, defender, _affinity, _rng).Execute(State);
            StartCoroutine(PlayQueued());
            return true;
        }

        /// <summary>
        /// Silently revert a unit to <paramref name="originalCell"/> and re-open its turn (used by the
        /// input layer when the player right-clicks to cancel a move they hadn't committed with an
        /// attack). No Domain event is raised — this is a UI-level take-back, not a game action.
        /// </summary>
        public void UndoMove(Unit unit, GridPos originalCell)
        {
            if (unit == null || State == null) return;
            unit.Position = originalCell;
            unit.TurnState = TurnState.Idle;
            UnitView v = ViewFor(unit);
            if (v != null) { v.SnapTo(originalCell); v.FaceSouth(); }
            StateChanged?.Invoke();
        }

        /// <summary>End a unit's turn without attacking ("待机"/Wait).</summary>
        public bool SubmitWait(Unit unit)
        {
            if (!CanAct()) return false;
            if (!new WaitCommand(unit).Execute(State)) return false;
            UnitView v = ViewFor(unit);
            if (v != null) v.FaceSouth();
            StateChanged?.Invoke();
            // If that was the last unit, hand the phase to the enemy.
            if (!State.IsOver && _turns.ActingTeamFinished())
                StartCoroutine(EndTurnAfterWait());
            return true;
        }

        private IEnumerator EndTurnAfterWait()
        {
            _busy = true;
            yield return EnemyTurn();
            _busy = false;
            StateChanged?.Invoke();
        }

        /// <summary>Player chooses to end the phase; the enemy then acts.</summary>
        public void RequestEndTurn()
        {
            if (!CanAct()) return;
            StartCoroutine(EndTurnRoutine());
        }

        // --- Turn-flow coroutines ---

        private IEnumerator PlayQueued()
        {
            _busy = true;
            yield return DrainQueue();
            StateChanged?.Invoke();
            if (!State.IsOver && _turns.ActingTeamFinished())
                yield return EnemyTurn();
            _busy = false;
            StateChanged?.Invoke();
        }

        private IEnumerator EndTurnRoutine()
        {
            _busy = true;
            yield return EnemyTurn();
            _busy = false;
            StateChanged?.Invoke();
        }

        private IEnumerator EnemyTurn()
        {
            _turns.NextPhase();           // Player -> Enemy (resets enemy units)
            yield return WaitForBanner(); // let the ENEMY PHASE banner finish before the AI moves
            _ai.TakeTurn(State);          // buffers its moves/attacks into the queue
            yield return DrainQueue();
            if (!State.IsOver)
            {
                _turns.NextPhase();       // Enemy -> Player (new round, resets player units)
                yield return WaitForBanner(); // hold input until the PLAYER PHASE banner clears
            }
        }

        /// <summary>Wait until the turn banner (if any) has finished animating. The phase event
        /// fires synchronously inside NextPhase, so by the time we get here the banner coroutine
        /// has already started and IsBannerPlaying is true.</summary>
        private IEnumerator WaitForBanner()
        {
            if (hud == null) yield break;
            while (hud.IsBannerPlaying) yield return null;
        }

        private IEnumerator DrainQueue()
        {
            while (_queue.Count > 0)
            {
                VisualStep step = _queue.Dequeue();
                switch (step.Kind)
                {
                    case VisualKind.Move:
                    {
                        UnitView v = ViewFor(step.Unit);
                        if (v != null)
                        {
                            v.WalkPath(step.Path);
                            while (v.IsAnimating) yield return null;
                            v.FaceSouth();
                        }
                        if (stepPause > 0f) yield return new WaitForSeconds(stepPause);
                        break;
                    }
                    case VisualKind.Damage:
                    {
                        UnitView atk = ViewFor(step.Unit);
                        UnitView def = ViewFor(step.Other);
                        float dur = 0.25f;
                        if (atk != null)
                        {
                            atk.FacePoint(step.Other.Position);
                            dur = atk.PlayAttack();
                        }
                        if (def != null) def.FacePoint(step.Unit.Position); // turn to face the attacker
                        yield return new WaitForSeconds(dur * 0.55f);
                        if (def != null)
                        {
                            if (step.Hit) def.PlayHit();
                            SpawnFloater(def.transform.position, step);
                        }
                        // Drop the defender's HP bar exactly as this swing lands (not when the Domain
                        // resolved the whole exchange moments earlier).
                        _displayHp[step.Other] = step.HpAfter;
                        yield return new WaitForSeconds(Mathf.Max(0.05f, dur * 0.45f));

                        // If a counter swing between the same pair is up next, leave both fighters
                        // facing each other so the reprisal reads as one continuous clash instead of
                        // snapping back to "face south" and re-turning.
                        bool counterNext = _queue.Count > 0 && IsCounterOf(_queue.Peek(), step);
                        if (!counterNext)
                        {
                            if (atk != null) atk.FaceSouth();
                            if (def != null && def.Unit != null && def.Unit.IsAlive) def.FaceSouth();
                        }
                        if (stepPause > 0f) yield return new WaitForSeconds(stepPause);
                        break;
                    }
                    case VisualKind.Died:
                    {
                        ViewFor(step.Unit)?.Die();
                        if (stepPause > 0f) yield return new WaitForSeconds(stepPause);
                        break;
                    }
                }
            }
        }

        // --- Domain event handlers (buffer only; playback is sequenced in DrainQueue) ---

        /// <summary>True when <paramref name="next"/> is the reprisal for <paramref name="step"/> —
        /// a damage step between the same two units, attacker and defender swapped.</summary>
        private static bool IsCounterOf(VisualStep next, VisualStep step) =>
            next.Kind == VisualKind.Damage && next.Unit == step.Other && next.Other == step.Unit;

        private void OnMoved(UnitMovedEvent e) => _queue.Enqueue(VisualStep.Move(e.Unit, e.Path));

        private void OnDamaged(UnitDamagedEvent e)
        {
            _queue.Enqueue(VisualStep.Damage(e.Attacker, e.Defender, e.Result.IsHit, e.Result.Damage, e.Result.IsCrit, e.DefenderHpAfter));
            string outcome = e.Result.IsHit
                ? (e.Result.IsCrit ? "CRIT " : "") + e.Result.Damage + " dmg (hp " + e.DefenderHpAfter + ")"
                : "MISS";
            Debug.Log("[Battle] " + e.Attacker.Id + " -> " + e.Defender.Id + ": " + outcome);
        }

        private void OnDied(UnitDiedEvent e) => _queue.Enqueue(VisualStep.Died(e.Unit));

        private void OnPhase(TurnPhaseChangedEvent e)
        {
            Debug.Log("[Battle] " + e.Team + " phase, round " + e.RoundNumber);
            PhaseChanged?.Invoke(e.Team, e.RoundNumber);
            StateChanged?.Invoke();
        }

        private void OnEnded(BattleEndedEvent e) => Debug.Log("[Battle] ENDED: " + e.Outcome);

        // --- Floating combat text (rendered by BattleHud on the uGUI canvas) ---

        private void SpawnFloater(Vector3 world, VisualStep step)
        {
            if (hud == null) return;

            string text;
            Color color;
            if (!step.Hit)
            {
                text = "MISS";
                color = new Color(0.85f, 0.85f, 0.85f);
            }
            else if (step.Crit)
            {
                text = "CRIT " + step.Amount;
                color = new Color(1f, 0.85f, 0.2f);
            }
            else
            {
                text = step.Amount.ToString();
                color = new Color(1f, 0.45f, 0.4f);
            }

            hud.SpawnFloater(world + Vector3.up * 0.6f, text, color);
        }

        private enum VisualKind { Move, Damage, Died }

        private readonly struct VisualStep
        {
            public readonly VisualKind Kind;
            public readonly Unit Unit;
            public readonly Unit Other;
            public readonly IReadOnlyList<GridPos> Path;
            public readonly bool Hit;

            public readonly int Amount;
            public readonly bool Crit;
            public readonly int HpAfter;

            private VisualStep(VisualKind kind, Unit unit, Unit other, IReadOnlyList<GridPos> path, bool hit, int amount, bool crit, int hpAfter)
            {
                Kind = kind;
                Unit = unit;
                Other = other;
                Path = path;
                Hit = hit;
                Amount = amount;
                Crit = crit;
                HpAfter = hpAfter;
            }

            public static VisualStep Move(Unit u, IReadOnlyList<GridPos> path) =>
                new(VisualKind.Move, u, null, path, false, 0, false, 0);

            public static VisualStep Damage(Unit attacker, Unit defender, bool hit, int amount, bool crit, int hpAfter) =>
                new(VisualKind.Damage, attacker, defender, null, hit, amount, crit, hpAfter);

            public static VisualStep Died(Unit u) =>
                new(VisualKind.Died, u, null, null, false, 0, false, 0);
        }
    }
}
