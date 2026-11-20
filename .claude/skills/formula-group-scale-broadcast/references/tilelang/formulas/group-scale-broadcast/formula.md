# group-scale-broadcast

One scale per group of G adjacent columns, then each element multiplied by its group's inverse.

## Math

eps is 1e-6. Storage is float32. G is the group size.

```text
scale[row, g] = max(eps, max |X[row, g*G : (g+1)*G]|)
Out[row, j] = X[row, j] * (1 / scale[row, j // G])
```

Rows do not mix. Groups do not mix. The scale stays live, and the multiply uses a value already loaded.

## Signature

**Match** when all of these hold:

- one value is reduced per group of G adjacent columns within a row
- the reduce is a max of absolute values, floored at eps
- each element is then multiplied by the inverse of its own group's scale
- a group never spans two rows

**Reject** — these are different formulas:

- one value for the whole input → `block-scale`
- one value per column → `column-scale`
- a sum into one value per output → `dot-product`

## Correctness check

For each group, `max |Out|` over the group equals `max |X|` over the group divided by `max(eps, that max)`. A spelling that lets a group cross a row boundary, or that uses a scale from a different group, is a different formula, not a variant.
