using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using FantacyCentry.View;

namespace FantacyCentry.EditorTools
{
    /// <summary>
    /// One-click demo wiring: drops the AI battlefield background, builds the logic grid
    /// from demo_map.json, and places LingShuang on a walkable cell with cell movement,
    /// blocked-cell stopping, and the Y-sort mechanism. The "打通一切" button.
    ///
    /// Coordinate contract (see <see cref="MapGrid"/>): 1 cell = 1 unit, cell (0,0) is
    /// bottom-left, background PPU=64 so the 2240px image spans 35 units.
    /// </summary>
    public static class MapSceneBuilder
    {
        private const string MapPng = "Assets/Art/Maps/demo_map.png";
        private const string MapJson = "Assets/Art/Maps/demo_map.json";
        private const string CharacterPrefab = "Assets/Art/Characters/LingShuang/LingShuang.prefab";

        // The character sprite is 1 world unit tall (PPU=48) and a map cell is also 1 unit
        // (PPU=64), so a unit would render exactly one-cell tall — visually a bit big on the
        // large painted terrain. Shrink it for the FFT/langrisser "person slightly smaller
        // than the tile" look. Tweak freely; 1.0 = one-cell tall.
        private const float CharacterScale = 0.6f;

        [MenuItem("Tools/FantacyCentry/Build Demo Map Scene")]
        private static void BuildDemoMapScene()
        {
            var bg = AssetDatabase.LoadAssetAtPath<Sprite>(MapPng);
            if (bg == null)
            {
                Debug.LogError($"[MapSceneBuilder] Background sprite not found at {MapPng}. " +
                               "Make sure it imported as a Sprite (PPU=64).");
                return;
            }

            var json = AssetDatabase.LoadAssetAtPath<TextAsset>(MapJson);
            if (json == null)
            {
                Debug.LogError($"[MapSceneBuilder] Map JSON not found at {MapJson}.");
                return;
            }

            // --- Logic grid -------------------------------------------------
            var gridGo = new GameObject("MapGrid");
            var grid = gridGo.AddComponent<MapGrid>();
            grid.mapJson = json;
            grid.Parse();
            int size = grid.Size;
            if (size <= 0)
            {
                Debug.LogError("[MapSceneBuilder] Failed to parse the map grid.");
                Object.DestroyImmediate(gridGo);
                return;
            }

            // --- Background sprite -----------------------------------------
            var bgGo = new GameObject("MapBackground");
            var bgSr = bgGo.AddComponent<SpriteRenderer>();
            bgSr.sprite = bg;
            bgSr.sortingOrder = -5000;          // well below any Y-sorted unit
            Vector2 center = grid.CenterWorld;   // cell centres span 0..size-1
            bgGo.transform.position = new Vector3(center.x, center.y, 0f);

            // --- Character --------------------------------------------------
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(CharacterPrefab);
            if (prefab == null)
            {
                Debug.LogWarning($"[MapSceneBuilder] {CharacterPrefab} not found. " +
                                 "Run Tools/FantacyCentry/Build LingShuang Rig first; " +
                                 "background + grid were still created.");
            }
            else
            {
                Vector2Int start = FindWalkableNearCenter(grid);
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                go.transform.position = new Vector3(start.x, start.y, 0f);
                go.transform.localScale = Vector3.one * CharacterScale;

                var ctrl = go.GetComponent<CharacterDemoController>();
                if (ctrl != null) ctrl.map = grid;
                if (go.GetComponent<YSort>() == null) go.AddComponent<YSort>();

                // Centre the (pixel-perfect) camera on the character and have it follow.
                if (Camera.main != null)
                {
                    Camera.main.transform.position = new Vector3(start.x, start.y, -10f);
                    var follow = Camera.main.GetComponent<CameraFollow>();
                    if (follow == null) follow = Camera.main.gameObject.AddComponent<CameraFollow>();
                    follow.target = go.transform;
                }

                Selection.activeGameObject = go;
                Debug.Log($"[MapSceneBuilder] Placed LingShuang at cell {start} on a {size}x{size} grid.");
            }

            EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
            Debug.Log("[MapSceneBuilder] Demo map scene assembled. Press Play and walk with arrow keys.");
        }

        /// <summary>Spiral out from the grid centre to the nearest walkable cell.</summary>
        private static Vector2Int FindWalkableNearCenter(MapGrid grid)
        {
            int c = grid.Size / 2;
            var center = new Vector2Int(c, c);
            if (grid.IsWalkable(center)) return center;

            for (int r = 1; r < grid.Size; r++)
            {
                for (int dx = -r; dx <= r; dx++)
                for (int dy = -r; dy <= r; dy++)
                {
                    var cell = new Vector2Int(c + dx, c + dy);
                    if (grid.IsWalkable(cell)) return cell;
                }
            }
            return center;
        }
    }
}
