using System.IO;
using TMPro;
using UnityEditor;
using UnityEngine;
using UnityEngine.TextCore.LowLevel;

namespace FantacyCentry.EditorTools
{
    /// <summary>
    /// Builds a <b>dynamic</b> TextMeshPro font asset from the bundled Chinese TTF
    /// (Assets/Art/UI/fonts/NotoSansSC-Regular.ttf). Dynamic mode rasterises glyphs on
    /// demand at runtime/edit-time, so we do NOT bake tens of thousands of CJK glyphs up
    /// front — the atlas grows only with the characters the game actually shows.
    /// </summary>
    public static class CnFontBuilder
    {
        private const string TtfPath = "Assets/Art/UI/fonts/NotoSansSC-Regular.ttf";
        private const string AssetPath = "Assets/Art/UI/fonts/NotoSansSC SDF.asset";

        [MenuItem("Tools/FantacyCentry/Build CN Font Asset")]
        public static void BuildMenu()
        {
            TMP_FontAsset fa = EnsureFont();
            if (fa != null)
            {
                Selection.activeObject = fa;
                EditorGUIUtility.PingObject(fa);
                Debug.Log("[CnFontBuilder] Chinese TMP font ready at " + AssetPath);
            }
        }

        /// <summary>Returns the dynamic CN TMP font asset, creating it from the TTF if missing.</summary>
        public static TMP_FontAsset EnsureFont()
        {
            var existing = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(AssetPath);
            if (existing != null) return existing;

            var ttf = AssetDatabase.LoadAssetAtPath<Font>(TtfPath);
            if (ttf == null)
            {
                Debug.LogError("[CnFontBuilder] Missing TTF at " + TtfPath +
                               " — download the font first.");
                return null;
            }

            TMP_FontAsset fontAsset = TMP_FontAsset.CreateFontAsset(
                ttf,
                samplingPointSize: 90,
                atlasPadding: 9,
                renderMode: GlyphRenderMode.SDFAA,
                atlasWidth: 1024,
                atlasHeight: 1024,
                atlasPopulationMode: AtlasPopulationMode.Dynamic,
                enableMultiAtlasSupport: true);

            if (fontAsset == null)
            {
                Debug.LogError("[CnFontBuilder] TMP_FontAsset.CreateFontAsset returned null.");
                return null;
            }

            fontAsset.name = Path.GetFileNameWithoutExtension(AssetPath);
            AssetDatabase.CreateAsset(fontAsset, AssetPath);

            // Persist the material + atlas texture(s) as sub-assets of the font asset.
            if (fontAsset.material != null)
            {
                fontAsset.material.name = fontAsset.name + " Material";
                AssetDatabase.AddObjectToAsset(fontAsset.material, fontAsset);
            }
            if (fontAsset.atlasTextures != null)
            {
                foreach (Texture2D tex in fontAsset.atlasTextures)
                {
                    if (tex == null) continue;
                    tex.name = fontAsset.name + " Atlas";
                    AssetDatabase.AddObjectToAsset(tex, fontAsset);
                }
            }

            EditorUtility.SetDirty(fontAsset);
            AssetDatabase.SaveAssets();
            AssetDatabase.ImportAsset(AssetPath);
            return fontAsset;
        }
    }
}
