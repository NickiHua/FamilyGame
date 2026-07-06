#!/usr/bin/env python3
r"""import_portraits.py — one-off: (re)import the FINAL 立绘 + bust portraits into Unity.

Deletes EVERYTHING currently under Assets/Art/UI/portraits/ (the old anchor) and
copies the approved masters from art/portraits/<char>/ as the NEW anchor:

    art/portraits/<char>/<char>_full.png      -> Assets/Art/UI/portraits/<Id>_full.png
    art/portraits/<char>/<char>_bust_base.png -> Assets/Art/UI/portraits/<Id>_bust.png

Each PNG gets a hand-written .meta (Sprite, Bilinear, PPU 100, alphaIsTransparency,
uncompressed) with a fresh GUID so Unity imports them cleanly.
"""
from __future__ import annotations

import secrets
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "art" / "portraits"
DST = ROOT / "Assets" / "Art" / "UI" / "portraits"

# folder name (lowercase master) -> Unity Unit id (== DisplayName / spawn id)
CHARS = {
    "luli": "LuLi",
    "suyao": "SuYao",
    "lingshuang": "LingShuang",
    "empirearcher": "EmpireArcher",
    "empireaxesoldier": "EmpireAxeSoldier",
    "empirecaptain": "EmpireCaptain",
}


def guid() -> str:
    return secrets.token_hex(16)


def sprite_id() -> str:
    # Unity sprite internal id: 16 random hex + a fixed type/serialization suffix.
    return secrets.token_hex(8) + "0800000000000000"


def meta_text() -> str:
    return f"""fileFormatVersion: 2
guid: {guid()}
TextureImporter:
  internalIDToNameTable: []
  externalObjects: {{}}
  serializedVersion: 13
  mipmaps:
    mipMapMode: 0
    enableMipMap: 0
    sRGBTexture: 1
    linearTexture: 0
    fadeOut: 0
    borderMipMap: 0
    mipMapsPreserveCoverage: 0
    alphaTestReferenceValue: 0.5
    mipMapFadeDistanceStart: 1
    mipMapFadeDistanceEnd: 3
  bumpmap:
    convertToNormalMap: 0
    externalNormalMap: 0
    heightScale: 0.25
    normalMapFilter: 0
    flipGreenChannel: 0
  isReadable: 0
  streamingMipmaps: 0
  streamingMipmapsPriority: 0
  vTOnly: 0
  ignoreMipmapLimit: 0
  grayScaleToAlpha: 0
  generateCubemap: 6
  cubemapConvolution: 0
  seamlessCubemap: 0
  textureFormat: 1
  maxTextureSize: 2048
  textureSettings:
    serializedVersion: 2
    filterMode: 1
    aniso: 1
    mipBias: 0
    wrapU: 1
    wrapV: 1
    wrapW: 1
  nPOTScale: 0
  lightmap: 0
  compressionQuality: 50
  spriteMode: 1
  spriteExtrude: 1
  spriteMeshType: 0
  alignment: 0
  spritePivot: {{x: 0.5, y: 0.5}}
  spritePixelsToUnits: 100
  spriteBorder: {{x: 0, y: 0, z: 0, w: 0}}
  spriteGenerateFallbackPhysicsShape: 0
  alphaUsage: 1
  alphaIsTransparency: 1
  spriteTessellationDetail: -1
  textureType: 8
  textureShape: 1
  singleChannelComponent: 0
  flipbookRows: 1
  flipbookColumns: 1
  maxTextureSizeSet: 0
  compressionQualitySet: 0
  textureFormatSet: 0
  ignorePngGamma: 0
  applyGammaDecoding: 0
  swizzle: 50462976
  cookieLightType: 0
  platformSettings:
  - serializedVersion: 4
    buildTarget: DefaultTexturePlatform
    maxTextureSize: 2048
    resizeAlgorithm: 0
    textureFormat: -1
    textureCompression: 0
    compressionQuality: 50
    crunchedCompression: 0
    allowsAlphaSplitting: 0
    overridden: 0
    ignorePlatformSupport: 0
    androidETC2FallbackOverride: 0
    forceMaximumCompressionQuality_BC6H_BC7: 0
  - serializedVersion: 4
    buildTarget: Standalone
    maxTextureSize: 2048
    resizeAlgorithm: 0
    textureFormat: -1
    textureCompression: 0
    compressionQuality: 50
    crunchedCompression: 0
    allowsAlphaSplitting: 0
    overridden: 0
    ignorePlatformSupport: 0
    androidETC2FallbackOverride: 0
    forceMaximumCompressionQuality_BC6H_BC7: 0
  spriteSheet:
    serializedVersion: 2
    sprites: []
    outline: []
    customData: 
    physicsShape: []
    bones: []
    spriteID: {sprite_id()}
    internalID: 0
    vertices: []
    indices: 
    edges: []
    weights: []
    secondaryTextures: []
    spriteCustomMetadata:
      entries: []
    nameFileIdTable: {{}}
  mipmapLimitGroupName: 
  pSDRemoveMatte: 0
  userData: 
  assetBundleName: 
  assetBundleVariant: 
"""


def main() -> None:
    if not DST.exists():
        raise SystemExit(f"Destination not found: {DST}")

    # 1) wipe the old anchor (all pngs + metas, keeps the folder + its .meta).
    removed = 0
    for f in DST.iterdir():
        if f.is_file():
            f.unlink()
            removed += 1
    print(f"deleted {removed} file(s) from {DST.relative_to(ROOT)}")

    # 2) copy the final masters in with fresh metas.
    for folder, uid in CHARS.items():
        for suffix_src, suffix_dst in (("_full", "_full"), ("_bust_base", "_bust")):
            src = SRC / folder / f"{folder}{suffix_src}.png"
            if not src.exists():
                raise SystemExit(f"Missing source: {src}")
            dst = DST / f"{uid}{suffix_dst}.png"
            shutil.copyfile(src, dst)
            (DST / f"{dst.name}.meta").write_text(meta_text(), encoding="utf-8")
            print(f"  {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")

    print("done.")


if __name__ == "__main__":
    main()
