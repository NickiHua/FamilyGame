using UnityEngine;

namespace FantacyCentry.View
{
    /// <summary>
    /// Depth-sorts a sprite by its foot Y so that, once buildings/objects are their own
    /// sprites, a unit standing lower on screen draws in front and one standing higher
    /// draws behind (top-down occlusion).
    ///
    /// NOTE for the M1 demo: the battlefield is one flat painted background, so there is
    /// no separate object sprite to be occluded BY yet — the character simply renders
    /// above the background. This component puts the mechanism in place; real occlusion
    /// arrives when houses/trees become sprites (see the layered framework: logic JSON +
    /// base map + object sprites).
    /// </summary>
    [RequireComponent(typeof(SpriteRenderer))]
    public class YSort : MonoBehaviour
    {
        [Tooltip("Sorting precision per world unit. Higher = finer ordering.")]
        public int unitsToOrder = 100;

        [Tooltip("Y offset of the sprite's 'foot' from its pivot, in world units.")]
        public float footOffset = 0f;

        [Tooltip("Constant added on top of the Y-sort value, used as a coarse LAYER band. " +
                 "Map objects (houses) keep 0; characters use a large value so a unit always " +
                 "draws ABOVE houses (never hidden behind one), while units still Y-sort against " +
                 "each OTHER inside their band.")]
        public int layerBias = 0;

        private SpriteRenderer _sr;

        private void Awake() => _sr = GetComponent<SpriteRenderer>();

        private void LateUpdate()
        {
            float footY = transform.position.y + footOffset;
            _sr.sortingOrder = layerBias + Mathf.RoundToInt(-footY * unitsToOrder);
        }
    }
}
