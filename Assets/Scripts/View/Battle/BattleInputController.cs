using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.EventSystems;
using FantacyCentry.Domain.Battle;
using FantacyCentry.Domain.Grid;
using FantacyCentry.Domain.Pathfinding;
using FantacyCentry.Domain.Units;

namespace FantacyCentry.View.Battle
{
    /// <summary>
    /// Mouse-driven SRPG selection on top of <see cref="BattleRunner"/>. Click an own unit to show
    /// its blue move range and gold attack targets; click a blue cell to move; click a highlighted
    /// foe to attack. Right-click / Esc cancels; Space / Enter ends the player phase. All legality
    /// is delegated to the Domain commands, so what you can click is exactly what the rules allow.
    /// </summary>
    public sealed class BattleInputController : MonoBehaviour
    {
        public BattleRunner runner;
        public RangeOverlay overlay;
        public Camera worldCamera;

        /// <summary>World position of cell (0,0); set from MapGrid.Origin so clicks map to the right cell.</summary>
        public Vector2 worldOrigin = Vector2.zero;

        /// <summary>The unit the player currently has selected (null when none). Read by the HUD.</summary>
        public Unit SelectedUnit => _selected;

        /// <summary>The unit currently under the mouse cursor (null when none / off-grid / busy).
        /// Read by the HUD to drive the unit info panel.</summary>
        public Unit HoveredUnit { get; private set; }

        /// <summary>Raised whenever the selection changes so the action menu can refresh.</summary>
        public event Action SelectionChanged;

        /// <summary>True when the selected unit is one the player may still act with this phase.</summary>
        public bool CanControlSelected() => _selected != null && IsControllable(_selected);

        /// <summary>UI hook: end the whole player phase (same as pressing Space).</summary>
        public void EndTurnFromUI()
        {
            if (runner == null || !runner.Ready || runner.IsBusy || runner.IsOver) return;
            if (runner.CurrentTurn != Team.Player) return;
            Deselect();
            runner.RequestEndTurn();
        }

        /// <summary>UI hook: standby the selected unit (same as pressing W).</summary>
        public void WaitFromUI() => WaitSelected();

        /// <summary>UI hook: the player picked an ability from the SKILL/MAGIC menu — enter
        /// targeting mode and highlight the legal targets (enemies for damage, allies for heal).</summary>
        public void BeginAbilityTargeting(Ability ability)
        {
            if (ability == null || _selected == null || !IsControllable(_selected)) return;
            _pendingAbility = ability;
            RefreshAbilityTargets();
            SelectionChanged?.Invoke();
        }

        /// <summary>Leave targeting mode and restore the normal move/attack overlay.</summary>
        public void CancelAbilityTargeting()
        {
            if (_pendingAbility == null) return;
            _pendingAbility = null;
            _abilityTargets.Clear();
            _abilityCells.Clear();
            _aoeCenter = null;
            RefreshOverlays();
            SelectionChanged?.Invoke();
        }

        private void RefreshAbilityTargets()
        {
            _abilityTargets.Clear();
            _abilityCells.Clear();
            if (overlay != null) overlay.Clear();
            Unit caster = _selected;
            BattleState state = runner.State;
            Ability ab = _pendingAbility;
            if (caster == null || state == null || ab == null) return;

            // AOE (火球): pick any CELL within range; the red range shows where it can be aimed.
            if (ab.Aoe != AbilityAoe.Single)
            {
                _abilityCells.UnionWith(CellsInRange(caster.Position, ab, state));
                if (overlay != null)
                {
                    // Stage A = aiming (red range). Stage B = a centre chosen: dim the range and
                    // paint the resolved footprint (orange) so the player can confirm with a 2nd click.
                    if (_aoeCenter.HasValue)
                    {
                        overlay.ShowRange(_abilityCells);
                        overlay.ShowAoeArea(AoeFootprint(_aoeCenter.Value, ab, state));
                    }
                    else
                    {
                        overlay.ShowRange(_abilityCells);
                    }
                    overlay.ShowSelection(caster.Position);
                }
                return;
            }

            IEnumerable<Unit> candidates = ab.Target == AbilityTarget.Enemy
                ? state.FoesOf(caster.Team)
                : state.AliveUnits.Where(u => !BattleState.AreEnemies(caster.Team, u.Team));

            var cells = new HashSet<GridPos>();
            foreach (Unit u in candidates)
            {
                int d = GridPos.ManhattanDistance(caster.Position, u.Position);
                if (d < ab.MinRange || d > ab.MaxRange) continue;
                _abilityTargets[u.Position] = u;
                cells.Add(u.Position);
            }

            if (overlay != null)
            {
                overlay.ShowRange(cells);            // red = valid targets this skill can point at
                overlay.ShowSelection(caster.Position);
            }
        }

        /// <summary>Every cell within an ability's min/max range of <paramref name="from"/>.</summary>
        private static IEnumerable<GridPos> CellsInRange(GridPos from, Ability ab, BattleState state)
        {
            for (int x = 0; x < state.Map.Width; x++)
                for (int y = 0; y < state.Map.Height; y++)
                {
                    var c = new GridPos(x, y);
                    int d = GridPos.ManhattanDistance(from, c);
                    if (d >= ab.MinRange && d <= ab.MaxRange) yield return c;
                }
        }

        /// <summary>The cells an AOE actually hits when centred on <paramref name="center"/>
        /// (currently a plus: centre + 4 orthogonal), clipped to the map.</summary>
        private static HashSet<GridPos> AoeFootprint(GridPos center, Ability ab, BattleState state)
        {
            var cells = new HashSet<GridPos> { center };
            if (ab.Aoe == AbilityAoe.Plus)
            {
                foreach (var (dx, dy) in new[] { (1, 0), (-1, 0), (0, 1), (0, -1) })
                {
                    var c = new GridPos(center.X + dx, center.Y + dy);
                    if (c.X >= 0 && c.X < state.Map.Width && c.Y >= 0 && c.Y < state.Map.Height)
                        cells.Add(c);
                }
            }
            return cells;
        }

        private static bool IsPointerOverUI()
        {
            EventSystem es = EventSystem.current;
            return es != null && es.IsPointerOverGameObject();
        }

        private Unit _selected;
        private readonly HashSet<GridPos> _moveCells = new();        // foe cell -> how we'd hit it: which reachable cell to stand on (Stop) and the foe itself.
        private readonly Dictionary<GridPos, FoePlan> _attackTargets = new();
        private bool _wasBusy;

        // Ability targeting: an ability chosen from the HUD, waiting for the player to click a target.
        private Ability _pendingAbility;
        private readonly Dictionary<GridPos, Unit> _abilityTargets = new();
        private readonly HashSet<GridPos> _abilityCells = new();   // valid centre cells for an AOE cast
        private GridPos? _aoeCenter;                                // AOE centre picked, awaiting confirm
        public bool IsTargetingAbility => _pendingAbility != null;

        // For right-click take-back: where the unit stood before an uncommitted move (null = nothing to undo).
        private GridPos? _undoCell;

        private readonly struct FoePlan
        {
            public readonly Unit Foe;
            public readonly GridPos Stop; // cell the unit moves to (== current cell if already in range)
            public FoePlan(Unit foe, GridPos stop) { Foe = foe; Stop = stop; }
        }

        private void Start()
        {
            if (worldCamera == null) worldCamera = Camera.main;
            if (overlay == null && runner != null) overlay = runner.overlay;
            if (runner != null) runner.StateChanged += OnStateChanged;
        }

        private void OnDestroy()
        {
            if (runner != null) runner.StateChanged -= OnStateChanged;
        }

        private void Update()
        {
            if (runner == null || !runner.Ready) return;

            // A modal overlay (e.g. the full-screen character detail) is open → freeze battlefield
            // interaction; the overlay handles its own dismissal.
            if (runner.hud != null && runner.hud.IsCharacterDetailOpen) return;

            // When the runner finishes animating, re-evaluate the current selection.
            if (_wasBusy && !runner.IsBusy) ReselectAfterAction();
            _wasBusy = runner.IsBusy;

            UpdateHover();

            if (runner.IsBusy || runner.IsOver) return;

            Keyboard kb = Keyboard.current;
            if (kb != null)
            {
                if (kb.escapeKey.wasPressedThisFrame) CancelOrUndo();
                if (kb.wKey.wasPressedThisFrame) { WaitSelected(); return; }
                if (kb.spaceKey.wasPressedThisFrame || kb.enterKey.wasPressedThisFrame)
                {
                    Deselect();
                    runner.RequestEndTurn();
                    return;
                }
            }

            Mouse mouse = Mouse.current;
            if (mouse == null) return;
            if (IsPointerOverUI()) return;   // clicks on the command panel / buttons are not world clicks
            if (mouse.rightButton.wasPressedThisFrame) { CancelOrUndo(); return; }
            if (mouse.leftButton.wasPressedThisFrame) HandleClick(ScreenToCell(mouse.position.ReadValue()));
        }

        private void HandleClick(GridPos cell)
        {
            BattleState state = runner.State;
            if (state == null) return;   // battle not ready / already torn down

            // 0) In ability-targeting mode: click a valid target to cast, anything else cancels.
            if (_pendingAbility != null)
            {
                // AOE (火球): two-stage. 1st click on a valid centre previews the effect area;
                // 2nd click (on that centre / its footprint) fires. Clicking a different valid
                // centre re-aims. Right-click take-back is handled in CancelOrUndo.
                if (_pendingAbility.Aoe != AbilityAoe.Single)
                {
                    if (_selected == null) { CancelAbilityTargeting(); return; }

                    if (_aoeCenter.HasValue)
                    {
                        var footprint = AoeFootprint(_aoeCenter.Value, _pendingAbility, state);
                        if (cell == _aoeCenter.Value || footprint.Contains(cell))
                        {
                            // Confirm: fire at the previewed centre.
                            Ability ab = _pendingAbility;
                            GridPos center = _aoeCenter.Value;
                            _pendingAbility = null; _abilityCells.Clear(); _aoeCenter = null;
                            runner.SubmitAbilityCell(_selected, center, ab);
                            return;
                        }
                        if (_abilityCells.Contains(cell)) { _aoeCenter = cell; RefreshAbilityTargets(); return; }
                        // Click outside range: drop the preview but stay in aiming mode.
                        _aoeCenter = null; RefreshAbilityTargets();
                        return;
                    }

                    if (_abilityCells.Contains(cell)) { _aoeCenter = cell; RefreshAbilityTargets(); }
                    else CancelAbilityTargeting();
                    return;
                }
                if (_selected != null && _abilityTargets.TryGetValue(cell, out Unit tgt))
                {
                    Ability ab = _pendingAbility;
                    _pendingAbility = null;
                    _abilityTargets.Clear();
                    runner.SubmitAbility(_selected, tgt, ab);
                }
                else
                {
                    CancelAbilityTargeting();
                }
                return;
            }

            // 1) Selected + clicked an attackable foe -> attack (moving into range first if needed).
            if (_selected != null && _attackTargets.TryGetValue(cell, out FoePlan plan))
            {
                if (plan.Stop == _selected.Position)
                {
                    runner.SubmitAttack(_selected, plan.Foe);
                }
                else
                {
                    // Move-into-range + strike is a single committed action -> nothing to undo.
                    _undoCell = null;
                    runner.SubmitMoveThenAttack(_selected, plan.Stop, plan.Foe);
                }
                return;
            }

            // 2) Selected + clicked a reachable blue cell -> move (remember where we came from so a
            //    right-click can take it back).
            if (_selected != null && _moveCells.Contains(cell))
            {
                GridPos before = _selected.Position;
                if (runner.SubmitMove(_selected, cell)) _undoCell = before;
                return;
            }

            // 3) Clicked one of my own controllable units -> (re)select it.
            Unit clicked = state.UnitAt(cell);
            if (clicked != null && IsControllable(clicked))
            {
                Select(clicked);
                return;
            }

            // 4) Empty / invalid -> clear.
            Deselect();
        }

        /// <summary>Right-click / Esc: undo an uncommitted move if there is one, otherwise deselect.</summary>
        private void CancelOrUndo()
        {
            // While previewing an AOE, right-click first drops the preview (back to aiming),
            // and only then cancels the whole ability on a second right-click.
            if (_pendingAbility != null && _aoeCenter.HasValue) { _aoeCenter = null; RefreshAbilityTargets(); return; }
            if (_pendingAbility != null) { CancelAbilityTargeting(); return; }
            if (_selected != null && _undoCell.HasValue && _selected.TurnState == TurnState.Moved)
            {
                runner.UndoMove(_selected, _undoCell.Value);
                _undoCell = null;
                RefreshOverlays();
                return;
            }
            Deselect();
        }

        /// <summary>Standby ("待机"): end the selected unit's turn without attacking.</summary>
        private void WaitSelected()
        {
            if (_selected == null || !IsControllable(_selected)) return;
            if (runner.SubmitWait(_selected)) Deselect();
        }

        private bool IsControllable(Unit u) =>
            u != null && u.IsAlive && u.TurnState != TurnState.Done &&
            BattleState.ActsInPhase(runner.CurrentTurn, u.Team) &&
            runner.CurrentTurn == Team.Player;

        private void Select(Unit unit)
        {
            _selected = unit;
            _undoCell = null;
            RefreshOverlays();
            SelectionChanged?.Invoke();
        }

        private void Deselect()
        {
            _selected = null;
            _undoCell = null;
            _pendingAbility = null;
            _moveCells.Clear();
            _attackTargets.Clear();
            _abilityTargets.Clear();
            _abilityCells.Clear();
            _aoeCenter = null;
            if (overlay != null) overlay.Clear();
            SelectionChanged?.Invoke();
        }

        private void ReselectAfterAction()
        {
            if (_selected == null) return;
            if (!IsControllable(_selected)) { Deselect(); return; }
            RefreshOverlays();
        }

        private void RefreshOverlays()
        {
            _moveCells.Clear();
            _attackTargets.Clear();
            if (overlay != null) overlay.Clear();
            if (_selected == null || runner.State == null) return;

            BattleState state = runner.State;

            // Cells the unit could STOP on this turn. If it has already moved, the only stop is
            // where it now stands (no further movement allowed).
            Dictionary<GridPos, int> reachable;
            if (_selected.TurnState == TurnState.Idle)
            {
                IPassability pass = state.PassabilityFor(_selected.Team);
                reachable = MovementRange.Compute(_selected.Position, _selected.Stats.Move, pass);
            }
            else
            {
                reachable = new Dictionary<GridPos, int> { [_selected.Position] = 0 };
            }

            // Blue = every reachable stop except where we already are.
            foreach (GridPos c in reachable.Keys)
                if (c != _selected.Position)
                    _moveCells.Add(c);

            // Red = the ring the unit could strike from ANY reachable stop (AttackRange already
            // excludes the stops themselves, so the red sits just outside the blue).
            HashSet<GridPos> attackRing = AttackRange.Compute(
                reachable.Keys, _selected.MinRange, _selected.MaxRange,
                state.Map.Width, state.Map.Height);

            // For each foe inside that threat, pick the cheapest stop we can attack it from (preferring
            // staying put). That cell is where a one-click move-and-attack will send the unit.
            foreach (Unit foe in state.FoesOf(_selected.Team))
            {
                GridPos bestStop = default;
                int bestCost = int.MaxValue;
                foreach (KeyValuePair<GridPos, int> stop in reachable)
                {
                    int d = GridPos.ManhattanDistance(stop.Key, foe.Position);
                    if (d < _selected.MinRange || d > _selected.MaxRange) continue;
                    if (stop.Value < bestCost) { bestCost = stop.Value; bestStop = stop.Key; }
                }
                if (bestCost != int.MaxValue)
                    _attackTargets[foe.Position] = new FoePlan(foe, bestStop);
            }

            if (overlay != null)
            {
                overlay.ShowMove(_moveCells);
                overlay.ShowAttack(attackRing);
                overlay.ShowSelection(_selected.Position);
            }
        }

        private void OnStateChanged()
        {
            // A new phase or end state may have invalidated the selection.
            if (_selected != null && !IsControllable(_selected)) Deselect();
        }

        private GridPos ScreenToCell(Vector2 screen)
        {
            Camera cam = worldCamera != null ? worldCamera : Camera.main;
            Vector3 world = cam.ScreenToWorldPoint(new Vector3(screen.x, screen.y, -cam.transform.position.z));
            return new GridPos(Mathf.RoundToInt(world.x - worldOrigin.x), Mathf.RoundToInt(world.y - worldOrigin.y));
        }

        /// <summary>Follow the mouse with a hover cursor, hidden while busy/over or off the grid.
        /// Also records the unit under the cursor so the HUD can show its info panel.</summary>
        private void UpdateHover()
        {
            Mouse mouse = Mouse.current;
            BattleState state = runner.State;
            if (mouse == null || state == null || runner.IsBusy || runner.IsOver)
            {
                HoveredUnit = null;
                overlay?.HideHover();
                return;
            }

            GridPos cell = ScreenToCell(mouse.position.ReadValue());
            if (cell.X < 0 || cell.Y < 0 || cell.X >= state.Map.Width || cell.Y >= state.Map.Height)
            {
                HoveredUnit = null;
                overlay?.HideHover();
                return;
            }

            HoveredUnit = state.UnitAt(cell);
            overlay?.ShowHover(cell);
        }
    }
}
