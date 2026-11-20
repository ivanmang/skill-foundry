# dot-product

One sum per output row, over the K axis.

## Math

`A` is `(N, K)`. `x` has length `K`. `Out` has length `N`.

```text
Out[n] = sum_k A[n, k] * x[k]
```

## Signature

**Match** when all of these hold:

- one value per output row, produced by a sum over the inner axis
- the combine is a multiply-accumulate, not a max
- there is no scale, no broadcast of a reduced value, and no eps floor

**Reject** — these are different formulas:

- a max of absolute values into one value, then divide → `block-scale`
- one value per column → `column-scale`
- one value per group, then broadcast → `group-scale-broadcast`

## Correctness check

Each output equals the dot product of its row of `A` with `x`. The order of accumulation within a row does not change the math.
