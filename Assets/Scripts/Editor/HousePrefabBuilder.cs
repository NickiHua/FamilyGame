using UnityEditor;
using UnityEngine;
using FantacyCentry.View;

namespace FantacyCentry.EditorTools
{
    /// <summary>
    /// Builds placeable house PREFAB variants at different cell footprints from the same
    /// source sprite (the original PNG is never modified). Each prefab carries a
    /// SpriteRenderer + YSort (top-down occlusion) + MapObstacle (so MapExporter stamps
    /// its cells as Building 'B'). Transform scale makes the sprite span exactly N x N
    /// cells regardless of the texture's import PPU.
    ///
    /// Menu: Tools/FantacyCentry/Build House Prefabs (6x6 + 8x8). Drag the resulting
    /// prefabs into the scene to compare sizes.
    /// </summary>
    public static class HousePrefabBuilder
    {
        private const string SpritePath = "Assets/Art/Objects/Houses/village_house1.png";
        private const string OutDir = "Assets/Art/Objects/Houses/";

        [MenuItem("Tools/FantacyCentry/Build House Prefabs (6x6 + 8x8)")]
        public static void Build()
        {
            var sprite = AssetDatabase.LoadAssetAtPath<Sprite>(SpritePath);
            if (sprite == null)
            {
                Debug.LogError($"[HousePrefabBuilder] sprite not found: {SpritePath}");
                return;
            }

            BuildOne(sprite, 6);
            BuildOne(sprite, 8);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log($"[HousePrefabBuilder] Built village_house1_6x6 + _8x8 prefabs in {OutDir}");
        }

        private static void BuildOne(Sprite sprite, int cells)
        {
            // World size of the sprite at scale 1 (= texturePx / PPU). Scale so it spans
            // exactly `cells` world units = `cells` grid cells, whatever the import PPU is.
            float nativeUnits = sprite.bounds.size.x;
            float scale = nativeUnits > 0f ? cells / nativeUnits : 1f;

            var go = new GameObject($"village_house1_{cells}x{cells}");
            go.transform.localScale = new Vector3(scale, scale, 1f);

            var sr = go.AddComponent<SpriteRenderer>();
            sr.sprite = sprite;
            sr.sortingOrder = 10; // YSort overrides this at runtime; harmless default in edit mode

            var ob = go.AddComponent<MapObstacle>();
            ob.size = new Vector2Int(cells, cells);

            go.AddComponent<YSort>();

            string path = $"{OutDir}village_house1_{cells}x{cells}.prefab";
            PrefabUtility.SaveAsPrefabAsset(go, path);
            Object.DestroyImmediate(go);
        }
    }
}
