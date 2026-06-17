using System;
using System.Collections.Generic;
using UnityEngine;

namespace FantacyCentry.View
{
    /// <summary>
    /// Moves a unit cell-by-cell across the grid with smooth interpolation between cells,
    /// driving facing + walk state on <see cref="CharacterSpriteAnimator"/>.
    ///
    /// Phase-1 visual mover only (no Domain dependency). With PPU = 48 and 1 unit = 1 tile,
    /// <see cref="cellSize"/> stays 1.
    /// </summary>
    [RequireComponent(typeof(CharacterSpriteAnimator))]
    public class GridMover : MonoBehaviour
    {
        [Tooltip("World units per grid tile. With PPU=48 (1 unit = 1 tile) keep this at 1.")]
        public float cellSize = 1f;

        [Tooltip("Movement speed in tiles per second.")]
        public float tilesPerSecond = 4f;

        [Tooltip("Vertical visual offset (in world units) added to the sprite within a cell. " +
                 "~0.5 centers the sprite on the tile (sprite pivot sits at the cell, feet hang low). " +
                 "Tune live in the Inspector; does not affect logic cell.")]
        public float visualYOffset = 0.5f;

        private CharacterSpriteAnimator _anim;
        private readonly Queue<Vector2Int> _path = new();

        private Vector2Int _cell;
        private Vector3 _segStart, _segEnd;
        private float _segT, _segDuration;
        private bool _moving;

        /// <summary>Raised when the queued path is fully consumed.</summary>
        public event Action Arrived;

        public Vector2Int Cell => _cell;
        public bool IsMoving => _moving;

        private void Awake()
        {
            _anim = GetComponent<CharacterSpriteAnimator>();
            _cell = WorldToCell(transform.position);
            transform.position = CellToWorld(_cell);
        }

        /// <summary>Queue a single destination cell (one step or straight segment).</summary>
        public void MoveTo(Vector2Int target) => MoveTo(new[] { target });

        /// <summary>Queue an ordered sequence of cells to walk through.</summary>
        public void MoveTo(IEnumerable<Vector2Int> cells)
        {
            _path.Clear();
            foreach (Vector2Int c in cells) _path.Enqueue(c);
            if (!_moving) BeginNextSegment();
        }

        private void BeginNextSegment()
        {
            if (_path.Count == 0)
            {
                _moving = false;
                _anim.SetMoving(false);
                Arrived?.Invoke();
                return;
            }

            Vector2Int next = _path.Dequeue();
            Vector2Int delta = next - _cell;
            if (delta != Vector2Int.zero)
                _anim.SetFacing(FacingFromDelta(delta));

            _segStart = CellToWorld(_cell);
            _segEnd = CellToWorld(next);
            _cell = next;

            float distance = Vector3.Distance(_segStart, _segEnd);
            _segDuration = Mathf.Max(0.0001f, distance / Mathf.Max(0.0001f, tilesPerSecond * cellSize));
            _segT = 0f;
            _moving = true;
            _anim.SetMoving(true);
        }

        private void Update()
        {
            if (_moving)
            {
                _segT += Time.deltaTime / _segDuration;
                if (_segT >= 1f)
                    BeginNextSegment();
            }

            // Recompute the rendered position every frame so the visual offset can be
            // tuned live in the Inspector and is applied even while standing still.
            Vector3 basePos = _moving
                ? Vector3.Lerp(_segStart, _segEnd, Mathf.Clamp01(_segT))
                : CellToWorld(_cell);
            transform.position = new Vector3(basePos.x, basePos.y + visualYOffset, basePos.z);
        }

        private Vector2Int WorldToCell(Vector3 world) =>
            new(Mathf.RoundToInt(world.x / cellSize), Mathf.RoundToInt(world.y / cellSize));

        private Vector3 CellToWorld(Vector2Int cell) =>
            new(cell.x * cellSize, cell.y * cellSize, transform.position.z);

        private static Facing FacingFromDelta(Vector2Int d)
        {
            if (Mathf.Abs(d.x) >= Mathf.Abs(d.y))
                return d.x >= 0 ? Facing.East : Facing.West;
            return d.y >= 0 ? Facing.North : Facing.South;
        }
    }
}
