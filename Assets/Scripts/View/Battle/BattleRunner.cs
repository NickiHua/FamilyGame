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
        /// <summary>Y-sort layer band so battle units always render above map objects (houses).</summary>
        private const int UnitLayerBias = 10000;

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

        [Header("Battle stage (cut to a side-view duel on each attack)")]
        [Tooltip("When on, every attack cuts to the bottom-of-screen duel演出 (Fire Emblem / 梦战 style). " +
                 "Turn off for fast in-place resolution on the map.")]
        public bool useBattleStage = true;
        [Tooltip("The director that plays the duel. Wired by BattleSceneBuilder.")]
        public BattleStageDirector stageDirector;

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

        /// <summary>Settle the visual HP for a unit (called by the stage director at the impact frame).</summary>
        public void SetDisplayHp(Unit unit, int hp) { if (unit != null) _displayHp[unit] = hp; }

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
            if (overlay != null) overlay.worldOrigin = mapGrid.Origin;

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
            var abilities = FantacyCentry.Domain.Units.Abilities.For(s.id);
            int maxMp = abilities.Count > 0 ? 20 : 0; // casters get an MP pool so skills/spells work
            var stats = new Stats(
                s.maxHp, maxMp, s.strength, s.magic, s.defense, s.resist,
                s.accuracy, s.evade, s.crit, s.move);
            return new Unit(s.id, s.team, stats)
            {
                Position = new GridPos(s.cell.x, s.cell.y),
                Weapon = s.weapon,
                MinRange = s.minRange,
                MaxRange = s.maxRange,
                Abilities = abilities,
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
            go.transform.position = new Vector3(mapGrid.Origin.x + s.cell.x, mapGrid.Origin.y + s.cell.y, 0f);

            // The demo arrow-key driver would fight our input; strip it from battle units.
            var demo = go.GetComponent<CharacterDemoController>();
            if (demo != null) Destroy(demo);
            // Characters always draw ABOVE map objects (houses): give their Y-sort a large layer
            // band so a unit is never hidden behind a building, while still sorting vs each other.
            var ysort = go.GetComponent<YSort>();
            if (ysort == null) ysort = go.AddComponent<YSort>();
            ysort.layerBias = UnitLayerBias;

            var view = go.GetComponent<UnitView>();
            if (view == null) view = go.AddComponent<UnitView>();
            var mover = go.GetComponent<GridMover>();
            if (mover != null) mover.worldOrigin = mapGrid.Origin;
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

        /// <summary>The ability currently being cast, so <see cref="OnDamaged"/> can tag its visual
        /// step with the right VFX (剑气/闪电) instead of a plain melee swing. Set only across the
        /// synchronous Execute of an ability command.</summary>
        private Ability _currentAbility;

        /// <summary>
        /// Cast <paramref name="ability"/> from <paramref name="caster"/> at <paramref name="target"/>
        /// (an enemy for damage skills, an ally for heals). Cast from the caster's current cell; no
        /// counter is provoked. Returns true if the cast was legal.
        /// </summary>
        public bool SubmitAbility(Unit caster, Unit target, Ability ability)
        {
            if (!CanAct() || caster == null || target == null || ability == null) return false;

            if (ability.IsHeal)
            {
                var cmd = new HealCommand(caster, target, ability);
                if (!cmd.Execute(State)) return false;
                if (ability.MapCast)
                    StartCoroutine(PlayMapHeal(caster, target, cmd.Healed, ability));
                else
                {
                    _queue.Enqueue(VisualStep.HealStep(caster, target, cmd.Healed, target.Hp, ability.VfxKey));
                    StartCoroutine(PlayQueued());
                }
                return true;
            }

            _currentAbility = ability;
            bool ok = new AbilityAttackCommand(caster, target, ability, _affinity, _rng).Execute(State);
            _currentAbility = null;
            if (!ok) return false;
            StartCoroutine(PlayQueued());
            return true;
        }

        /// <summary>Cast a MAP AOE ability (火球术) centred on <paramref name="center"/>, hitting every
        /// enemy in its footprint. Plays on the map (no battle-stage cut).</summary>
        public bool SubmitAbilityCell(Unit caster, GridPos center, Ability ability)
        {
            if (!CanAct() || caster == null || ability == null || ability.Aoe == AbilityAoe.Single) return false;
            var cmd = new AoeFireballCommand(caster, center, ability, _affinity, _rng);
            if (!cmd.Execute(State)) return false;
            StartCoroutine(PlayMapAoe(center, ability, cmd.Results));
            return true;
        }

        private Vector3 CellToWorld(GridPos cell) =>
            new(mapGrid.Origin.x + cell.X, mapGrid.Origin.y + cell.Y, 0f);

        /// <summary>Play a frame bank as a world SpriteRenderer at <paramref name="world"/>, sized to
        /// <paramref name="worldHeight"/> units, at <paramref name="alpha"/> opacity (semi-transparent heals).</summary>
        private IEnumerator PlayMapVfx(Sprite[] frames, Vector3 world, float worldHeight, float fps, float alpha)
        {
            if (frames == null || frames.Length == 0) { yield return new WaitForSeconds(0.3f); yield break; }
            var go = new GameObject("MapVfx");
            var sr = go.AddComponent<SpriteRenderer>();
            sr.sortingOrder = UnitLayerBias * 3; // above characters
            go.transform.position = world;
            float spf = 1f / Mathf.Max(1f, fps);
            foreach (Sprite s in frames)
            {
                if (s != null)
                {
                    sr.sprite = s;
                    float unitH = s.rect.height / s.pixelsPerUnit;
                    float sc = worldHeight / Mathf.Max(0.01f, unitH);
                    go.transform.localScale = new Vector3(sc, sc, 1f);
                }
                sr.color = new Color(1f, 1f, 1f, alpha);
                yield return new WaitForSeconds(spf);
            }
            Destroy(go);
        }

        private IEnumerator PlayMapHeal(Unit caster, Unit target, int healed, Ability ability)
        {
            _busy = true; StateChanged?.Invoke();
            UnitView tv = ViewFor(target);
            Vector3 w = tv != null ? tv.transform.position : CellToWorld(target.Position);
            BattleAudio.PlayHeal();
            // Semi-transparent heal glow ON the ally, rising from the feet.
            yield return PlayMapVfx(stageDirector != null ? stageDirector.BankFor(ability.VfxKey) : null,
                w, 2.4f, 14f, 0.6f);
            _displayHp[target] = target.Hp;
            if (hud != null) hud.SpawnFloater(w + Vector3.up * 0.8f, "+" + healed, new Color(0.4f, 0.95f, 0.5f));
            StateChanged?.Invoke();
            if (!State.IsOver && _turns.ActingTeamFinished())
                yield return EnemyTurn();
            _busy = false; StateChanged?.Invoke();
        }

        private IEnumerator PlayMapAoe(GridPos center, Ability ability, System.Collections.Generic.List<Domain.Battle.AoeFireballCommand.Hit> results)
        {
            _busy = true; StateChanged?.Invoke();
            Vector3 w = CellToWorld(center) + Vector3.up * 0.5f;
            BattleAudio.PlayMagic("fire");
            yield return PlayMapVfx(stageDirector != null ? stageDirector.BankFor(ability.VfxKey) : null,
                w, 3f, 16f, 1f);
            BattleAudio.PlayHit();
            foreach (var r in results)
            {
                if (r.Unit == null) continue;
                _displayHp[r.Unit] = r.HpAfter;
                UnitView v = ViewFor(r.Unit);
                Vector3 fw = v != null ? v.transform.position : CellToWorld(r.Unit.Position);
                if (hud != null)
                {
                    string t = !r.Landed ? "MISS" : (r.Crit ? "CRIT " + r.Dmg : r.Dmg.ToString());
                    Color c = !r.Landed ? new Color(0.85f, 0.85f, 0.85f) : new Color(1f, 0.5f, 0.45f);
                    hud.SpawnFloater(fw + Vector3.up * 0.6f, t, c);
                }
            }
            yield return DrainQueue(); // plays any deaths queued by the command
            StateChanged?.Invoke();
            if (!State.IsOver && _turns.ActingTeamFinished())
                yield return EnemyTurn();
            _busy = false; StateChanged?.Invoke();
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
                            BattleAudio.PlayFootstep();
                            v.WalkPath(step.Path);
                            float ft = 0f;
                            while (v.IsAnimating)
                            {
                                ft += Time.deltaTime;
                                if (ft >= 0.3f) { ft = 0f; BattleAudio.PlayFootstep(); }
                                yield return null;
                            }
                            v.FaceSouth();
                        }
                        if (stepPause > 0f) yield return new WaitForSeconds(stepPause);
                        break;
                    }
                    case VisualKind.Damage:
                    {
                        UnitView atk = ViewFor(step.Unit);
                        UnitView def = ViewFor(step.Other);

                        // --- Ability (剑气/闪电/冰锥): ranged cast, plays its VFX on the target, no counter ---
                        if (!string.IsNullOrEmpty(step.Vfx))
                        {
                            BattleAudio.PlayMagic(step.Vfx);
                            if (useBattleStage && stageDirector != null && atk != null && def != null)
                            {
                                var hit = new BattleStageDirector.Hit { Landed = step.Hit, Dmg = step.Amount, Crit = step.Crit, HpAfter = step.HpAfter };
                                yield return stageDirector.PlayAbility(atk, def, hit, step.Vfx, isHeal: false, speedMul: step.VfxSpeed);
                            }
                            else
                            {
                                if (atk != null) atk.FacePoint(step.Other.Position);
                                yield return new WaitForSeconds(0.25f);
                                if (def != null && step.Hit) def.PlayHit();
                                _displayHp[step.Other] = step.HpAfter;
                                if (def != null) SpawnFloater(def.transform.position, step);
                            }
                            if (stepPause > 0f) yield return new WaitForSeconds(stepPause);
                            break;
                        }

                        // --- Cut to the side-view duel stage (default) ---
                        if (useBattleStage && stageDirector != null && atk != null && def != null)
                        {
                            // Fold an immediately-following counter (same pair, swapped) into ONE duel.
                            bool hasCounter = _queue.Count > 0 && IsCounterOf(_queue.Peek(), step);
                            VisualStep counter = hasCounter ? _queue.Dequeue() : default;

                            var atkHit = new BattleStageDirector.Hit { Landed = step.Hit, Dmg = step.Amount, Crit = step.Crit, HpAfter = step.HpAfter };
                            var ctrHit = new BattleStageDirector.Hit { Landed = hasCounter && counter.Hit, Dmg = counter.Amount, Crit = counter.Crit, HpAfter = counter.HpAfter };
                            // The stage settles HP + pops floaters on impact via SettleHit → runner.SetDisplayHp.
                            yield return stageDirector.Play(atk, def, atkHit, hasCounter, ctrHit);
                            if (stepPause > 0f) yield return new WaitForSeconds(stepPause);
                            break;
                        }

                        // --- Fast in-place resolution on the map ---
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
                    case VisualKind.Heal:
                    {
                        UnitView caster = ViewFor(step.Unit);
                        UnitView tgt = ViewFor(step.Other);
                        BattleAudio.PlayHeal();
                        if (useBattleStage && stageDirector != null && caster != null && tgt != null)
                            yield return stageDirector.PlayAbility(caster, tgt, BattleStageDirector.Hit.Miss, step.Vfx, isHeal: true);
                        else
                            yield return new WaitForSeconds(0.35f);
                        _displayHp[step.Other] = step.HpAfter;
                        if (tgt != null && hud != null)
                            hud.SpawnFloater(tgt.transform.position + Vector3.up * 0.6f,
                                "+" + step.Amount, new Color(0.4f, 0.95f, 0.5f));
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
            string vfx = _currentAbility != null ? _currentAbility.VfxKey : null;
            float vfxSpeed = _currentAbility != null ? _currentAbility.VfxSpeedMul : 1f;
            _queue.Enqueue(VisualStep.Damage(e.Attacker, e.Defender, e.Result.IsHit, e.Result.Damage, e.Result.IsCrit, e.DefenderHpAfter, vfx, vfxSpeed));
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

        private enum VisualKind { Move, Damage, Died, Heal }

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
            public readonly string Vfx;    // ability VFX key (null = plain attack)
            public readonly bool IsHeal;
            public readonly float VfxSpeed; // ability VFX speed multiplier (1 = normal)

            private VisualStep(VisualKind kind, Unit unit, Unit other, IReadOnlyList<GridPos> path, bool hit, int amount, bool crit, int hpAfter, string vfx, bool isHeal, float vfxSpeed)
            {
                Kind = kind;
                Unit = unit;
                Other = other;
                Path = path;
                Hit = hit;
                Amount = amount;
                Crit = crit;
                HpAfter = hpAfter;
                Vfx = vfx;
                IsHeal = isHeal;
                VfxSpeed = vfxSpeed;
            }

            public static VisualStep Move(Unit u, IReadOnlyList<GridPos> path) =>
                new(VisualKind.Move, u, null, path, false, 0, false, 0, null, false, 1f);

            public static VisualStep Damage(Unit attacker, Unit defender, bool hit, int amount, bool crit, int hpAfter, string vfx = null, float vfxSpeed = 1f) =>
                new(VisualKind.Damage, attacker, defender, null, hit, amount, crit, hpAfter, vfx, false, vfxSpeed);

            public static VisualStep HealStep(Unit caster, Unit target, int amount, int hpAfter, string vfx) =>
                new(VisualKind.Heal, caster, target, null, true, amount, false, hpAfter, vfx, true, 1f);

            public static VisualStep Died(Unit u) =>
                new(VisualKind.Died, u, null, null, false, 0, false, 0, null, false, 1f);
        }
    }
}
