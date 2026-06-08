using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using FantacyCentry.View;
using Action = FantacyCentry.View.CharacterSpriteAnimator.Action;
using Dir3 = FantacyCentry.View.CharacterSpriteAnimator.Dir3;
using Clip = FantacyCentry.View.CharacterSpriteAnimator.Clip;

namespace FantacyCentry.EditorTools
{
    /// <summary>
    /// One-click rig builder: scans a character's PixelLab "animations/&lt;action&gt;/&lt;dir&gt;/frame_*.png"
    /// folders, assembles the S/E/N clip library (frame_000 skipped — it's the rotation reference),
    /// and saves a ready-to-drop prefab with SpriteRenderer + CharacterSpriteAnimator + GridMover +
    /// CharacterDemoController. Replaces the tedious manual drag flow in spec §5.7.
    /// </summary>
    public static class CharacterRigBuilder
    {
        private const string CharactersRoot = "Assets/Art/Characters";

        [MenuItem("Tools/FantacyCentry/Build LingShuang Rig")]
        private static void BuildLingShuang() => BuildCharacter("LingShuang");

        private static void BuildCharacter(string characterName)
        {
            string characterFolder = $"{CharactersRoot}/{characterName}";
            string animationsRoot = FindAnimationsFolder(characterFolder);
            if (animationsRoot == null)
            {
                Debug.LogError($"[FantacyCentry] No 'animations' folder found under {characterFolder}");
                return;
            }

            var clips = new List<Clip>();
            foreach (string actionDir in Directory.GetDirectories(animationsRoot))
            {
                if (!TryClassify(Path.GetFileName(actionDir), out Action action, out float fps, out bool loop))
                {
                    Debug.LogWarning($"[FantacyCentry] Could not classify action folder, skipped: {actionDir}");
                    continue;
                }

                foreach ((string subfolder, Dir3 dir) in new[]
                         {
                             ("south", Dir3.South),
                             ("east", Dir3.East),
                             ("north", Dir3.North),
                         })
                {
                    string dirFolder = Path.Combine(actionDir, subfolder).Replace('\\', '/');
                    Sprite[] frames = LoadFrames(dirFolder);
                    if (frames.Length == 0)
                    {
                        Debug.LogWarning($"[FantacyCentry] No frames in {dirFolder}");
                        continue;
                    }

                    clips.Add(new Clip { action = action, dir = dir, fps = fps, loop = loop, frames = frames });
                }
            }

            if (clips.Count == 0)
            {
                Debug.LogError($"[FantacyCentry] No clips built for {characterName} — aborting.");
                return;
            }

            Sprite defaultSprite = clips
                .FirstOrDefault(c => c.action == Action.Idle && c.dir == Dir3.South)?.frames.FirstOrDefault()
                ?? clips[0].frames[0];

            var go = new GameObject(characterName);
            var sr = go.AddComponent<SpriteRenderer>();
            sr.sprite = defaultSprite;
            sr.sortingOrder = 10;

            var anim = go.AddComponent<CharacterSpriteAnimator>();
            anim.Configure(clips);
            go.AddComponent<GridMover>();
            go.AddComponent<CharacterDemoController>();

            string prefabPath = $"{characterFolder}/{characterName}.prefab";
            PrefabUtility.SaveAsPrefabAsset(go, prefabPath, out bool ok);
            Object.DestroyImmediate(go);
            AssetDatabase.SaveAssets();

            if (ok)
            {
                Debug.Log($"[FantacyCentry] Built {characterName} rig with {clips.Count} clips → {prefabPath}");
                Selection.activeObject = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            }
            else
            {
                Debug.LogError($"[FantacyCentry] Failed to save prefab at {prefabPath}");
            }
        }

        private static string FindAnimationsFolder(string root)
        {
            if (!Directory.Exists(root)) return null;
            if (Path.GetFileName(root) == "animations") return root.Replace('\\', '/');
            return Directory.GetDirectories(root, "animations", SearchOption.AllDirectories)
                .Select(p => p.Replace('\\', '/'))
                .FirstOrDefault();
        }

        private static Sprite[] LoadFrames(string dirFolder)
        {
            if (!Directory.Exists(dirFolder)) return System.Array.Empty<Sprite>();

            return Directory.GetFiles(dirFolder, "frame_*.png")
                .Select(p => p.Replace('\\', '/'))
                // Skip frame_000 — it is the PixelLab rotation reference frame, not animation content.
                .Where(p => !Path.GetFileNameWithoutExtension(p).EndsWith("000"))
                .OrderBy(p => p, System.StringComparer.Ordinal)
                .Select(AssetDatabase.LoadAssetAtPath<Sprite>)
                .Where(s => s != null)
                .ToArray();
        }

        /// <summary>
        /// Maps a PixelLab action folder name to a logical action + default fps (spec §5.7 table).
        /// Order matters: folder names contain overlapping tokens (e.g. walk folder also says "idle").
        /// </summary>
        private static bool TryClassify(string folderName, out Action action, out float fps, out bool loop)
        {
            string n = folderName.ToLowerInvariant();

            if (n.Contains("walk"))
            {
                action = Action.Walk; fps = 10f; loop = true; return true;
            }
            if (n.Contains("sword") || n.Contains("raises") || n.Contains("attack")
                || n.Contains("thrust") || n.Contains("lance") || n.Contains("spear")
                || n.Contains("punch") || n.Contains("kick"))
            {
                action = Action.Attack; fps = 12f; loop = false; return true;
            }
            if (n.Contains("recoil") || n.Contains("hit") || n.Contains("takes")
                || n.Contains("flinch"))
            {
                action = Action.Hit; fps = 10f; loop = false; return true;
            }
            if (n.Contains("idle") || n.Contains("breathing") || n.Contains("stand"))
            {
                action = Action.Idle; fps = 8f; loop = true; return true;
            }

            action = Action.Idle; fps = 8f; loop = true; return false;
        }
    }
}
