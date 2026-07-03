using UnityEngine;

namespace FantacyCentry.View
{
    /// <summary>
    /// Marks a map object (house / tree / rock) as a movement OBSTACLE. The Stage1
    /// <see cref="FantacyCentry.EditorTools.MapExporter"/> stamps every cell under this
    /// footprint as Building ('B', non-walkable) into Assets/Art/Maps/stage1_map.json,
    /// so the painted-tilemap export and the pathfinding blocking stay in sync (no more
    /// hand-edited JSON that gets wiped on the next export).
    ///
    /// Footprint defaults to the object's <see cref="SpriteRenderer"/> bounds: a 256px
    /// sprite imported at PPU 64 spans 4x4 world units = 4x4 cells. Override with
    /// <see cref="size"/> to block fewer cells (e.g. leave the doorway row walkable),
    /// and nudge with <see cref="offset"/>.
    ///
    /// Coordinate convention matches the exporter: after the tilemap is snapped so its
    /// bottom-left cell sits at world (0,0), cell (cx,cy) covers world [cx,cx+1]x[cy,cy+1].
    /// </summary>
    [DisallowMultipleComponent]
    public class MapObstacle : MonoBehaviour
    {
        [Tooltip("Footprint in CELLS (width, height). (0,0) = auto from the SpriteRenderer bounds.")]
        public Vector2Int size = Vector2Int.zero;

        [Tooltip("Shift the footprint by this many cells (x = right, y = up). " +
                 "e.g. (0,1) raises it one row to leave the front doorway walkable.")]
        public Vector2Int offset = Vector2Int.zero;

        [Tooltip("Draw the blocked footprint in the Scene view when selected.")]
        public bool drawGizmo = true;

        /// <summary>
        /// Blocked cells in world-cell coords (cell (0,0) = world [0,1]x[0,1]).
        /// Footprint is centred horizontally on the sprite and anchored on its base.
        /// </summary>
        public void GetFootprint(out int leftCell, out int bottomCell, out int width, out int height)
        {
            var sr = GetComponent<SpriteRenderer>();
            Vector3 minCorner;
            float worldW, worldH;
            if (sr != null && sr.sprite != null)
            {
                Bounds b = sr.bounds;
                minCorner = b.min;
                worldW = b.size.x;
                worldH = b.size.y;
            }
            else
            {
                minCorner = transform.position;
                worldW = 1f;
                worldH = 1f;
            }

            width = size.x > 0 ? size.x : Mathf.Max(1, Mathf.RoundToInt(worldW));
            height = size.y > 0 ? size.y : Mathf.Max(1, Mathf.RoundToInt(worldH));

            float centerX = minCorner.x + worldW * 0.5f;
            leftCell = Mathf.FloorToInt(centerX - width * 0.5f + 0.5f) + offset.x;
            bottomCell = Mathf.FloorToInt(minCorner.y + 0.5f) + offset.y;
        }

#if UNITY_EDITOR
        private void OnDrawGizmosSelected()
        {
            if (!drawGizmo) return;
            GetFootprint(out int lc, out int bc, out int w, out int h);
            Gizmos.color = new Color(1f, 0.3f, 0.2f, 0.4f);
            for (int dx = 0; dx < w; dx++)
                for (int dy = 0; dy < h; dy++)
                    Gizmos.DrawCube(
                        new Vector3(lc + dx + 0.5f, bc + dy + 0.5f, 0f),
                        new Vector3(0.9f, 0.9f, 0.01f));
        }
#endif
    }
}
