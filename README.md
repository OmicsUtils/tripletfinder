# triplet-finder

This tool identifies spatial triplets of cells based on an **effective interaction distance**. It was originally designed as a preprocessing step for identifying immune cell triads, but may be applicable to other spatial analysis tasks.

> **Definition of Effective Interaction Distance and Triplets**
>
> Pairwise distances between cells are computed as the centroid-to-centroid distance
> minus the sum of the two cells’ radii, where each radius is defined as the average of
> the minimum and maximum cell diameter columns.
>
> Two cells are considered capable of interaction if this **effective distance** is
> less than a user-defined interaction threshold, representing the assumed spatial
> range over which cells can communicate or influence one another.
>
> A **triplet** is defined as a fully connected set of three cells (a 3-clique) in which
> all three pairwise effective distances satisfy this interaction criterion within a
> single image or field of view.



The tool is designed to be:  
- memory-safe by default (streaming mode)  
- usable as both a Python library and a command-line tool  
- suitable for large microscopy / spatial biology datasets  

---

## Installation

### From source (recommended for development)

Clone the repository and install in editable mode:

```bash
pip install -e .
```

This will install:

* the Python package: `triplet_finder`
* the CLI command: `triplet-finder`

### Dependencies

Python ≥ 3.9 is required.

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
* writes one CSV per image (if `--output-dir` is provided)
* does **not** keep all triplets in memory (default behavior)

### Write a combined output CSV (opt-in)

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

⚠️ For large datasets, this may require substantial memory.

---

### Excluding cells by metadata (e.g. cell type)

```bash
triplet-finder \
  --input cells.csv \
  --exclude-col tentative_cell_type \
  --exclude-values Unknown \
  --output-dir per_image_triplets/
```

---

### Summary / dry-run mode

Prints a summary of the dataset and parameters without computing triplets:

```bash
triplet-finder \
  --input cells.csv \
  --exclude-col tentative_cell_type \
  --exclude-values Unknown \
  --summary
```

Example output:

```
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
Min cell diameter column: cell_min_caliper
Max cell diameter column: cell_max_caliper
Distance threshold: 15.0
```

---

### Metadata headers

By default, per-image csv file outputs include metadata headers (tool version, parameters, command, etc.).

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

---

### Example: streaming mode (recommended)

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
    threshold=15.0,
    output_dir="per_image_triplets",
    return_triplets=False,  # default
)
```

This writes per-image CSVs and returns `None`.

---

### Example: returning all triplets

```python
triplets = find_triplets_with_details(
    input_data=df,
    image_col="image_sliced",
    x_col="centroid_x_um",
    y_col="centroid_y_um",
    min_cell_diameter_column="cell_min_caliper",
    max_cell_diameter_column="cell_max_caliper",
    threshold=15.0,
    return_triplets=True,
)

print(triplets.head())
```

---

### Metadata in Python usage

```python
metadata = {
    "experiment": "Immune_Triads_Preprocessing",
    "threshold": 15.0,
    "notes": "Unknown cells excluded"
}

find_triplets_with_details(
    input_data=df,
    image_col="image_sliced",
    x_col="centroid_x_um",
    y_col="centroid_y_um",
    min_cell_diameter_column="cell_min_caliper",
    max_cell_diameter_column="cell_max_caliper",
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
* Per-image outputs can be safely parallelized downstream
* Suitable for use from Python, R (via reticulate), or shell pipelines

---

## License

MIT License

---

> **Disclaimer**
>
> This software was originally developed for the author’s personal research use.
> It is provided “as is,” without guarantees of suitability for any particular purpose.
> Users are responsible for verifying correctness, assumptions, and performance
> on their own data before using the tool in analyses, publications, or decision-making.
