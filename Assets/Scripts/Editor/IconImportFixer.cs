using System.IO;
using UnityEditor;
using UnityEngine;

namespace FantacyCentry.EditorTools
{
    /// <summary>
    /// Forces crisp, HD-friendly import settings on the command/UI icons. These icons are 200px
    /// but shown at ~45px in the HUD, so without mipmaps the downscale aliases and looks
    /// "pixelated". This sets mipmaps ON (smooth minification), Bilinear filtering, anisotropic
    /// sampling, and uncompressed colour — then reimports. Run it via the menu; editing the .meta
    /// by hand does not stick because Unity rewrites the meta on reimport.
    /// </summary>
    public static class IconImportFixer
    {
        private const string IconDir = "Assets/Art/UI/icons";

        [MenuItem("Tools/FantacyCentry/Fix UI Icon Import (HD)")]
        public static void Fix()
        {
            if (!Directory.Exists(IconDir))
            {
                Debug.LogError("[IconImportFixer] Missing folder " + IconDir);
                return;
            }

            string[] guids = AssetDatabase.FindAssets("t:Texture2D", new[] { IconDir });
            int n = 0;
            foreach (string guid in guids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                var ti = AssetImporter.GetAtPath(path) as TextureImporter;
                if (ti == null) continue;

                ti.textureType = TextureImporterType.Sprite;
                ti.spriteImportMode = SpriteImportMode.Single;
                ti.mipmapEnabled = true;                 // smooth minification when shown small
                ti.filterMode = FilterMode.Bilinear;
                ti.anisoLevel = 4;                        // sharper at oblique / minified sampling
                ti.textureCompression = TextureImporterCompression.Uncompressed;
                ti.maxTextureSize = 512;                  // plenty for a 200px icon
                ti.alphaIsTransparency = true;

                var ps = ti.GetDefaultPlatformTextureSettings();
                ps.textureCompression = TextureImporterCompression.Uncompressed;
                ps.maxTextureSize = 512;
                ti.SetPlatformTextureSettings(ps);

                ti.SaveAndReimport();
                n++;
            }

            AssetDatabase.Refresh();
            Debug.Log($"[IconImportFixer] Reimported {n} icons with mipmaps + uncompressed (HD).");
        }
    }
}
