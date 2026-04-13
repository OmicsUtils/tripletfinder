#!/usr/bin/env python3

import os
import logging

import pandas as pd
import numpy as np
from scipy.spatial import cKDTree


def setup_logger(logfile_path=None, verbose=True):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    if logfile_path:
        logdir = os.path.dirname(logfile_path)
        if logdir:
            os.makedirs(logdir, exist_ok=True)

        file_handler = logging.FileHandler(logfile_path, mode="a")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if verbose:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    # Prevent log propagation to root logger
    logger.propagate = False

    return logger


def find_triplets_with_details(
    input_data: pd.DataFrame,
    image_col: str,
    x_col: str,
    y_col: str,
    min_cell_diameter_column: str | None = None,
    max_cell_diameter_column: str | None = None,
    distance_mode: str = "effective",
    threshold: float = 15.0,
    output_dir: str | None = None,
    skip_processed: bool = True,
    return_triplets: bool = False,
    metadata: dict | None = None,
    logger=None,
) -> pd.DataFrame | None:
    """
    Identify spatial triplets of cells using either centroid or effective distance.

    distance_mode:
        - "effective": centroid distance minus radii (default)
        - "centroid": raw centroid-to-centroid distance
    """

    if logger is None:
        logger = logging.getLogger(__name__)

    if distance_mode not in {"effective", "centroid"}:
        raise ValueError("distance_mode must be 'effective' or 'centroid'")

    # Required columns
    required_cols = {image_col, x_col, y_col}

    if distance_mode == "effective":
        if min_cell_diameter_column is None or max_cell_diameter_column is None:
            raise ValueError("min/max diameter columns required for effective distance")
        required_cols.update({min_cell_diameter_column, max_cell_diameter_column})

    missing = required_cols - set(input_data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    input_data2 = input_data.reset_index().rename(columns={"index": "orig_idx"})
    triplet_records = [] if return_triplets else None

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    for img_id, subinput_data in input_data2.groupby(image_col):
        out_path = None
        if output_dir:
            out_path = os.path.join(output_dir, f"{img_id}_triplets.csv")
            if skip_processed and os.path.exists(out_path):
                logger.info(f"Skipping {img_id} (already processed)")
                continue

        logger.info(f"Processing {img_id}")

        coords = subinput_data[[x_col, y_col]].to_numpy()
        idx = subinput_data["orig_idx"].to_numpy()
        N = len(coords)

        if N < 3:
            continue

        # Radii
        if distance_mode == "effective":
            radii = (
                subinput_data[min_cell_diameter_column].to_numpy()
                + subinput_data[max_cell_diameter_column].to_numpy()
            ) / 2.0
        else:
            radii = np.zeros(N)

        # KDTree
        tree = cKDTree(coords)

        if distance_mode == "effective":
            max_rad_sum = np.max(radii) * 2.0
            search_radius = threshold + max_rad_sum
        else:
            search_radius = threshold

        # Build adjacency graph
        adj = {i: set() for i in range(N)}

        for i in range(N):
            neighbors = tree.query_ball_point(coords[i], search_radius)
            for j in neighbors:
                if j <= i:
                    continue

                d_cent = np.linalg.norm(coords[i] - coords[j])

                if distance_mode == "effective":
                    d_val = d_cent - (radii[i] + radii[j])
                else:
                    d_val = d_cent

                if d_val <= threshold:
                    adj[i].add(j)
                    adj[j].add(i)

        # Find triplets
        img_records = []

        for i in range(N):
            for j in adj[i]:
                if j <= i:
                    continue

                common = adj[i].intersection(adj[j])

                for k in common:
                    if k <= j:
                        continue

                    record = {
                        "image": img_id,
                        "cell1_idx": idx[i],
                        "cell2_idx": idx[j],
                        "cell3_idx": idx[k],
                    }

                    for prefix, row_idx in zip(
                        ["cell1", "cell2", "cell3"], [i, j, k]
                    ):
                        row = subinput_data.iloc[row_idx].to_dict()
                        for col, val in row.items():
                            record[f"{prefix}_{col}"] = val

                    img_records.append(record)
                    if return_triplets:
                        triplet_records.append(record)

        # Write per-image output
        if out_path:
            df_img = pd.DataFrame(img_records)

            with open(out_path, "w") as fh:
                if metadata:
                    for k in sorted(metadata):
                        fh.write(f"# {k}: {metadata[k]}\n")
                df_img.to_csv(fh, index=False)

            logger.info(f"Wrote {out_path}")

    # Return combined output if requested
    if return_triplets:
        if triplet_records:
            return pd.DataFrame(triplet_records)
        else:
            return pd.DataFrame(
                columns=["image", "cell1_idx", "cell2_idx", "cell3_idx"]
            )

    return None