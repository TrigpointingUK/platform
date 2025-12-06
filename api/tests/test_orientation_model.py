"""Tests for orientation model utilities."""

import numpy as np

from api.services.orientation_model import _softmax


class TestSoftmax:
    """Tests for the _softmax function."""

    def test_softmax_basic(self):
        """Basic softmax computation."""
        x = np.array([1.0, 2.0, 3.0])
        result = _softmax(x)
        # Should sum to 1
        assert np.isclose(np.sum(result), 1.0)
        # Higher input should have higher probability
        assert result[2] > result[1] > result[0]

    def test_softmax_uniform(self):
        """Uniform inputs give uniform outputs."""
        x = np.array([1.0, 1.0, 1.0, 1.0])
        result = _softmax(x)
        assert np.allclose(result, [0.25, 0.25, 0.25, 0.25])

    def test_softmax_numerical_stability(self):
        """Softmax handles large values without overflow."""
        # Large values that would overflow exp() without the max subtraction
        x = np.array([1000.0, 1001.0, 1002.0])
        result = _softmax(x)
        assert np.isclose(np.sum(result), 1.0)
        assert not np.any(np.isnan(result))
        assert not np.any(np.isinf(result))

    def test_softmax_zeros(self):
        """Softmax of zeros gives uniform distribution."""
        x = np.array([0.0, 0.0, 0.0])
        result = _softmax(x)
        assert np.allclose(result, [1 / 3, 1 / 3, 1 / 3])

    def test_softmax_negative_values(self):
        """Softmax handles negative values correctly."""
        x = np.array([-1.0, 0.0, 1.0])
        result = _softmax(x)
        assert np.isclose(np.sum(result), 1.0)
        # Verify ordering
        assert result[2] > result[1] > result[0]
