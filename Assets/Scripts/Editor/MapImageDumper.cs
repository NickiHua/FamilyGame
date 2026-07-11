using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Tilemaps;
using FantacyCentry.View;

namespace FantacyCentry.EditorTools
{
    public static class MapImageDumper
    {
        private const int OutputSize = 1920;
        private const string ScenePath = "Assets/Scenes/SampleBattle.unity";
        private const string MapJsonPath = "Assets/Art/Maps/stage1_map.json";
        private const string OutputDir = "art/maps/map_raw";

        [MenuItem("Tools/FantacyCentry/Dump Stage1 Map Images")]
        public static void DumpStage1MapImages()
        {
            try
            {
                EnsureSceneLoaded();

                var stage1 = GameObject.Find("Stage1");
                if (stage1 == null)
                    throw new InvalidOperationException("Stage1 Tilemap was not found in SampleBattle.");
                var sourceTilemap = stage1.GetComponent<Tilemap>();
                if (sourceTilemap == null)
                    throw new InvalidOperationException("Stage1 does not have a Tilemap component.");

                var state = CaptureSceneState();
                var previousDualGrid = GameObject.Find("DualGrid");
                GameObject generatedDualGrid = null;
                GameObject generatedWaterTiles = null;
                GameObject generatedBridgeTiles = null;

                try
                {
                    if (previousDualGrid != null)
                    {
                        previousDualGrid.name = "__MapDump_PreviousDualGrid";
                        SetRenderers(previousDualGrid, false);
                    }

                    Selection.activeGameObject = stage1;
                    MapExporter.Export();
                    AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);

                    var grid = LoadMapGrid();
                    Directory.CreateDirectory(OutputDir);

                    EnableOnly(stage1.GetComponentsInChildren<TilemapRenderer>(true));
                    RenderGrid(grid, Path.Combine(OutputDir, "stage1_tilemap_raw_1920.png"));

                    DualGridBuilder.Build(grid);
                    generatedDualGrid = GameObject.Find("DualGrid");
                    generatedWaterTiles = CopySourceTiles(sourceTilemap, "MapDump_WaterTiles", IsWaterTile, -5001);
                    generatedBridgeTiles = CopySourceTiles(sourceTilemap, "MapDump_BridgeTiles", IsBridgeTile, -4979);

                    var dualRenderers = new List<Renderer>();
                    if (generatedWaterTiles != null)
                        dualRenderers.AddRange(generatedWaterTiles.GetComponentsInChildren<TilemapRenderer>(true));
                    if (generatedDualGrid != null)
                        dualRenderers.AddRange(generatedDualGrid.GetComponentsInChildren<TilemapRenderer>(true));
                    if (generatedBridgeTiles != null)
                        dualRenderers.AddRange(generatedBridgeTiles.GetComponentsInChildren<TilemapRenderer>(true));
                    EnableOnly(dualRenderers.ToArray());
                    RenderGrid(grid, Path.Combine(OutputDir, "stage1_tilemap_dualgrid_1920.png"));

                    Debug.Log($"[MapImageDumper] Wrote 2 images to {OutputDir} at {OutputSize}x{OutputSize}.");
                }
                finally
                {
                    if (generatedBridgeTiles != null)
                        UnityEngine.Object.DestroyImmediate(generatedBridgeTiles);
                    if (generatedWaterTiles != null)
                        UnityEngine.Object.DestroyImmediate(generatedWaterTiles);
                    if (generatedDualGrid != null)
                        UnityEngine.Object.DestroyImmediate(generatedDualGrid);
                    if (previousDualGrid != null)
                        previousDualGrid.name = "DualGrid";
                    state.Restore();
                }

                if (Application.isBatchMode)
                    EditorApplication.Exit(0);
            }
            catch (Exception ex)
            {
                Debug.LogException(ex);
                if (Application.isBatchMode)
                    EditorApplication.Exit(1);
                else
                    throw;
            }
        }

        public static void DumpStage1DualGridFromJsonImage()
        {
            try
            {
                EnsureSceneLoaded();
                var state = CaptureSceneState();
                var previousDualGrid = GameObject.Find("DualGrid");
                GameObject generatedDualGrid = null;

                try
                {
                    if (previousDualGrid != null)
                    {
                        previousDualGrid.name = "__MapDump_PreviousDualGrid";
                        SetRenderers(previousDualGrid, false);
                    }

                    var grid = LoadMapGrid();
                    Directory.CreateDirectory(OutputDir);

                    DualGridBuilder.Build(grid);
                    generatedDualGrid = GameObject.Find("DualGrid");
                    if (generatedDualGrid == null)
                        throw new InvalidOperationException("DualGridBuilder did not create a DualGrid object.");

                    BuildWaterTiles(generatedDualGrid.transform, grid);
                    BuildBridgeTiles(generatedDualGrid.transform, grid);

                    var tilemapRenderers = generatedDualGrid.GetComponentsInChildren<TilemapRenderer>(true);
                    EnableOnly(tilemapRenderers);
                    RenderGrid(grid, Path.Combine(OutputDir, "stage1_tilemap_dualgrid_1920.png"));
                    Debug.Log($"[MapImageDumper] Wrote JSON dual-grid image to {OutputDir} at {OutputSize}x{OutputSize}.");
                }
                finally
                {
                    if (generatedDualGrid != null)
                        UnityEngine.Object.DestroyImmediate(generatedDualGrid);
                    if (previousDualGrid != null)
                        previousDualGrid.name = "DualGrid";
                    state.Restore();
                }

                if (Application.isBatchMode)
                    EditorApplication.Exit(0);
            }
            catch (Exception ex)
            {
                Debug.LogException(ex);
                if (Application.isBatchMode)
                    EditorApplication.Exit(1);
                else
                    throw;
            }
        }

        private static void EnsureSceneLoaded()
        {
            var activeScene = EditorSceneManager.GetActiveScene();
            if (activeScene.path == ScenePath)
                return;
            if (!Application.isBatchMode && activeScene.isDirty)
                throw new InvalidOperationException($"Active scene '{activeScene.path}' has unsaved changes; open SampleBattle or save before dumping.");
            EditorSceneManager.OpenScene(ScenePath);
        }

        private static MapGrid LoadMapGrid()
        {
            var json = AssetDatabase.LoadAssetAtPath<TextAsset>(MapJsonPath);
            if (json == null)
                throw new FileNotFoundException("Map JSON was not found.", MapJsonPath);

            var gridGo = GameObject.Find("MapGrid") ?? new GameObject("MapGrid");
            var grid = gridGo.GetComponent<MapGrid>() ?? gridGo.AddComponent<MapGrid>();
            grid.mapJson = json;
            grid.Parse();
            if (grid.Width <= 0 || grid.Height <= 0)
                throw new InvalidOperationException("MapGrid failed to parse stage1_map.json.");
            return grid;
        }

        private static SceneState CaptureSceneState()
        {
            return new SceneState(UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsInactive.Include));
        }

        private static void SetRenderers(GameObject root, bool enabled)
        {
            if (root == null) return;
            foreach (var renderer in root.GetComponentsInChildren<Renderer>(true))
                renderer.enabled = enabled;
        }

        private static void EnableOnly(Renderer[] keepRenderers)
        {
            var keep = new HashSet<Renderer>(keepRenderers);
            foreach (var renderer in UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsInactive.Include))
                renderer.enabled = keep.Contains(renderer);
        }

        private static GameObject CopySourceTiles(Tilemap source, string name, Func<TileBase, bool> includeTile, int sortingOrder)
        {
            var go = new GameObject(name);
            go.transform.SetParent(source.transform.parent, false);
            go.transform.localPosition = source.transform.localPosition;
            go.transform.localRotation = source.transform.localRotation;
            go.transform.localScale = source.transform.localScale;
            var tilemap = go.AddComponent<Tilemap>();
            var renderer = go.AddComponent<TilemapRenderer>();
            renderer.sortingOrder = sortingOrder;

            int copied = 0;
            source.CompressBounds();
            foreach (var pos in source.cellBounds.allPositionsWithin)
            {
                var tile = source.GetTile(pos);
                if (tile == null || !includeTile(tile))
                    continue;
                tilemap.SetTile(pos, tile);
                copied++;
            }

            if (copied > 0)
                return go;
            UnityEngine.Object.DestroyImmediate(go);
            return null;
        }

        private static bool IsWaterTile(TileBase tile) =>
            tile.name.StartsWith("water", StringComparison.OrdinalIgnoreCase);

        private static bool IsBridgeTile(TileBase tile) =>
            tile.name.StartsWith("bridge", StringComparison.OrdinalIgnoreCase);

        private static GameObject BuildWaterTiles(Transform parent, MapGrid grid)
        {
            var waterTiles = new TileBase[4];
            for (int i = 0; i < waterTiles.Length; i++)
                waterTiles[i] = LoadTile($"Assets/Art/Tiles/water_base_{i + 1}.asset")
                             ?? LoadTile($"Assets/Art/Tiles/t_water_base_{i + 1}.asset");
            var fallback = waterTiles[0] ?? LoadTile("Assets/Art/Tiles/water.asset");
            if (fallback == null)
                return null;

            return BuildTerrainTiles(parent, grid, "MapDump_WaterTiles", -5001, (terrain, x, y) =>
            {
                if (terrain != 'W' && terrain != 'D')
                    return null;
                return waterTiles[(x & 1) + ((y & 1) * 2)] ?? fallback;
            });
        }

        private static GameObject BuildBridgeTiles(Transform parent, MapGrid grid)
        {
            var bridge = LoadTile("Assets/Art/Tiles/bridge.asset");
            if (bridge == null)
                return null;

            return BuildTerrainTiles(parent, grid, "MapDump_BridgeTiles", -4979, (terrain, _, _) =>
                terrain == 'D' ? bridge : null);
        }

        private static GameObject BuildTerrainTiles(
            Transform parent,
            MapGrid grid,
            string name,
            int sortingOrder,
            Func<char, int, int, TileBase> pickTile)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = new Vector3(grid.Origin.x - 0.5f, grid.Origin.y - 0.5f, 0f);
            var tilemap = go.AddComponent<Tilemap>();
            var renderer = go.AddComponent<TilemapRenderer>();
            renderer.sortingOrder = sortingOrder;

            int count = 0;
            for (int y = 0; y < grid.Height; y++)
            for (int x = 0; x < grid.Width; x++)
            {
                var tile = pickTile(grid.TerrainAt(new Vector2Int(x, y)), x, y);
                if (tile == null)
                    continue;
                tilemap.SetTile(new Vector3Int(x, y, 0), tile);
                count++;
            }

            if (count > 0)
                return go;
            UnityEngine.Object.DestroyImmediate(go);
            return null;
        }

        private static TileBase LoadTile(string path) => AssetDatabase.LoadAssetAtPath<TileBase>(path);

        private static void RenderGrid(MapGrid grid, string path)
        {
            var cameraGo = new GameObject("MapDumpCamera");
            var camera = cameraGo.AddComponent<Camera>();
            camera.orthographic = true;
            camera.orthographicSize = grid.Height * 0.5f;
            camera.transform.position = new Vector3(grid.CenterWorld.x, grid.CenterWorld.y, -10f);
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = new Color(0f, 0f, 0f, 0f);
            camera.nearClipPlane = 0.1f;
            camera.farClipPlane = 100f;
            camera.cullingMask = ~0;
            camera.allowHDR = false;
            camera.allowMSAA = false;

            var renderTexture = new RenderTexture(OutputSize, OutputSize, 24, RenderTextureFormat.ARGB32)
            {
                antiAliasing = 1,
                filterMode = FilterMode.Point,
            };
            var previousActive = RenderTexture.active;
            var previousTarget = camera.targetTexture;
            try
            {
                camera.targetTexture = renderTexture;
                camera.Render();
                RenderTexture.active = renderTexture;

                var texture = new Texture2D(OutputSize, OutputSize, TextureFormat.RGBA32, false);
                texture.ReadPixels(new Rect(0, 0, OutputSize, OutputSize), 0, 0);
                texture.Apply(false, false);
                File.WriteAllBytes(path, texture.EncodeToPNG());
                UnityEngine.Object.DestroyImmediate(texture);
                Debug.Log($"[MapImageDumper] Wrote {path}");
            }
            finally
            {
                camera.targetTexture = previousTarget;
                RenderTexture.active = previousActive;
                renderTexture.Release();
                UnityEngine.Object.DestroyImmediate(renderTexture);
                UnityEngine.Object.DestroyImmediate(cameraGo);
            }
        }

        private sealed class SceneState
        {
            private readonly Renderer[] _renderers;
            private readonly bool[] _rendererEnabled;

            public SceneState(Renderer[] renderers)
            {
                _renderers = renderers;
                _rendererEnabled = new bool[renderers.Length];
                for (int i = 0; i < renderers.Length; i++)
                    _rendererEnabled[i] = renderers[i].enabled;
            }

            public void Restore()
            {
                for (int i = 0; i < _renderers.Length; i++)
                    if (_renderers[i] != null)
                        _renderers[i].enabled = _rendererEnabled[i];
            }
        }
    }
}