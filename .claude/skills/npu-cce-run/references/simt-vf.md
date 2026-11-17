# A `__simt_vf__` body

A reference for the language. Not a formula. The measured dot-product spelling
is `skill:tilelanggym-dot-product`.

Lane `t` is `tid & 31`. The warp is `tid >> 5`. Lane `t` reads element `t`. The
warp reduction finishes the group. Lane 0 writes.

```text
__simt_vf__ body:
    lane = tid & 31
    wid  = tid >> 5
    value = lane's element
    reduced = asc_reduce_*(value)
    if lane == 0: store reduced
```

The host `__vector__` kernel copies the inputs into the buffer, waits until that
copy has finished, then calls this body with `asc_vf_call`. The waits are
`skill:npu-cce-run` (the sync the staged bodies depend on).

```text
refuse, lanes far apart:
    base = tid * stride
    value = buffer[base + k]
```

Compile with `skill:npu-cce-run`. For a measured full-kernel cell see the
`skill:tilelanggym-dot-product`.