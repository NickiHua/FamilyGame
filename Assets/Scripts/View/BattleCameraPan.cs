using UnityEngine;
using UnityEngine.InputSystem;

namespace FantacyCentry.View
{
    /// <summary>
    /// SRPG-style camera panning for the battle scene: push the mouse cursor against a
    /// screen edge (or hold the arrow keys) to scroll the view across a map larger than
    /// one screen. Movement is clamped to the map bounds so you can never pan into the
    /// void. WASD is intentionally left free because the battle input uses W for standby.
    /// </summary>
    public class BattleCameraPan : MonoBehaviour
    {
        [Tooltip("Camera to move. Defaults to the camera on this object, then Camera.main.")]
        public Camera cam;

        [Tooltip("How many pixels in from each screen edge trigger panning.")]
        public float edgeThicknessPx = 16f;

        [Tooltip("Pan speed in world units per second.")]
        public float panSpeed = 12f;

        [Tooltip("Hold the arrow keys to pan as well (WASD is reserved for unit input).")]
        public bool enableArrowKeys = true;

        [Tooltip("Only edge-scroll while the cursor is inside the game view.")]
        public bool requireCursorInside = true;

        [Header("Map bounds (world units)")]
        [Tooltip("Bottom-left corner of the pannable area.")]
        public Vector2 boundsMin = new(-0.5f, -0.5f);

        [Tooltip("Top-right corner of the pannable area.")]
        public Vector2 boundsMax = new(31.5f, 31.5f);

        private void Awake()
        {
            if (cam == null) cam = GetComponent<Camera>();
            if (cam == null) cam = Camera.main;
        }

        private void Update()
        {
            if (cam == null) return;

            Vector2 dir = Vector2.zero;

            Mouse mouse = Mouse.current;
            if (mouse != null)
            {
                Vector2 mp = mouse.position.ReadValue();
                float w = Screen.width;
                float h = Screen.height;
                bool inside = mp.x >= 0f && mp.x <= w && mp.y >= 0f && mp.y <= h;
                if (!requireCursorInside || inside)
                {
                    if (mp.x <= edgeThicknessPx) dir.x -= 1f;
                    else if (mp.x >= w - edgeThicknessPx) dir.x += 1f;
                    // Input System screen coords: y = 0 is the BOTTOM of the window.
                    if (mp.y <= edgeThicknessPx) dir.y -= 1f;
                    else if (mp.y >= h - edgeThicknessPx) dir.y += 1f;
                }
            }

            if (enableArrowKeys)
            {
                Keyboard kb = Keyboard.current;
                if (kb != null)
                {
                    if (kb.leftArrowKey.isPressed) dir.x -= 1f;
                    if (kb.rightArrowKey.isPressed) dir.x += 1f;
                    if (kb.downArrowKey.isPressed) dir.y -= 1f;
                    if (kb.upArrowKey.isPressed) dir.y += 1f;
                }
            }

            if (dir == Vector2.zero) return;
            if (dir.sqrMagnitude > 1f) dir = dir.normalized;

            Vector3 pos = transform.position + (Vector3)(dir * (panSpeed * Time.deltaTime));
            transform.position = ClampToBounds(pos);
        }

        private Vector3 ClampToBounds(Vector3 pos)
        {
            float halfY = cam.orthographicSize;
            float halfX = halfY * cam.aspect;

            float minX = boundsMin.x + halfX;
            float maxX = boundsMax.x - halfX;
            float minY = boundsMin.y + halfY;
            float maxY = boundsMax.y - halfY;

            // If the map is narrower than the view on an axis, lock to its centre.
            pos.x = minX <= maxX ? Mathf.Clamp(pos.x, minX, maxX) : (boundsMin.x + boundsMax.x) * 0.5f;
            pos.y = minY <= maxY ? Mathf.Clamp(pos.y, minY, maxY) : (boundsMin.y + boundsMax.y) * 0.5f;
            return pos;
        }
    }
}
