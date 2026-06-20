using System.Collections.Generic;
using UnityEngine;
using FantacyCentry.Domain.Grid;
using FantacyCentry.Domain.Units;

namespace FantacyCentry.View.Battle
{
    /// <summary>
    /// Binds one Domain <see cref="Unit"/> to its scene GameObject. It owns no rules — it just
    /// renders what the Domain already decided: walk a path, swing, react, vanish. The
    /// <see cref="BattleRunner"/> calls these in response to Domain events, so the visual is always
    /// a replay of authoritative state.
    /// </summary>
    [RequireComponent(typeof(GridMover))]
    [RequireComponent(typeof(CharacterSpriteAnimator))]
    public sealed class UnitView : MonoBehaviour
    {
        private GridMover _mover;
        private CharacterSpriteAnimator _anim;

        /// <summary>The Domain unit this view represents (set by <see cref="Bind"/>).</summary>
        public Unit Unit { get; private set; }

        /// <summary>True while the sprite is still walking a queued path.</summary>
        public bool IsAnimating => _mover != null && _mover.IsMoving;

        private void Awake() => CacheComponents();

        private void CacheComponents()
        {
            if (_mover == null) _mover = GetComponent<GridMover>();
            if (_anim == null) _anim = GetComponent<CharacterSpriteAnimator>();
        }

        /// <summary>Attach a Domain unit and snap the sprite to its current cell.</summary>
        public void Bind(Unit unit)
        {
            CacheComponents();
            Unit = unit;
            // Keep the sprite visually centred on its tile (feet-pivot needs a ~half-cell lift).
            _mover.visualYOffset = 0.5f;
            _mover.SnapToCell(new Vector2Int(unit.Position.X, unit.Position.Y));
            FaceSouth();
        }

        /// <summary>Walk the full path (origin → destination inclusive); the origin cell is skipped.</summary>
        public void WalkPath(IReadOnlyList<GridPos> path)
        {
            if (path == null || path.Count < 2) return;
            var cells = new List<Vector2Int>(path.Count - 1);
            for (int i = 1; i < path.Count; i++) // skip origin (already standing there)
                cells.Add(new Vector2Int(path[i].X, path[i].Y));
            _mover.MoveTo(cells);
        }

        /// <summary>Turn to face a target cell (used right before an attack swing).</summary>
        public void FacePoint(GridPos target)
        {
            CacheComponents();
            GridPos from = Unit != null ? Unit.Position : new GridPos(
                Mathf.RoundToInt(transform.position.x),
                Mathf.RoundToInt(transform.position.y - _mover.visualYOffset));
            _anim.SetFacing(FacingFromDelta(target.X - from.X, target.Y - from.Y));
        }

        /// <summary>Play the attack one-shot; returns its duration in seconds.</summary>
        public float PlayAttack() => _anim.PlayOneShot(CharacterSpriteAnimator.Action.Attack);

        /// <summary>Play the hit/react one-shot; returns its duration in seconds.</summary>
        public float PlayHit() => _anim.PlayOneShot(CharacterSpriteAnimator.Action.Hit);

        /// <summary>Reset to the default south-facing idle (we don't persist facing between turns).</summary>
        public void FaceSouth()
        {
            CacheComponents();
            _anim.SetFacing(Facing.South);
        }

        /// <summary>Teleport the sprite to a cell (used when undoing a move).</summary>
        public void SnapTo(GridPos cell)
        {
            CacheComponents();
            _mover.SnapToCell(new Vector2Int(cell.X, cell.Y));
        }

        /// <summary>Remove a dead unit from view (no death clip in the rig yet, so just hide it).</summary>
        public void Die() => gameObject.SetActive(false);

        private static Facing FacingFromDelta(int dx, int dy)
        {
            if (Mathf.Abs(dx) >= Mathf.Abs(dy))
                return dx >= 0 ? Facing.East : Facing.West;
            return dy >= 0 ? Facing.North : Facing.South;
        }
    }
}
