"""OpenUSD: a `.usda` text writer (Mesh with normals, `primvars:displayColor`, `primvars:st`, a `UsdPreviewSurface`
material fed by the vertex colours or a texture), `.usdc` / `.usdz` through `usd-core` when installed, and a reader
(through `usd-core`; a small `.usda` parser otherwise, enough to read what the writer writes)."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import numpy as np

from ..mesh import Mesh


def usd_core_available() -> bool:
    try:
        import pxr  # type: ignore
    except ImportError:
        return False
    return pxr is not None


def usda_text(mesh: Mesh, name: str = "fractal", texture: str | None = None, meters_per_unit: float = 1.0) -> str:
    """The scene as `.usda` text; `texture` is the file name of a colour texture beside it (needs UVs)."""
    prim = _identifier(name)
    lines = ["#usda 1.0", "(", f'    defaultPrim = "{prim}"', f"    metersPerUnit = {meters_per_unit:g}", '    upAxis = "Z"',
             "    doc = \"Fractalchemy 3D export\"", ")", "", f'def Xform "{prim}"', "{",
             '    def Mesh "mesh" (', '        prepend apiSchemas = ["MaterialBindingAPI"]', "    )", "    {"]
    n_faces = mesh.face_count
    lines.append(f"        int[] faceVertexCounts = [{', '.join(['3'] * n_faces)}]")
    lines.append(f"        int[] faceVertexIndices = [{', '.join(map(str, mesh.faces.reshape(-1).tolist()))}]")
    lines.append(f"        point3f[] points = [{_tuples(mesh.vertices)}]")
    if mesh.normals is not None:
        lines.append(f"        normal3f[] normals = [{_tuples(mesh.normals, 5)}] (")
        lines.append('            interpolation = "vertex"')
        lines.append("        )")
    if mesh.colors is not None:
        lines.append(f"        color3f[] primvars:displayColor = [{_tuples(np.clip(mesh.colors, 0, 1), 4)}] (")
        lines.append('            interpolation = "vertex"')
        lines.append("        )")
    if mesh.uvs is not None:
        lines.append(f"        texCoord2f[] primvars:st = [{_tuples(mesh.uvs, 5)}] (")
        lines.append('            interpolation = "vertex"')
        lines.append("        )")
    lines.append('        uniform token subdivisionScheme = "none"')
    lines.append(f"        rel material:binding = </{prim}/Materials/{prim}Material>")
    lines.append("    }")
    lines.append("")
    lines.append('    def Scope "Materials"')
    lines.append("    {")
    lines.append(f'        def Material "{prim}Material"')
    lines.append("        {")
    lines.append(f"            token outputs:surface.connect = </{prim}/Materials/{prim}Material/PreviewSurface.outputs:surface>")
    lines.append("")
    lines.append('            def Shader "PreviewSurface"')
    lines.append("            {")
    lines.append('                uniform token info:id = "UsdPreviewSurface"')
    if texture is not None and mesh.uvs is not None:
        lines.append(f"                color3f inputs:diffuseColor.connect = </{prim}/Materials/{prim}Material/Texture.outputs:rgb>")
    elif mesh.colors is not None:
        lines.append(f"                color3f inputs:diffuseColor.connect = </{prim}/Materials/{prim}Material/ColorReader.outputs:result>")
    else:
        lines.append("                color3f inputs:diffuseColor = (0.8, 0.8, 0.8)")
    lines.append("                float inputs:roughness = 0.7")
    lines.append("                float inputs:metallic = 0")
    lines.append("                token outputs:surface")
    lines.append("            }")
    if texture is not None and mesh.uvs is not None:
        lines.append("")
        lines.append('            def Shader "stReader"')
        lines.append("            {")
        lines.append('                uniform token info:id = "UsdPrimvarReader_float2"')
        lines.append('                token inputs:varname = "st"')
        lines.append("                float2 outputs:result")
        lines.append("            }")
        lines.append("")
        lines.append('            def Shader "Texture"')
        lines.append("            {")
        lines.append('                uniform token info:id = "UsdUVTexture"')
        lines.append(f"                asset inputs:file = @{texture}@")
        lines.append(f"                float2 inputs:st.connect = </{prim}/Materials/{prim}Material/stReader.outputs:result>")
        lines.append('                token inputs:wrapS = "clamp"')
        lines.append('                token inputs:wrapT = "clamp"')
        lines.append("                float3 outputs:rgb")
        lines.append("            }")
    elif mesh.colors is not None:
        lines.append("")
        lines.append('            def Shader "ColorReader"')
        lines.append("            {")
        lines.append('                uniform token info:id = "UsdPrimvarReader_float3"')
        lines.append('                token inputs:varname = "displayColor"')
        lines.append("                float3 outputs:result")
        lines.append("            }")
    lines.append("        }")
    lines.append("    }")
    lines.append("}")
    return "\n".join(lines) + "\n"


def write_usd(mesh: Mesh, path: Path, texture: Path | None = None, name: str = "fractal", meters_per_unit: float = 1.0) -> list[Path]:
    """Write `.usda` (always), or `.usdc` / `.usdz` through usd-core (a `.usda` is written instead when it is missing).

    Returns the files written.
    """
    path = Path(path)
    text = usda_text(mesh, name, texture.name if texture is not None else None, meters_per_unit)
    suffix = path.suffix.lower()
    if suffix == ".usda" or not usd_core_available():
        target = path if suffix == ".usda" else path.with_suffix(".usda")
        target.write_text(text, encoding="utf-8")
        return [target]
    from pxr import Usd, UsdUtils  # type: ignore
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / f"{_identifier(name)}.usda"
        source.write_text(text, encoding="utf-8")
        if texture is not None and texture.exists():
            (Path(folder) / texture.name).write_bytes(texture.read_bytes())
        if suffix == ".usdz":
            if not UsdUtils.CreateNewUsdzPackage(str(source), str(path)):
                raise OSError(f"could not write {path.name}")
        else:
            stage = Usd.Stage.Open(str(source))
            stage.Export(str(path))
    return [path]


def read_usd(path: Path) -> Mesh:
    """Read the first Mesh prim (usd-core when installed; the writer's `.usda` layout otherwise).

    Raises:
        ValueError: When no mesh is found.
    """
    path = Path(path)
    if usd_core_available():
        from pxr import Usd, UsdGeom  # type: ignore
        stage = Usd.Stage.Open(str(path))
        for prim in stage.Traverse():
            if prim.IsA(UsdGeom.Mesh):
                geom = UsdGeom.Mesh(prim)
                points = np.asarray(geom.GetPointsAttr().Get(), dtype=np.float64)
                counts = np.asarray(geom.GetFaceVertexCountsAttr().Get(), dtype=np.int64)
                indices = np.asarray(geom.GetFaceVertexIndicesAttr().Get(), dtype=np.int64)
                faces = _triangulate(counts, indices)
                mesh = Mesh(points, faces)
                normals = geom.GetNormalsAttr().Get()
                if normals is not None and len(normals) == points.shape[0]:
                    mesh.normals = np.asarray(normals, dtype=np.float64)
                else:
                    mesh.compute_normals()
                api = UsdGeom.PrimvarsAPI(prim)
                color = api.GetPrimvar("displayColor")
                if color and color.Get() is not None and len(color.Get()) == points.shape[0]:
                    mesh.colors = np.asarray(color.Get(), dtype=np.float32)
                st = api.GetPrimvar("st")
                if st and st.Get() is not None and len(st.Get()) == points.shape[0]:
                    mesh.uvs = np.asarray(st.Get(), dtype=np.float32)
                return mesh
        raise ValueError(f"{path.name}: no Mesh prim")
    if path.suffix.lower() != ".usda":
        raise ValueError(f"{path.name}: reading binary USD needs the usd-core package")
    return _parse_usda(path.read_text(encoding="utf-8"), path.name)


def _parse_usda(text: str, label: str) -> Mesh:
    def array(pattern: str):
        match = re.search(pattern + r"\s*=\s*\[(.*?)\]", text, re.S)
        if match is None:
            return None
        numbers = re.findall(r"-?\d+(?:\.\d+)?(?:e[-+]?\d+)?", match.group(1))
        return np.array(numbers, dtype=np.float64)
    points = array(r"point3f\[\]\s+points")
    counts = array(r"int\[\]\s+faceVertexCounts")
    indices = array(r"int\[\]\s+faceVertexIndices")
    if points is None or counts is None or indices is None:
        raise ValueError(f"{label}: no Mesh prim")
    mesh = Mesh(points.reshape(-1, 3), _triangulate(counts.astype(np.int64), indices.astype(np.int64)))
    normals = array(r"normal3f\[\]\s+normals")
    if normals is not None and normals.size == points.size:
        mesh.normals = normals.reshape(-1, 3)
    else:
        mesh.compute_normals()
    colors = array(r"color3f\[\]\s+primvars:displayColor")
    if colors is not None and colors.size == points.size:
        mesh.colors = colors.reshape(-1, 3).astype(np.float32)
    uvs = array(r"texCoord2f\[\]\s+primvars:st")
    if uvs is not None and uvs.size == points.size // 3 * 2:
        mesh.uvs = uvs.reshape(-1, 2).astype(np.float32)
    return mesh


def _triangulate(counts: np.ndarray, indices: np.ndarray) -> np.ndarray:
    if counts.size and (counts == 3).all():
        return indices.reshape(-1, 3)
    faces = []
    pos = 0
    for n in counts.tolist():
        poly = indices[pos:pos + n]
        pos += n
        for i in range(1, n - 1):
            faces.append([poly[0], poly[i], poly[i + 1]])
    return np.asarray(faces, dtype=np.int64).reshape(-1, 3)


def _tuples(array: np.ndarray, digits: int = 6) -> str:
    return ", ".join("(" + ", ".join(f"{v:.{digits}g}" for v in row) + ")" for row in array.tolist())


def _identifier(name: str) -> str:
    ident = re.sub(r"[^A-Za-z0-9_]", "_", name).strip("_") or "fractal"
    return ident if not ident[0].isdigit() else "_" + ident


__all__ = ["usda_text", "write_usd", "read_usd", "usd_core_available"]
