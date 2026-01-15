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
    min_cell_diameter_column: str,
    max_cell_diameter_column: str,
    threshold: float,
    output_dir: str | None = None,
    skip_processed: bool = True,
    return_triplets: bool = False,
    metadata: dict | None = None,
    logger=None,
) -> pd.DataFrame | None:
    """
    Identify spatial triplets of cells within a specified effective distance threshold.

    For each image (as defined by `image_col`), this function finds all unique triplets
    of cells such that each pair within the triplet is within `threshold` distance of
    one another after accounting for cell size. Pairwise distances are computed as the
    centroid-to-centroid distance minus the sum of the two cells' radii, where each
    radius is defined as the average of the minimum and maximum cell diameter columns.

    The algorithm operates independently per image:
      1. Cells are grouped by `image_col`.
      2. A KD-tree is constructed using cell centroid coordinates.
      3. Cell–cell adjacencies are determined based on the effective distance criterion.
      4. Fully connected triplets (3-cliques) are enumerated.
      5. For each triplet, the full per-cell metadata is attached with cell-specific
         prefixes (e.g. `cell1_`, `cell2_`, `cell3_`).

    Optionally, per-image CSV files can be written, and images with existing outputs
    can be skipped. Metadata headers are written to per-image
    outputs if `metadata` is provided.

    If `return_triplets` is False, triplets are not accumulated in memory and
    the function returns None.

    Parameters
    ----------
    input_data : pandas.DataFrame
        Input table containing one row per cell, including spatial coordinates,
        image identifiers, and cell size information.
    image_col : str
        Column name identifying the image or field of view to group cells by.
    x_col : str
        Column name for the x-coordinate of the cell centroid.
    y_col : str
        Column name for the y-coordinate of the cell centroid.
    min_cell_diameter_column : str
        Column name for the minimum cell diameter (or caliper).
    max_cell_diameter_column : str
        Column name for the maximum cell diameter (or caliper).
    threshold : float
        Maximum allowed effective distance between two cells for them to be considered
        adjacent. Effective distance is defined as centroid distance minus the sum of
        the two cell radii.
    output_dir : str or None, optional
        Directory in which to write per-image triplet CSV files. If None, no per-image
        files are written.
    skip_processed : bool, optional
        If True and `output_dir` is provided, images for which an output file already
        exists are skipped.
    return_triplets : bool, optional
        If True, will return pandas dataframe with all triplets (warning, may require much memory to do this). Defaults to False. 
    logger : logging.Logger or None, optional
        Logger used for status and progress messages. If None, a module-level logger
        is used.

    Returns
    -------
    pandas.DataFrame
        A DataFrame where each row corresponds to a single triplet. Columns include:
        - `image`, `cell1_idx`, `cell2_idx`, `cell3_idx`
        - All original input columns duplicated and prefixed with `cell1_`, `cell2_`,
          and `cell3_` for the three cells in the triplet.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    required_cols = {
        image_col,
        x_col,
        y_col,
        min_cell_diameter_column,
        max_cell_diameter_column,
    }
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
        radii = (
            subinput_data[min_cell_diameter_column].to_numpy()
            + subinput_data[max_cell_diameter_column].to_numpy()
        ) / 2.0
        idx = subinput_data["orig_idx"].to_numpy()
        N = len(coords)

        if N < 3:
            continue

        tree = cKDTree(coords)
        max_rad_sum = np.max(radii) * 2.0
        search_radius = threshold + max_rad_sum

        adj = {i: set() for i in range(N)}

        for i in range(N):
            for j in tree.query_ball_point(coords[i], search_radius):
                if j <= i:
                    continue
                d_cent = np.linalg.norm(coords[i] - coords[j])
                d_eff = d_cent - (radii[i] + radii[j])
                if d_eff <= threshold:
                    adj[i].add(j)
                    adj[j].add(i)

        img_records = []

        for i in range(N):
            for j in adj[i]:
                if j <= i:
                    continue
                for k in adj[i].intersection(adj[j]):
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

        if out_path:
            df_img = pd.DataFrame(img_records)

            with open(out_path, "w") as fh:
                if metadata:
                    for k, v in metadata.items():
                        fh.write(f"# {k}: {v}\n")
                df_img.to_csv(fh, index=False)

            logger.info(f"Wrote {out_path}")

    if return_triplets:
        return pd.DataFrame(triplet_records)

    return None