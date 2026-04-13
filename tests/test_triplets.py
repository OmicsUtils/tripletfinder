import pandas as pd
import pytest

from triplet_finder import find_triplets_with_details


def make_simple_triangle():
    """
    Three cells forming a tight triangle.
    Should always form one triplet.
    """
    return pd.DataFrame({
        "image_sliced": ["img1", "img1", "img1"],
        "centroid_x_um": [0.0, 1.0, 0.5],
        "centroid_y_um": [0.0, 0.0, 0.8],
        "cell_min_caliper": [1.0, 1.0, 1.0],
        "cell_max_caliper": [1.0, 1.0, 1.0],
    })


def make_spaced_cells():
    """
    Three cells far apart unless using large radii correction.
    """
    return pd.DataFrame({
        "image_sliced": ["img1", "img1", "img1"],
        "centroid_x_um": [0.0, 10.0, 20.0],
        "centroid_y_um": [0.0, 0.0, 0.0],
        "cell_min_caliper": [15.0, 15.0, 15.0],
        "cell_max_caliper": [15.0, 15.0, 15.0],
    })


# ------------------------
# CENTROID MODE TESTS
# ------------------------

def test_centroid_mode_finds_triplet():
    df = make_simple_triangle()

    result = find_triplets_with_details(
        input_data=df,
        image_col="image_sliced",
        x_col="centroid_x_um",
        y_col="centroid_y_um",
        distance_mode="centroid",
        threshold=2.0,
        return_triplets=True,
    )

    assert result is not None
    assert len(result) == 1


def test_centroid_mode_no_triplet_if_far():
    df = make_spaced_cells()

    result = find_triplets_with_details(
        input_data=df,
        image_col="image_sliced",
        x_col="centroid_x_um",
        y_col="centroid_y_um",
        distance_mode="centroid",
        threshold=5.0,
        return_triplets=True,
    )

    assert len(result) == 0


# ------------------------
# EFFECTIVE MODE TESTS
# ------------------------

def test_effective_mode_finds_triplet_due_to_radii():
    df = make_spaced_cells()

    # Large radii make effective distance small
    result = find_triplets_with_details(
        input_data=df,
        image_col="image_sliced",
        x_col="centroid_x_um",
        y_col="centroid_y_um",
        min_cell_diameter_column="cell_min_caliper",
        max_cell_diameter_column="cell_max_caliper",
        distance_mode="effective",
        threshold=5.0,
        return_triplets=True,
    )

    assert result is not None
    assert len(result) == 1


def test_effective_mode_requires_diameter_columns():
    df = make_simple_triangle()

    with pytest.raises(ValueError):
        find_triplets_with_details(
            input_data=df,
            image_col="image_sliced",
            x_col="centroid_x_um",
            y_col="centroid_y_um",
            distance_mode="effective",
            threshold=5.0,
            return_triplets=True,
        )


# ------------------------
# GENERAL BEHAVIOR TESTS
# ------------------------

def test_invalid_distance_mode():
    df = make_simple_triangle()

    with pytest.raises(ValueError):
        find_triplets_with_details(
            input_data=df,
            image_col="image_sliced",
            x_col="centroid_x_um",
            y_col="centroid_y_um",
            distance_mode="invalid_mode",
            threshold=5.0,
        )


def test_streaming_mode_returns_none():
    df = make_simple_triangle()

    result = find_triplets_with_details(
        input_data=df,
        image_col="image_sliced",
        x_col="centroid_x_um",
        y_col="centroid_y_um",
        distance_mode="centroid",
        threshold=2.0,
        return_triplets=False,
    )

    assert result is None


def test_empty_result_has_expected_columns():
    df = make_spaced_cells()

    result = find_triplets_with_details(
        input_data=df,
        image_col="image_sliced",
        x_col="centroid_x_um",
        y_col="centroid_y_um",
        distance_mode="centroid",
        threshold=1.0,
        return_triplets=True,
    )

    assert list(result.columns) == [
        "image", "cell1_idx", "cell2_idx", "cell3_idx"
    ]