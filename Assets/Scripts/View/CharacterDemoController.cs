using UnityEngine;
using UnityEngine.InputSystem;

namespace FantacyCentry.View
{
    /// <summary>
    /// Phase-1 manual test driver: walk the character one tile per arrow-key press,
    /// and trigger Attack / Hit one-shots. Uses the new Input System (the project's
    /// Active Input Handling). Remove or disable once real battle input exists.
    /// </summary>
    [RequireComponent(typeof(GridMover))]
    public class CharacterDemoController : MonoBehaviour
    {
        [Tooltip("Optional logic grid. When set, the unit refuses to step onto blocked cells " +
                 "(water/cliff/building/wall). Leave null to walk freely.")]
        public MapGrid map;

        private GridMover _mover;
        private CharacterSpriteAnimator _anim;

        private void Awake()
        {
            _mover = GetComponent<GridMover>();
            _anim = GetComponent<CharacterSpriteAnimator>();
        }

        private void Update()
        {
            Keyboard kb = Keyboard.current;
            if (kb == null) return;

            if (!_mover.IsMoving)
            {
                Vector2Int step = Vector2Int.zero;
                if (kb.upArrowKey.wasPressedThisFrame) step = Vector2Int.up;
                else if (kb.downArrowKey.wasPressedThisFrame) step = Vector2Int.down;
                else if (kb.leftArrowKey.wasPressedThisFrame) step = Vector2Int.left;
                else if (kb.rightArrowKey.wasPressedThisFrame) step = Vector2Int.right;

                if (step != Vector2Int.zero)
                {
                    Vector2Int target = _mover.Cell + step;
                    // Always face the way we tried to move, even when blocked.
                    if (map != null && !map.IsWalkable(target))
                        _anim.SetFacing(FacingFromStep(step));
                    else
                        _mover.MoveTo(target);
                }
            }

            if (kb.spaceKey.wasPressedThisFrame)
                _anim.PlayOneShot(CharacterSpriteAnimator.Action.Attack);
            if (kb.hKey.wasPressedThisFrame)
                _anim.PlayOneShot(CharacterSpriteAnimator.Action.Hit);
        }

        private static Facing FacingFromStep(Vector2Int step)
        {
            if (step.x != 0) return step.x > 0 ? Facing.East : Facing.West;
            return step.y > 0 ? Facing.North : Facing.South;
        }
    }
}
