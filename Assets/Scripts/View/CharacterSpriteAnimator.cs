using System;
using System.Collections.Generic;
using UnityEngine;

namespace FantacyCentry.View
{
    /// <summary>
    /// Lightweight frame-by-frame sprite animator for PixelLab character sheets.
    ///
    /// Why not Unity's Animator/AnimationClip (spec §2 tech table)?
    /// For the M1 art-pipeline slice we drive frames in code so the whole rig can be
    /// generated from sprite folders without any hand-authored .anim/.controller assets
    /// or Unity GUI clicking. This is an intentional, reversible deviation — see
    /// docs decision log. We can swap to Animator later without touching GridMover.
    ///
    /// Stores only South/East/North clips; West reuses East with flipX (spec §5.2).
    /// </summary>
    [RequireComponent(typeof(SpriteRenderer))]
    public class CharacterSpriteAnimator : MonoBehaviour
    {
        public enum Action { Idle, Walk, Attack, Hit }
        public enum Dir3 { South, East, North }

        [Serializable]
        public class Clip
        {
            public Action action;
            public Dir3 dir;
            public float fps = 10f;
            public bool loop = true;
            public Sprite[] frames;
        }

        [SerializeField] private List<Clip> clips = new();

        private SpriteRenderer _sr;
        private Facing _facing = Facing.South;
        private bool _moving;

        private Clip _current;
        private float _timer;
        private int _frameIndex;

        private Action? _oneShot;
        private float _oneShotEnd;

        private void Awake()
        {
            _sr = GetComponent<SpriteRenderer>();
        }

        /// <summary>Editor-tool hook: inject the generated clip library.</summary>
        public void Configure(List<Clip> generated) => clips = generated;

        public void SetFacing(Facing f) => _facing = f;
        public void SetMoving(bool m) => _moving = m;

        /// <summary>Play a non-looping action (Attack/Hit) once. Returns its duration in seconds.</summary>
        public float PlayOneShot(Action action)
        {
            _oneShot = action;
            Clip clip = Resolve(action, ToDir3(_facing, out _));
            float duration = (clip != null && clip.frames != null && clip.frames.Length > 0)
                ? clip.frames.Length / Mathf.Max(1f, clip.fps)
                : 0.25f;
            _oneShotEnd = Time.time + duration;
            _current = null; // force restart
            return duration;
        }

        private void Update()
        {
            if (_sr == null) return;

            Action action;
            if (_oneShot.HasValue && Time.time < _oneShotEnd)
            {
                action = _oneShot.Value;
            }
            else
            {
                _oneShot = null;
                action = _moving ? Action.Walk : Action.Idle;
            }

            Dir3 dir = ToDir3(_facing, out bool flipX);
            Clip clip = Resolve(action, dir);
            if (clip == null || clip.frames == null || clip.frames.Length == 0) return;

            if (clip != _current)
            {
                _current = clip;
                _timer = 0f;
                _frameIndex = 0;
            }

            _timer += Time.deltaTime;
            float frameDuration = 1f / Mathf.Max(1f, clip.fps);
            while (_timer >= frameDuration)
            {
                _timer -= frameDuration;
                _frameIndex++;
                if (_frameIndex >= clip.frames.Length)
                    _frameIndex = clip.loop ? 0 : clip.frames.Length - 1;
            }

            _sr.sprite = clip.frames[Mathf.Clamp(_frameIndex, 0, clip.frames.Length - 1)];
            _sr.flipX = flipX;
        }

        private Clip Resolve(Action action, Dir3 dir)
        {
            for (int i = 0; i < clips.Count; i++)
                if (clips[i].action == action && clips[i].dir == dir)
                    return clips[i];

            // Fallback: same action South, then Idle South, then anything.
            for (int i = 0; i < clips.Count; i++)
                if (clips[i].action == action && clips[i].dir == Dir3.South)
                    return clips[i];
            for (int i = 0; i < clips.Count; i++)
                if (clips[i].action == Action.Idle && clips[i].dir == Dir3.South)
                    return clips[i];
            return clips.Count > 0 ? clips[0] : null;
        }

        private static Dir3 ToDir3(Facing f, out bool flipX)
        {
            switch (f)
            {
                case Facing.North: flipX = false; return Dir3.North;
                case Facing.East: flipX = false; return Dir3.East;
                case Facing.West: flipX = true; return Dir3.East;
                default: flipX = false; return Dir3.South;
            }
        }
    }
}
