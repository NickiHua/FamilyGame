using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;
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

        private Unit _selected;
        private readonly HashSet<GridPos> _moveCells = new();        // foe cell -> how we'd hit it: which reachable cell to stand on (Stop) and the foe itself.
        private readonly Dictionary<GridPos, FoePlan> _attackTargets = new();
        private bool _wasBusy;

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
            if (mouse.rightButton.wasPressedThisFrame) { CancelOrUndo(); return; }
            if (mouse.leftButton.wasPressedThisFrame) HandleClick(ScreenToCell(mouse.position.ReadValue()));
        }

        private void HandleClick(GridPos cell)
        {
            BattleState state = runner.State;

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
            _moveCells.Clear();
            _attackTargets.Clear();
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
            return new GridPos(Mathf.RoundToInt(world.x), Mathf.RoundToInt(world.y));
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
