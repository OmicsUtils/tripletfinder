# triplet-finder

This tool identifies spatial triplets of cells based on a user-defined distance criterion. It was originally designed as a preprocessing step for identifying immune cell triads, but may also be useful for other spatial analysis tasks.

> **Definition of Distance Criteria and Triplets**
>
> The tool supports two distance modes:
>
> - **effective**: pairwise distances are computed as the centroid-to-centroid distance
>   minus the sum of the two cells’ radii, where each radius is defined as the average
>   of the minimum and maximum cell diameter columns.
> - **centroid**: pairwise distances are computed directly as centroid-to-centroid
>   distance, without accounting for cell size.
>
> Two cells are considered capable of interaction if their pairwise distance under the
> selected mode is less than a user-defined threshold, representing the assumed spatial
> range over which cells can communicate or influence one another.
>
> A **triplet** is defined as a fully connected set of three cells (a 3-clique) in which
> all three pairwise distances satisfy this criterion within a single image or field of view.

The tool is designed to be:  
- memory-safe by default (streaming mode)  
- usable as both a Python library and a command-line tool  
- suitable for large microscopy / spatial biology datasets  

---

## Installation

### From source

Clone the repository and install in editable mode:

```bash
pip install -e .
````

This will install:

* the Python package: `triplet_finder`  
* the CLI command: `triplet-finder`  

### Dependencies

Python >= 3.9 is required.

Core dependencies:

* pandas
* numpy
* scipy

These are installed automatically via `pip`.

---

## Command-Line Usage

After installation, the CLI is available as:

```bash
triplet-finder --help
```

### Basic usage (streaming, low memory)

```bash
triplet-finder \
  --input cells.csv \
  --output-dir per_image_triplets/
```

This:

* processes each image independently
* writes one CSV per image if `--output-dir` is provided
* does **not** keep all triplets in memory by default

### Choose the distance mode

#### Effective distance mode

```bash
triplet-finder \
  --input cells.csv \
  --distance-mode effective \
  --output-dir per_image_triplets/
```

#### Centroid distance mode

```bash
triplet-finder \
  --input cells.csv \
  --distance-mode centroid \
  --output-dir per_image_triplets/
```

### Write a combined output CSV

```bash
triplet-finder \
  --input cells.csv \
  --output-dir per_image_triplets/ \
  --combined-output \
  --output all_triplets.csv
```

This:

* writes per-image CSVs
* also returns all triplets in memory
* writes a combined CSV

For large datasets, this may require substantial memory.

### Excluding cells by metadata

```bash
triplet-finder \
  --input cells.csv \
  --exclude-col tentative_cell_type \
  --exclude-values Unknown \
  --output-dir per_image_triplets/
```

### Summary / dry-run mode

Prints a summary of the dataset and parameters without computing triplets:

```bash
triplet-finder \
  --input cells.csv \
  --exclude-col tentative_cell_type \
  --exclude-values Unknown \
  --distance-mode effective \
  --summary
```

Example output:

```text
Summary
-------
Images (total): 132
Cells (total): 45892
Cells after filtering: 37211
Images with ≥3 cells: 129

Parameters
----------
Image column: image_sliced
X coordinate column: centroid_x_um
Y coordinate column: centroid_y_um
Distance mode: effective
Distance threshold: 15.0
Min cell diameter column: cell_min_caliper
Max cell diameter column: cell_max_caliper
```

In `centroid` mode, the minimum and maximum cell diameter columns are not used.

### Metadata headers

By default, per-image CSV outputs include metadata headers such as tool version, parameters, and command invocation.

To disable metadata headers:

```bash
triplet-finder --no-metadata ...
```

---

## Python API Usage

The core functionality is available as a Python function.

### Import

```python
from triplet_finder import find_triplets_with_details
```

### Example: streaming mode with effective distance

```python
import pandas as pd
from triplet_finder import find_triplets_with_details

df = pd.read_csv("cells.csv")

find_triplets_with_details(
    input_data=df,
    image_col="image_sliced",
    x_col="centroid_x_um",
    y_col="centroid_y_um",
    min_cell_diameter_column="cell_min_caliper",
    max_cell_diameter_column="cell_max_caliper",
    distance_mode="effective",
    threshold=15.0,
    output_dir="per_image_triplets",
    return_triplets=False,
)
```

This writes per-image CSVs and returns `None`.

### Example: centroid mode

```python
triplets = find_triplets_with_details(
    input_data=df,
    image_col="image_sliced",
    x_col="centroid_x_um",
    y_col="centroid_y_um",
    distance_mode="centroid",
    threshold=15.0,
    return_triplets=True,
)
```

### Example: returning all triplets with effective distance

```python
triplets = find_triplets_with_details(
    input_data=df,
    image_col="image_sliced",
    x_col="centroid_x_um",
    y_col="centroid_y_um",
    min_cell_diameter_column="cell_min_caliper",
    max_cell_diameter_column="cell_max_caliper",
    distance_mode="effective",
    threshold=15.0,
    return_triplets=True,
)

print(triplets.head())
```

### Metadata in Python usage

```python
metadata = {
    "experiment": "Immune_Triads_Preprocessing",
    "threshold": 15.0,
    "distance_mode": "effective",
    "notes": "Unknown cells excluded",
}

find_triplets_with_details(
    input_data=df,
    image_col="image_sliced",
    x_col="centroid_x_um",
    y_col="centroid_y_um",
    min_cell_diameter_column="cell_min_caliper",
    max_cell_diameter_column="cell_max_caliper",
    distance_mode="effective",
    threshold=15.0,
    output_dir="per_image_triplets",
    metadata=metadata,
)
```

---

## Design Notes

* Triplets are computed independently per image
* KD-tree acceleration is used for spatial queries
* Default behavior avoids storing all triplets in memory
* Per-image outputs can be parallelized downstream
* Suitable for use from Python, R via reticulate, or shell pipelines

---

## License

MIT License

---

**Disclaimer**

This software was developed for internal research use and is provided “as is.”
No guarantees are made regarding suitability for any specific purpose.
Users are responsible for validating the software’s assumptions, correctness,
and performance on their own data before applying it to analyses or publications.

```

The main changes are:
- replaced the old single-definition paragraph with a two-mode definition
- added `--distance-mode` to CLI usage
- updated the summary example to include `Distance mode`
- clarified that caliper columns are only used in `effective` mode
- kept the Python import as `triplet_finder`
- cleaned up the disclaimer wording and CSV capitalization
```
