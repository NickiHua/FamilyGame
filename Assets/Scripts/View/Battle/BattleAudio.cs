using UnityEngine;

namespace FantacyCentry.View.Battle
{
    /// <summary>
    /// Tiny 2D SFX player for the battle. Holds clip banks (wired by BattleSceneBuilder from
    /// Assets/Audio/) and plays one-shots on gameplay events. A lightweight singleton so the
    /// runner / HUD / stage director can fire sounds without holding references.
    /// </summary>
    public sealed class BattleAudio : MonoBehaviour
    {
        public static BattleAudio Instance { get; private set; }

        [Tooltip("2D AudioSource used for all one-shots (added by the builder).")]
        public AudioSource source;

        [Header("Clip banks (random pick)")]
        public AudioClip[] footsteps;
        public AudioClip[] slashes;
        public AudioClip[] hits;
        public AudioClip[] ui;

        [Header("Single clips")]
        public AudioClip magicFire;
        public AudioClip magicThunder;
        public AudioClip magicIce;
        public AudioClip charge;
        public AudioClip heal;

        [Range(0f, 1f)] public float volume = 0.8f;

        private void Awake()
        {
            Instance = this;
            if (source == null) source = GetComponent<AudioSource>();
            if (source != null)
            {
                source.playOnAwake = false;
                source.spatialBlend = 0f; // 2D
            }
        }

        private void OnDestroy()
        {
            if (Instance == this) Instance = null;
        }

        private void One(AudioClip clip, float vol = 1f)
        {
            if (clip != null && source != null) source.PlayOneShot(clip, volume * vol);
        }

        private void Rand(AudioClip[] bank, float vol = 1f)
        {
            if (bank != null && bank.Length > 0) One(bank[Random.Range(0, bank.Length)], vol);
        }

        public void Footstep() => Rand(footsteps, 0.6f);
        public void Slash() => Rand(slashes);
        public void Hit() => Rand(hits);
        public void Click() => Rand(ui, 0.8f);
        public void Heal() => One(heal);
        public void Charge() => One(charge, 0.8f);

        /// <summary>Play the elemental cast sound for a VFX key ("fireball","lightning","icespike",...).</summary>
        public void Magic(string vfxKey)
        {
            if (string.IsNullOrEmpty(vfxKey)) { One(charge); return; }
            string k = vfxKey.ToLowerInvariant();
            if (k.Contains("fire")) One(magicFire);
            else if (k.Contains("light") || k.Contains("thunder")) One(magicThunder);
            else if (k.Contains("ice") || k.Contains("frost")) One(magicIce);
            else One(charge);
        }

        // --- Static convenience so callers don't null-check the singleton ------------------
        public static void PlayFootstep() { if (Instance != null) Instance.Footstep(); }
        public static void PlaySlash() { if (Instance != null) Instance.Slash(); }
        public static void PlayHit() { if (Instance != null) Instance.Hit(); }
        public static void PlayClick() { if (Instance != null) Instance.Click(); }
        public static void PlayHeal() { if (Instance != null) Instance.Heal(); }
        public static void PlayCharge() { if (Instance != null) Instance.Charge(); }
        public static void PlayMagic(string vfxKey) { if (Instance != null) Instance.Magic(vfxKey); }
    }
}
