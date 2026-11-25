"""Unit tests verifying PRD §8.2 masking order and NDVI clamping."""
from unittest.mock import MagicMock

from services.ndvi_service import apply_s2_mask_pipeline, compute_ndvi_band


def test_mask_pipeline_order() -> None:
    """Verify 1. clip -> 2. WorldCover -> 3. SCL -> 4. MSK_CLDPRB -> 5. B8+B4>0."""
    call_order: list[str] = []
    img = MagicMock()
    aoi = MagicMock()
    cropland = MagicMock()

    def _clip(_aoi: object) -> MagicMock:
        call_order.append("clip")
        return img

    img.clip.side_effect = _clip

    def _update_mask(mask: object) -> MagicMock:
        if mask is cropland:
            call_order.append("worldcover")
        else:
            call_order.append(f"mask_{len(call_order)}")
        return img

    img.updateMask.side_effect = _update_mask
    img.select.return_value = img
    img.neq.return_value = img
    img.And.return_value = img
    img.lte.return_value = img
    img.toFloat.return_value = img
    img.add.return_value = img
    img.gt.return_value = img

    apply_s2_mask_pipeline(img, aoi, cropland)
    assert call_order[0] == "clip"
    assert call_order[1] == "worldcover"
    assert len(call_order) == 5


def test_compute_ndvi_band_clamps() -> None:
    img = MagicMock()
    ndvi_img = MagicMock()
    img.normalizedDifference.return_value = ndvi_img
    ndvi_img.rename.return_value = ndvi_img
    compute_ndvi_band(img)
    img.normalizedDifference.assert_called_once_with(["B8", "B4"])
    ndvi_img.clamp.assert_called_once_with(-1.0, 1.0)
