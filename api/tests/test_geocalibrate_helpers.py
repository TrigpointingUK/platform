"""
Edge-case and helper coverage for api.utils.geocalibrate.

The synthetic end-to-end happy path lives in test_geocalibrate_synthetic.py;
this file targets the inverse projection helper, validation errors, the
no-edges path and the Natural Earth coastline downloader (with requests mocked).
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from api.utils import geocalibrate
from api.utils.geocalibrate import (
    CalibrationResult,
    _affine_from_correspondences,
    _sobel_edge_points,
    calibrate_affine_from_coastline,
    download_natural_earth_110m_uk_coastline,
    download_natural_earth_coastline,
)


class TestCalibrationResultInverse:
    def test_xy_to_lonlat_round_trips_with_lonlat_to_xy(self):
        # Simple scale+translate affine and its exact inverse.
        affine = np.array([[2.0, 0.0, 1.0], [0.0, 3.0, -2.0]])
        inverse = np.array([[0.5, 0.0, -0.5], [0.0, 1.0 / 3.0, 2.0 / 3.0]])
        r = CalibrationResult(
            affine=affine,
            inverse=inverse,
            pixel_bbox=(0, 0, 10, 10),
            bounds_geo=(0, 0, 1, 1),
        )
        x, y = r.lonlat_to_xy(3.0, 4.0)
        lon, lat = r.xy_to_lonlat(x, y)
        assert lon == pytest.approx(3.0)
        assert lat == pytest.approx(4.0)


class TestAffineFromCorrespondences:
    def test_raises_on_too_few_points(self):
        src = np.zeros((2, 2))
        dst = np.zeros((2, 2))
        with pytest.raises(ValueError, match="at least 3"):
            _affine_from_correspondences(src, dst)

    def test_raises_on_mismatched_lengths(self):
        src = np.zeros((4, 2))
        dst = np.zeros((3, 2))
        with pytest.raises(ValueError):
            _affine_from_correspondences(src, dst)


class TestSobelEmptyImage:
    def test_blank_image_yields_no_edge_points(self):
        blank = Image.new("L", (20, 20), color=128)
        pts = _sobel_edge_points(blank, threshold=10.0)
        assert pts.shape == (0, 2)


class TestCalibrateValidation:
    def test_no_edges_raises(self, tmp_path):
        blank = Image.new("L", (20, 20), color=128)
        path = tmp_path / "blank.png"
        blank.save(path)
        # Force the "no edges" branch with an impossibly high threshold.
        with patch(
            "api.utils.geocalibrate._sobel_edge_points",
            return_value=np.zeros((0, 2), dtype=np.float32),
        ):
            with pytest.raises(ValueError, match="No edges detected"):
                calibrate_affine_from_coastline(str(path), [(0.0, 50.0)] * 5)

    def test_non_nx2_coastline_raises(self, tmp_path):
        # Add a bright square so Sobel detects some edges.
        arr = np.zeros((20, 20), dtype=np.uint8)
        arr[5:15, 5:15] = 255
        Image.fromarray(arr, mode="L").save(tmp_path / "sq.png")
        with pytest.raises(ValueError, match="Nx2"):
            calibrate_affine_from_coastline(str(tmp_path / "sq.png"), [(1.0, 2.0, 3.0)])


def _fake_geojson():
    return {
        "features": [
            {
                "geometry": {
                    "type": "LineString",
                    # one point inside the UK window, one outside
                    "coordinates": [[-2.0, 51.0], [40.0, 10.0]],
                }
            },
            {"geometry": {"type": "Point", "coordinates": [-2.0, 51.0]}},
        ]
    }


class TestDownloadCoastline:
    def test_invalid_resolution_raises(self):
        with pytest.raises(ValueError, match="resolution"):
            download_natural_earth_coastline("999m")

    def test_filters_to_uk_window(self):
        resp = MagicMock()
        resp.json.return_value = _fake_geojson()
        resp.raise_for_status.return_value = None
        with patch.object(geocalibrate.requests, "get", return_value=resp) as m_get:
            pts = download_natural_earth_coastline("10m")
        m_get.assert_called_once()
        # Only the in-window point survives; non-LineString feature ignored.
        assert pts == [(-2.0, 51.0)]

    def test_applies_max_points_cap(self):
        coords = [[lon, 51.0] for lon in np.linspace(-10, 4, 100)]
        resp = MagicMock()
        resp.json.return_value = {
            "features": [{"geometry": {"type": "LineString", "coordinates": coords}}]
        }
        resp.raise_for_status.return_value = None
        with patch.object(geocalibrate.requests, "get", return_value=resp):
            pts = download_natural_earth_coastline("10m", max_points=10)
        assert len(pts) == 10

    def test_no_points_in_window_raises(self):
        resp = MagicMock()
        resp.json.return_value = {
            "features": [
                {"geometry": {"type": "LineString", "coordinates": [[40.0, 10.0]]}}
            ]
        }
        resp.raise_for_status.return_value = None
        with patch.object(geocalibrate.requests, "get", return_value=resp):
            with pytest.raises(RuntimeError, match="No coastline points"):
                download_natural_earth_coastline("10m")

    def test_110m_wrapper_delegates(self):
        with patch.object(
            geocalibrate,
            "download_natural_earth_coastline",
            return_value=[(1.0, 2.0)],
        ) as m:
            out = download_natural_earth_110m_uk_coastline(max_points=123)
        m.assert_called_once_with("110m", max_points=123)
        assert out == [(1.0, 2.0)]
