# Expert optimization quick reference

The report emits a diagnosis only when the required measured metric and context are present.

## Pipeline bounds

- **Vector bound**: Vector is the dominant base pipeline and its activity is at least 50%.
- **MTE2 bound**: MTE2 is the dominant base pipeline. A bandwidth limit requires measured bytes, transfer time, and a documented peak bandwidth; activity alone is insufficient.
- **Cube bound**: Cube is the dominant base pipeline.
- **Scalar bound**: Scalar activity is greater than 30%. Values above 70% are shown as a high severity Scalar bound.
- **Pipeline bubbles**: at least two base units are in the 30%–50% range with no clear dominant unit.

## Balance and conflicts

- **Logical-block imbalance**: `(max(duration) - min(duration)) / max(duration) * 100`; greater than 10% is imbalanced and at least 30% is severe.
- **Conflicts**: total conflict ratio greater than 5%; bankgroup or bank conflict ratio greater than 3%.
- **L2 reuse**: total L2 hit rate below 50% is a review signal.
- **Frequency**: current frequency below 90% of rated frequency is a measurement stability warning.

## Evidence limits

DoubleBuffer effectiveness requires timestamped MTE2 and compute intervals. Overlap above 30% is effective, 10%–30% is partial, and below 5% is ineffective. Do not infer overlap from aggregate activity percentages or unrelated Warp events. Reference speedup figures are empirical examples and must not be presented as measured gains for the current capture.
