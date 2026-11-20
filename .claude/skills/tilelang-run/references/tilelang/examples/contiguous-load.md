# Contiguous load

A reference for a SIMT load. Not a formula.

Lane `t` reads element `t + step * threads`, so one warp reads 32 adjacent elements. The other address, `t * stride + step`, puts neighboring lanes far apart. Use the first when the data is contiguous. Use the second only when the user's math really is that stride.

```text
with T.SimtVF(threads):
    for step in steps:
        for t in Parallel(threads):
            acc[t] = acc[t] + buf[step * threads + t]
```

```text
refuse, lanes far apart:
    acc[t] = acc[t] + buf[t * stride + step]
```

Compile and launch with `tilelang/run/ascend.md`.
