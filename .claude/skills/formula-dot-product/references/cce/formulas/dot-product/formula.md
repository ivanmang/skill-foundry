# dot-product — CCE

The math is unchanged from the TileLang formula. CCE is a spelling of the same formula, not a new formula.

## Math

`A` is `(N, K)`. `x` has length `K`. `Out` has length `N`.

```text
Out[n] = sum_k A[n, k] * x[k]
```

## Signature

The same match and reject rules as the TileLang `dot-product`. One value per output row, produced by a multiply-accumulate over the inner axis, with no scale and no eps floor. A max into a scale, or one value per column or group, is a different formula.

## Correctness check

Each output equals the dot product of its row of `A` with `x`. The measured body passed with max abs error 9.537e-07 against the fp32 gold.
