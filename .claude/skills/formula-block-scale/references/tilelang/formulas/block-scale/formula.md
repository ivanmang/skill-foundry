# block-scale

One scale for the whole input, then every element divided by it.

## Math

eps is 1e-6. Storage is float32.

```text
scale = max(eps, max |X|)
Out = X / scale
```

On a 2D tile the same formula is written per column and then reduced across columns:

```text
m[col] = max over rows |X[row, col]|
scale = max(eps, max over columns m[col])
Out[row, col] = X[row, col] / scale
```

## Signature

**Match** when all of these hold:

- one value is reduced over the whole input
- the reduce is a max of absolute values, floored at eps
- every element is then divided by that one value

**Reject** — these are different formulas:

- one value per column, then multiply by its inverse → `column-scale`
- one value per group, then each element multiplied by its group's inverse → `group-scale-broadcast`
- a sum, not a max, into one value per output → `dot-product`

## Correctness check

`max |Out|` equals `max |X| / max(eps, max |X|)`. When the input is all zero, the scale is eps and every output is zero. A spelling that computes a per-column or per-group scale instead is a different formula, not a variant of this one.
