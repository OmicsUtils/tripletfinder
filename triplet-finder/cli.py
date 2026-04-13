# triad_finder/cli.py

import argparse
import os
import sys
from datetime import datetime
import pandas as pd

from .triplet_finder import find_triplets_with_details, setup_logger


def main():
    parser = argparse.ArgumentParser(
        description="Find spatial cell triplets within distance threshold"
    )

    # I/O
    parser.add_argument("--input", required=True, help="Input CSV file")
    parser.add_argument("--output", help="Combined output CSV file")
    parser.add_argument("--output-dir", help="Optional per-image output directory")

    # Geometry
    parser.add_argument("--threshold", type=float, default=15.0)
    parser.add_argument("--distance-mode", choices=["effective", "centroid"], default="effective")

    parser.add_argument("--image-col", default="image_sliced")
    parser.add_argument("--x-col", default="centroid_x_um")
    parser.add_argument("--y-col", default="centroid_y_um")
    parser.add_argument("--min-cell-diameter-col", default="cell_min_caliper")
    parser.add_argument("--max-cell-diameter-col", default="cell_max_caliper")

    # Filtering
    parser.add_argument("--exclude-col", help="Column name used to exclude cells")
    parser.add_argument(
        "--exclude-values",
        nargs="+",
        help="One or more values to exclude from processing",
    )

    # Execution behavior
    parser.add_argument("--no-skip", action="store_true")
    parser.add_argument(
        "--combined-output",
        action="store_true",
        help="Return all triplets in memory and write a combined output CSV",
    )

    # Reporting
    parser.add_argument("--summary", action="store_true", help="Print summary and exit")
    parser.add_argument("--dry-run", action="store_true", help="Alias for --summary")

    # Metadata / logging
    parser.add_argument("--no-metadata", action="store_true")
    parser.add_argument("--logfile", help="Log file path")

    args = parser.parse_args()

    logger = setup_logger(args.logfile)

    logger.info("Loading data")
    input_data = pd.read_csv(args.input)

    # Pre-filter stats
    total_cells = len(input_data)
    total_images = input_data[args.image_col].nunique()

    # Validate exclusion args
    if bool(args.exclude_col) ^ bool(args.exclude_values):
        raise ValueError("--exclude-col and --exclude-values must be used together")

    # Apply exclusion
    if args.exclude_col:
        if args.exclude_col not in input_data.columns:
            raise ValueError(f"Exclude column not found: {args.exclude_col}")

        before = len(input_data)
        input_data = input_data[
            ~input_data[args.exclude_col].isin(args.exclude_values)
        ]
        logger.info(f"Excluded {before - len(input_data)} rows")

    if input_data.empty:
        logger.warning("No cells remain after filtering; exiting")
        return

    images_with_3plus = (
        input_data.groupby(args.image_col).size().ge(3).sum()
    )

    # Summary / dry-run
    if args.summary or args.dry_run:
        print("\nSummary")
        print("-------")
        print(f"Images (total): {total_images}")
        print(f"Cells (total): {total_cells}")
        print(f"Cells after filtering: {len(input_data)}")
        print(f"Images with ≥3 cells: {images_with_3plus}")

        print("\nParameters")
        print("----------")
        print(f"Image column: {args.image_col}")
        print(f"X coordinate column: {args.x_col}")
        print(f"Y coordinate column: {args.y_col}")
        print(f"Distance mode: {args.distance_mode}")
        print(f"Distance threshold: {args.threshold}")

        if args.distance_mode == "effective":
            print(f"Min cell diameter column: {args.min_cell_diameter_col}")
            print(f"Max cell diameter column: {args.max_cell_diameter_col}")

        print("\nOutputs")
        print("-------")
        print(f"Would write per-image CSVs: {'yes' if args.output_dir else 'no'}")
        print(f"Would skip existing outputs: {'yes' if not args.no_skip else 'no'}")
        print(f"Would return combined output: {'yes' if args.combined_output else 'no'}")

        return

    # Ensure output directory exists BEFORE core runs
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)

    # Require output if combined mode
    if args.combined_output and not args.output:
        raise ValueError("--output is required if --combined-output is set")

    # Build metadata
    metadata = None
    if not args.no_metadata:
        try:
            from importlib.metadata import version
            tool_version = version("triplet-finder")
        except Exception:
            tool_version = "unknown"

        metadata = {
            "tool": "triplet-finder",
            "version": tool_version,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "command": " ".join(sys.argv),
            "distance_mode": args.distance_mode,
            "threshold": args.threshold,
            "x_col": args.x_col,
            "y_col": args.y_col,
        }

        if args.distance_mode == "effective":
            metadata["min_cell_diameter_col"] = args.min_cell_diameter_col
            metadata["max_cell_diameter_col"] = args.max_cell_diameter_col

    # Call core
    triplets = find_triplets_with_details(
        input_data=input_data,
        image_col=args.image_col,
        x_col=args.x_col,
        y_col=args.y_col,
        min_cell_diameter_column=args.min_cell_diameter_col,
        max_cell_diameter_column=args.max_cell_diameter_col,
        distance_mode=args.distance_mode,
        threshold=args.threshold,
        output_dir=args.output_dir,
        skip_processed=not args.no_skip,
        return_triplets=args.combined_output,
        metadata=metadata,
        logger=logger,
    )

    # Write combined output
    if args.combined_output:
        triplets.to_csv(args.output, index=False)
        logger.info(f"Wrote combined output to {args.output}")


if __name__ == "__main__":
    main()