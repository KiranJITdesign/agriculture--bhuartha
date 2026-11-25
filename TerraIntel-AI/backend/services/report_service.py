"""PDF report generation service (WeasyPrint primary with pure-Python PDF + image fallback)."""
from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any

from PIL import Image

CSS_PATH = (
    Path(__file__).resolve().parent.parent
    / "analyses"
    / "templates"
    / "reports"
    / "crop_health_report.css"
)
MEDIA_ROOT = Path(__file__).resolve().parent.parent / "media"


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _media_url_to_path(url: str) -> Path | None:
    if not url or not url.startswith("/media/"):
        return None
    rel = url[len("/media/") :]
    p = (MEDIA_ROOT / rel).resolve()
    if p.exists() and p.is_file():
        return p
    return None


def _encode_png_as_jpeg_rgb(
    img_path: Path, bg_rgb: tuple[int, int, int] = (17, 24, 39)
) -> tuple[bytes, int, int] | None:
    if not img_path.exists():
        return None
    with Image.open(img_path) as im:
        rgba = im.convert("RGBA")
        canvas = Image.new("RGBA", rgba.size, (*bg_rgb, 255))
        composited = Image.alpha_composite(canvas, rgba).convert("RGB")
        # Resize very small rasters cleanly for crisp PDF embedding
        w, h = composited.size
        if max(w, h) < 400:
            scale = 400 / max(1, max(w, h))
            new_size = (int(w * scale), int(h * scale))
            composited = composited.resize(new_size, Image.Resampling.NEAREST)
        buf = io.BytesIO()
        composited.save(buf, format="JPEG", quality=92)
        return buf.getvalue(), composited.width, composited.height


def _build_pdf_with_images(
    page1_lines: list[str],
    images: list[tuple[str, Path]],
) -> bytes:
    """
    Build a valid 1-or-2 page PDF 1.4 document with text on page 1
    and embedded output images on page 2 (no external native libraries required).
    """
    # Page 1 content stream
    p1_cmds = ["BT", "/F1 11 Tf", "48 780 Td", "15 TL"]
    for idx, line in enumerate(page1_lines[:46]):
        safe = _escape_pdf_text(line[:95])
        if idx == 0:
            p1_cmds.append(f"({safe}) Tj")
        else:
            p1_cmds.append(f"T* ({safe}) Tj")
    p1_cmds.append("ET")
    p1_stream = "\n".join(p1_cmds).encode("latin-1", errors="replace")

    prepared_imgs: list[tuple[str, bytes, int, int]] = []
    for caption, path in images:
        encoded = _encode_png_as_jpeg_rgb(path)
        if encoded is not None:
            jpg_bytes, w, h = encoded
            prepared_imgs.append((caption, jpg_bytes, w, h))

    objects: list[bytes] = []
    # Obj 1: Catalog, Obj 2: Pages, Obj 3: Font
    kids_refs = "[4 0 R 6 0 R]" if prepared_imgs else "[4 0 R]"
    page_cnt = 2 if prepared_imgs else 1
    pages_obj = f"2 0 obj << /Type /Pages /Kids {kids_refs} /Count {page_cnt} >> endobj\n"
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(pages_obj.encode("ascii"))
    objects.append(b"3 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")

    # Obj 4: Page 1, Obj 5: Page 1 contents
    objects.append(
        b"4 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 3 0 R >> >> /Contents 5 0 R >> endobj\n"
    )
    objects.append(
        f"5 0 obj << /Length {len(p1_stream)} >>\nstream\n".encode("ascii")
        + p1_stream
        + b"\nendstream endobj\n"
    )

    if prepared_imgs:
        # Obj 6: Page 2, Obj 7: Page 2 contents, Obj 8+: Image XObjects
        xobj_entries: list[str] = []
        p2_cmds = ["BT", "/F1 13 Tf", "48 790 Td", "(Satellite & NDVI Output Imagery) Tj", "ET"]
        y_cursor = 755.0
        max_box_w = 499.0
        max_box_h = 310.0 if len(prepared_imgs) > 1 else 540.0

        img_objs: list[bytes] = []
        next_obj_num = 8
        for idx, (caption, jpg_bytes, w, h) in enumerate(prepared_imgs[:2]):
            im_name = f"Im{idx}"
            xobj_entries.append(f"/{im_name} {next_obj_num} 0 R")

            scale = min(max_box_w / max(1, w), max_box_h / max(1, h))
            draw_w = w * scale
            draw_h = h * scale
            y_img = y_cursor - 20.0 - draw_h

            p2_cmds.extend(
                [
                    "BT",
                    "/F1 11 Tf",
                    f"48 {y_cursor:.1f} Td",
                    f"({_escape_pdf_text(caption)}) Tj",
                    "ET",
                    "q",
                    f"{draw_w:.2f} 0 0 {draw_h:.2f} 48 {y_img:.2f} cm",
                    f"/{im_name} Do",
                    "Q",
                ]
            )
            y_cursor = y_img - 32.0

            img_obj = (
                f"{next_obj_num} 0 obj << /Type /XObject /Subtype /Image /Width {w} /Height {h} "
                f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode "
                f"/Length {len(jpg_bytes)} >>\nstream\n".encode("ascii")
                + jpg_bytes
                + b"\nendstream endobj\n"
            )
            img_objs.append(img_obj)
            next_obj_num += 1

        p2_stream = "\n".join(p2_cmds).encode("latin-1", errors="replace")
        xobj_dict = " ".join(xobj_entries)
        objects.append(
            f"6 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> /XObject << {xobj_dict} >> >> "
            f"/Contents 7 0 R >> endobj\n".encode("ascii")
        )
        objects.append(
            f"7 0 obj << /Length {len(p2_stream)} >>\nstream\n".encode("ascii")
            + p2_stream
            + b"\nendstream endobj\n"
        )
        objects.extend(img_objs)

    buf = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = [0]
    for obj in objects:
        offsets.append(len(buf))
        buf.extend(obj)
    xref_pos = len(buf)
    buf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for off in offsets[1:]:
        buf.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    trailer = (
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    )
    buf.extend(trailer.encode("ascii"))
    return bytes(buf)


def render_crop_health_pdf(rendered_html: str, context: dict[str, Any] | None = None) -> bytes:
    """Render HTML string into PDF bytes via WeasyPrint, falling back to pure-Python PDF+images."""
    try:
        from weasyprint import CSS, HTML

        stylesheets = [CSS(filename=str(CSS_PATH))] if CSS_PATH.exists() else []
        pdf_bytes: bytes = HTML(string=rendered_html).write_pdf(stylesheets=stylesheets)
        return pdf_bytes
    except OSError:
        ctx = context or {}
        lines = [
            f"TerraIntel Crop Health Report - {ctx.get('region_name', 'Region')}",
            f"Analysis Window: {ctx.get('start_date', '')} to {ctx.get('end_date', '')}",
            f"Valid Cropland Coverage: {ctx.get('valid_pixel_pct', '0.00')}%",
        ]
        if ctx.get("low_coverage"):
            lines.append("WARNING: INSUFFICIENT COVERAGE (< 30% valid pixels)")
        mean_v = ctx.get("mean_ndvi", "0.0000")
        p50_v = ctx.get("p50_ndvi", "0.0000")
        lines.extend(
            [
                f"Mean NDVI: {mean_v} (p50: {p50_v})",
                f"Cropland Area: {ctx.get('cropland_area_ha', '0.00')} ha",
                f"Absolute Low Greenness: {ctx.get('absolute_low_area_ha', '0.00')} ha",
                f"Relative Low Greenness: {ctx.get('relative_low_area_ha', '0.00')} ha",
                "",
                "Vigour Class Breakdown:",
            ]
        )
        for row in ctx.get("class_stats", []):
            lines.append(
                f"  - {row['vigour_class']}: {row['area_ha']} ha ({row['area_pct']}%)"
            )

        prev = ctx.get("previous_period")
        if prev:
            p_win = f"{prev['start_date']} to {prev['end_date']}"
            c_win = f"{ctx.get('start_date', '')} to {ctx.get('end_date', '')}"
            lines.extend(
                [
                    "",
                    "Multi-Period Comparison (vs Previous Recorded Window):",
                    f"  - Previous Period: {p_win} (Mean NDVI: {prev['mean_ndvi']})",
                    f"  - Current Period:  {c_win} (Mean NDVI: {mean_v})",
                    f"  - Delta NDVI (Current - Previous): {prev['delta_ndvi']}",
                ]
            )

        lines.extend(["", "Sentinel-2 Scene Provenance (COPERNICUS/S2_SR_HARMONIZED / L2A):"])
        for sc in ctx.get("scenes", [])[:12]:
            lines.append(f"  - {sc.get('scene_id', '')} ({sc.get('acquired_at', '')})")

        images: list[tuple[str, Path]] = []
        ndvi_path = ctx.get("ndvi_image_path")
        tc_path = ctx.get("tc_image_path")
        if isinstance(ndvi_path, Path):
            images.append(("NDVI Classification Output (ColorBrewer YlGn 0.00 - 0.90)", ndvi_path))
        if isinstance(tc_path, Path):
            images.append(("Sentinel-2 True-Colour Output", tc_path))

        return _build_pdf_with_images(lines, images)


def render_compare_pdf(
    *,
    region_name: str,
    period_a_start: str,
    period_a_end: str,
    period_b_start: str,
    period_b_end: str,
    mean_delta_ndvi: str,
    analysed_area_ha: str,
    bins: list[dict[str, str]],
    diff_tile_url: str = "",
) -> bytes:
    """Build a downloadable PDF report for a two-period Delta NDVI comparison."""
    lines = [
        f"TerraIntel Two-Period NDVI Comparison Report - {region_name}",
        f"Period A: {period_a_start} to {period_a_end}",
        f"Period B: {period_b_start} to {period_b_end}",
        f"Mean Delta NDVI (Period B - Period A): {mean_delta_ndvi}",
        f"Analysed Cropland Area: {analysed_area_ha} ha",
        "",
        "Delta NDVI Distribution (+/- 0.05 bins with area > 0%):",
    ]
    non_zero = [b for b in bins if float(b.get("area_pct", "0")) > 0.0]
    for b in non_zero[:25]:
        lines.append(
            f"  [{b['bin_min']}, {b['bin_max']}): {b['area_ha']} ha ({b['area_pct']}%)"
        )

    images: list[tuple[str, Path]] = []
    diff_path = _media_url_to_path(diff_tile_url)
    if diff_path is not None:
        images.append(
            (
                f"Delta NDVI Output (Period B - Period A, RdBu -0.50 to +0.50) | {region_name}",
                diff_path,
            )
        )
    return _build_pdf_with_images(lines, images)


def _to_data_uri(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def build_report_context(
    analysis: Any,
    previous_analysis: Any | None = None,
) -> dict[str, Any]:
    """Extract template context (including output images & previous period)."""
    ndvi_path = _media_url_to_path(getattr(analysis, "ndvi_tile_url", ""))
    tc_path = _media_url_to_path(getattr(analysis, "true_colour_tile_url", ""))

    previous_period: dict[str, str] | None = None
    if previous_analysis is not None:
        delta = float(analysis.mean_ndvi) - float(previous_analysis.mean_ndvi)
        previous_period = {
            "start_date": previous_analysis.start_date.isoformat(),
            "end_date": previous_analysis.end_date.isoformat(),
            "mean_ndvi": f"{previous_analysis.mean_ndvi:.4f}",
            "delta_ndvi": f"{delta:+.4f}",
        }

    return {
        "region_name": analysis.region.name,
        "start_date": analysis.start_date.isoformat(),
        "end_date": analysis.end_date.isoformat(),
        "mean_ndvi": f"{analysis.mean_ndvi:.4f}",
        "p50_ndvi": f"{analysis.p50_ndvi:.4f}",
        "cropland_area_ha": f"{analysis.cropland_area_ha:.2f}",
        "absolute_low_area_ha": f"{analysis.absolute_low_area_ha:.2f}",
        "relative_low_area_ha": f"{analysis.relative_low_area_ha:.2f}",
        "valid_pixel_pct": f"{analysis.valid_pixel_pct:.2f}",
        "low_coverage": bool(analysis.low_coverage),
        "class_stats": [
            {
                "vigour_class": cs.vigour_class,
                "area_ha": f"{cs.area_ha:.2f}",
                "area_pct": f"{cs.area_pct:.2f}",
            }
            for cs in analysis.class_stats.all()
        ],
        "scenes": analysis.scenes or [],
        "previous_period": previous_period,
        "ndvi_image_path": ndvi_path,
        "tc_image_path": tc_path,
        "ndvi_data_uri": _to_data_uri(ndvi_path),
        "tc_data_uri": _to_data_uri(tc_path),
    }
