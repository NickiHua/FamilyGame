using System.Collections.Generic;
using UnityEngine;
using FantacyCentry.Domain.Grid;

namespace FantacyCentry.View.Battle
{
    /// <summary>
    /// Draws the SRPG tile highlights: blue = reachable move cells, gold = attackable cells,
    /// a frame on the selected unit. Pools flat sprites placed at cell positions (1 cell = 1 unit).
    /// Sprites are scaled to exactly one world unit regardless of their import PPU, and given a
    /// sorting order below every unit but above the map background.
    /// </summary>
    public sealed class RangeOverlay : MonoBehaviour
    {
        [Header("Tile sprites (Assets/Art/UI/range/)")]
        public Sprite moveTile;
        public Sprite attackTile;
        public Sprite selectFrame;

        [Tooltip("Frame drawn under the mouse cursor as it moves over the grid. " +
                 "Falls back to selectFrame when left empty.")]
        public Sprite hoverCursor;

        [Tooltip("Tint applied to the hover cursor so it reads differently from the " +
                 "solid gold selection frame (a faint, semi-transparent highlight).")]
        public Color hoverTint = new Color(1f, 1f, 1f, 0.55f);

        [Tooltip("Sorting order for ground highlights. Must be below every unit (units Y-sort to " +
                 "negative orders) yet above the map background (-5000).")]
        public int tileSortingOrder = -4000;

        /// <summary>World position of cell (0,0); set from MapGrid.Origin so tiles align to the map.</summary>
        public Vector2 worldOrigin = Vector2.zero;

        private readonly List<SpriteRenderer> _pool = new();
        private int _active;
        private SpriteRenderer _hover;

        /// <summary>Hide every tile (call before drawing a new selection).</summary>
        public void Clear()
        {
            for (int i = 0; i < _active; i++)
                _pool[i].gameObject.SetActive(false);
            _active = 0;
        }

        public void ShowMove(IEnumerable<GridPos> cells) => Paint(cells, moveTile, tileSortingOrder);

        public void ShowAttack(IEnumerable<GridPos> cells) => Paint(cells, attackTile, tileSortingOrder + 1);

        public void ShowSelection(GridPos cell)
        {
            if (selectFrame == null) return;
            Place(cell, selectFrame, tileSortingOrder + 2);
        }

        /// <summary>Move the hover cursor to <paramref name="cell"/> (creating it on first use).</summary>
        public void ShowHover(GridPos cell)
        {
            Sprite sprite = hoverCursor != null ? hoverCursor : selectFrame;
            if (sprite == null) return;

            if (_hover == null)
            {
                var go = new GameObject("HoverCursor");
                go.transform.SetParent(transform, false);
                _hover = go.AddComponent<SpriteRenderer>();
            }

            _hover.gameObject.SetActive(true);
            _hover.sprite = sprite;
            _hover.color = hoverTint;
            _hover.sortingOrder = tileSortingOrder + 3; // above the selection frame
            Transform t = _hover.transform;
            t.position = new Vector3(worldOrigin.x + cell.X, worldOrigin.y + cell.Y, 0f);

            float w = sprite.bounds.size.x;
            float h = sprite.bounds.size.y;
            t.localScale = new Vector3(
                w > 0f ? 1f / w : 1f,
                h > 0f ? 1f / h : 1f,
                1f);
        }

        /// <summary>Hide the hover cursor (mouse left the grid).</summary>
        public void HideHover()
        {
            if (_hover != null) _hover.gameObject.SetActive(false);
        }

        private void Paint(IEnumerable<GridPos> cells, Sprite sprite, int order)
        {
            if (sprite == null || cells == null) return;
            foreach (GridPos c in cells) Place(c, sprite, order);
        }

        private void Place(GridPos cell, Sprite sprite, int order)
        {
            SpriteRenderer sr = Next();
            sr.sprite = sprite;
            sr.sortingOrder = order;
            Transform t = sr.transform;
            t.position = new Vector3(worldOrigin.x + cell.X, worldOrigin.y + cell.Y, 0f);

            // Scale so the sprite covers exactly one cell no matter its import PPU.
            float w = sprite.bounds.size.x;
            float h = sprite.bounds.size.y;
            t.localScale = new Vector3(
                w > 0f ? 1f / w : 1f,
                h > 0f ? 1f / h : 1f,
                1f);
        }

        private SpriteRenderer Next()
        {
            SpriteRenderer sr;
            if (_active < _pool.Count)
            {
                sr = _pool[_active];
                sr.gameObject.SetActive(true);
            }
            else
            {
                var go = new GameObject("RangeTile");
                go.transform.SetParent(transform, false);
                sr = go.AddComponent<SpriteRenderer>();
                _pool.Add(sr);
            }
            _active++;
            return sr;
        }
    }
}
