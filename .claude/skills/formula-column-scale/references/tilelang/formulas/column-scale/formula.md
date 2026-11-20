# column-scale

One scale per column, then each element multiplied by its column's inverse.

## Math

eps is 1e-6. Storage is float32.

```text
scale[col] = max(eps, max over rows |X[row, col]|)
Out[row, col] = X[row, col] * (1 / scale[col])
```

## Signature

**Match** when all of these hold:

- one value is reduced per column, over the rows of that column
- the reduce is a max of absolute values, floored at eps
- each element of the column is then multiplied by that column's inverse
- no value crosses a column boundary; nothing is broadcast

**Reject** — these are different formulas:

- one value for the whole input, then every element divided by it → `block-scale`
- one value per group along a row, then each element multiplied by its group's inverse → `group-scale-broadcast`
- a sum, not a max → `dot-product`

## Correctness check

For each column, `max over rows |Out[row, col]|` equals `max over rows |X[row, col]| / max(eps, that max)`. A spelling that inserts a reducer across the columns computes the block scale and is a different formula, not a variant of this one.
