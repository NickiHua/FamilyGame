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
                    _mover.MoveTo(_mover.Cell + step);
            }

            if (kb.spaceKey.wasPressedThisFrame)
                _anim.PlayOneShot(CharacterSpriteAnimator.Action.Attack);
            if (kb.hKey.wasPressedThisFrame)
                _anim.PlayOneShot(CharacterSpriteAnimator.Action.Hit);
        }
    }
}
