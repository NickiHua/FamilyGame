using UnityEditor;
using UnityEngine;

namespace FantacyCentry.EditorTools
{
    /// <summary>
    /// Locks pixel-art import settings for every texture under Assets/Art/Characters
    /// (spec §5.6). Runs automatically on (re)import so newly dropped PixelLab frames
    /// never come in blurry. Use the menu item to reapply to already-imported assets.
    /// </summary>
    public class PixelArtImportPostprocessor : AssetPostprocessor
    {
        private const string CharactersRoot = "Assets/Art/Characters";
        private const string TilesetsRoot = "Assets/Art/Tilesets";
        private const string MapsRoot = "Assets/Art/Maps";

        private void OnPreprocessTexture()
        {
            string path = assetPath.Replace('\\', '/');
            bool isCharacter = path.StartsWith(CharactersRoot);
            bool isTileset = path.StartsWith(TilesetsRoot);
            bool isMap = path.StartsWith(MapsRoot);
            if (!isCharacter && !isTileset && !isMap) return;

            var ti = (TextureImporter)assetImporter;
            ti.textureType = TextureImporterType.Sprite;
            ti.filterMode = FilterMode.Point;   // most critical: no bilinear blur
            ti.textureCompression = TextureImporterCompression.Uncompressed;
            ti.wrapMode = TextureWrapMode.Clamp;
            ti.mipmapEnabled = false;
            ti.alphaIsTransparency = true;

            if (isCharacter)
            {
                // PixelLab v3 exports one PNG per frame — keep as Single sprite.
                ti.spriteImportMode = SpriteImportMode.Single;
                ti.spritePixelsPerUnit = 48;    // 1 unit = 1 tile (48px character)
            }
            else if (isMap)
            {
                // AI-painted battlefield background: one big image, 64px per grid cell.
                // PPU=64 → 2240px image spans exactly 35 units (35 cells), so 1 cell = 1 unit
                // and the logic grid lines up with GridMover (cellSize = 1).
                ti.spriteImportMode = SpriteImportMode.Single;
                ti.spritePixelsPerUnit = 64;
                ti.maxTextureSize = 4096;       // keep the 2240px map un-downscaled
            }
            else // tileset
            {
                // Cainos pack is a 16px grid packed into one PNG — slice in Sprite Editor.
                ti.spriteImportMode = SpriteImportMode.Multiple;
                ti.spritePixelsPerUnit = 16;    // 1 unit = 1 tile (16px terrain)
            }
        }

        [MenuItem("Tools/FantacyCentry/Reapply Pixel Art Import Settings")]
        private static void Reapply()
        {
            AssetDatabase.ImportAsset(CharactersRoot, ImportAssetOptions.ImportRecursive);
            AssetDatabase.ImportAsset(TilesetsRoot, ImportAssetOptions.ImportRecursive);
            AssetDatabase.ImportAsset(MapsRoot, ImportAssetOptions.ImportRecursive);
            Debug.Log("[FantacyCentry] Reapplied pixel-art import settings under Characters + Tilesets + Maps");
        }
    }
}
