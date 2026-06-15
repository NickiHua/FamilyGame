using UnityEngine;

namespace FantacyCentry.View
{
    /// <summary>
    /// Smoothly keeps the camera centred on a target (the player unit) so you can walk
    /// across a map larger than one screen. Pixel-art friendly: follows in world space and
    /// lets the Pixel Perfect Camera handle snapping.
    /// </summary>
    public class CameraFollow : MonoBehaviour
    {
        [Tooltip("What to keep centred (usually the player character).")]
        public Transform target;

        [Tooltip("Seconds-ish smoothing. 0 = snap instantly.")]
        public float smoothTime = 0.15f;

        private Vector3 _velocity;

        private void LateUpdate()
        {
            if (target == null) return;

            Vector3 goal = new(target.position.x, target.position.y, transform.position.z);
            transform.position = smoothTime <= 0f
                ? goal
                : Vector3.SmoothDamp(transform.position, goal, ref _velocity, smoothTime);
        }
    }
}
