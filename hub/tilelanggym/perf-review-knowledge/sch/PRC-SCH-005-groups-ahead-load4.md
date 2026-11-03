---
id: PRC-SCH-005
name: load-ahead (load-4, load-2) versus dual-drain
category: SCH
applies_to: SIMT Case-3 G32 · era=case3-quant-bcast · float32 · axis=1xG · shapes 64×64, 64×128, 128×128 · A5 camodel
status: ready
---

# PRC-SCH-005：load-ahead

## 知识点

Load-ahead is the schedule. Load-4 and load-2 are its passes: four groups before the max, or two when four does not divide. Neither name is a load width.

One warp owns one group of 32. Lane `t` reads element `t`, so the warp load is 32 adjacent columns. The address is

```text
addr = ((step * 4 + k) * warps + warp) * 32 + lane
```

`warps = threads / 32`. `groups = rows * (cols / 32)`. A pass loads `k = 0,1,2,3` into registers, then takes the warp max of each, then stores `held * (1 / max(m, eps))` at the same address. The load of group `k+1` does not use the max of group `k`.

The first of the four still waits on its load. The other three were issued during that wait. Dual-drain uses the same ownership and instead loads every group the warp owns before any max. Its live set is one value per group. Load-4's live set is four values, then those four are dropped.

### Corner cases

- `cols` must be a multiple of 32. A group then does not cross a row, and the address depends on `groups` and `warps`, not on the row/column split of the same element count.
- `threads` is a multiple of 32, at most 2048. `groups` must be a positive multiple of `warps`. This kernel does not launch extra idle threads.
- Four must divide `groups / warps`, or the launch is load-2, not load-4. On 64×64 at 2048 threads each warp has two groups.
- Issued group-loads stay equal to the number of groups. On 64×64 that count is 128 at 128, 512, 1024, and 2048 threads. Doubling the threads does not halve the window. 128→512 shortens it. 1024 matches 512. 2048 is the two-group cell and is longer.
- Compare at the same thread count and the same storage type. Float16 storage adds a conversion on the load and the store. Those rows are not this table.
- At 128 threads on 64×64, and at 256 threads on 64×128, dual-drain is the shorter window. From 512 threads up, load-4 is shorter, except the 64×64 launch at 2048 threads, which is load-2.
- One launch holds `X` and `Out` in one buffer. A shape that does not fit is tiled.

### 实测摘要

Float32. Pass. VF is the `VF_SIMT` window. Load-4 means four groups before the max, not a 4-wide load. The 64×64 cell at 2048 threads is load-2, marked *.

| Shape | Threads | Dual-drain VF | Load-4 VF |
|---|---:|---:|---:|
| 64×64 | 128 | 941 | 1352 |
| 64×64 | 512 | 665 | 645 |
| 64×64 | 1024 | 691 | 635 |
| 64×64 | 2048 | 1055 | 1044 * |
| 64×128 | 256 | 1405 | 1555 |
| 64×128 | 512 | 1214 | 1208 |
| 64×128 | 1024 | 1239 | 1044 |
| 64×128 | 2048 | 1202 | 1111 |
| 128×128 | 512 | 2683 | 2140 |
| 128×128 | 1024 | 2624 | 2010 |
| 128×128 | 2048 | 3208 | 1887 |

On 128×128 dual-drain spills: `LDK`/`STK` are 48, 96, and 192 at 512, 1024, and 2048 threads. Load-4 does not spill on these cells. Load-4 is shorter than dual-drain from 512 threads up, except the 64×64 cell at 2048 threads, which is load-2. Keeplive is shorter on 64×64. Pack is shorter on 64×128.

Load-ahead on one launch: 64×128, 256 threads, float32, 8 warps. The only change is how many groups are loaded before the max. Pass, max abs error 1.192e-07. Warp 0, lane 0, on load-4 reads 0, 256, 512, 768.

| Schedule | Groups before the max | VF | el/cyc |
|---|---:|---:|---:|
| one at a time | 1 | 3721 | 2.20 |
| load-2 | 2 | 2134 | 3.84 |
| load-4 | 4 | 1555 | 5.27 |

## 错误写法

```text
// 反例：一个 warp 拥有的每个 group 都先 load、再 abs，最后才 max。
// 活值是 E/T 个，不是 4 个。大 shape 上这会 spill。
load every group this warp owns
absolute value of each
then the max
```

```text
// 反例：groups/warps 不能被 4 整除，仍把这次 launch 叫 load-4。那是 load-2。
// 64×64、2048 threads 时每个 warp 只剩 2 个 group。
```

## 正确写法

```text
held[k] = X[((step * 4 + k) * warps + warp) * 32 + lane]   for k in 0..3
inv[k]  = 1 / max(warp_max(abs(held[k])), eps)
store held[k] * inv[k] at that same address
```

Source: `work/ST-Analysis/SV8/kernel.py`, `make_warp_f16_unroll(..., factor=4, dtype="float32")`.

## 识别方法

1. The address is `(group_index * warps + warp) * 32 + lane`, with `lane = tid % 32`.
2. Four loads are issued, then four warp maxes, then four stores. A dump of this schedule on 64×64 shows 128 `SIMT_LDS`, one per group, at every thread count.
3. A two-group pass is not this card. A within-group `float2` load is not this card either: that thread owns 32 columns, and the next thread is 32 columns away.

误报边界：do not rank a float16 row against this table. Do not treat the 2048-thread 64×64 cell as load-4. That cell is load-2. Do not expect the window to shrink in step with the thread count. Do not call a `G≠32` kernel this schedule. Lane `t` on element `t` still applies; a warp max that mixes two groups does not. Keeplive on 64×64 and pack on 64×128 are shorter than this SIMT schedule. The procedure for a similar kernel is in `tilelanggym-softlib-simt`, sections "When the kernel looks like SV8" and "load-ahead".

## 证据要求

A claim that cites this card must give:

- The shape, the thread count, and that storage is float32.
- Whether `groups / warps` is divisible by 4.
- VF for load-4 and, when the claim is "shorter than dual-drain", VF for dual-drain at that same thread count.

## 参考

- `/home/onasismelchiorjeyakumar/workspace/tilelang/work/ST-Analysis/SV8/ANALYSIS.md` Tables 2, 3, and 4
- `/home/onasismelchiorjeyakumar/workspace/tilelang/work/ST-Analysis/skill-testing/PRC-SIMT-004/summary.txt`
- `/home/onasismelchiorjeyakumar/workspace/tilelang/work/ST-Analysis/SV8/kernel.py`
- Skill: `tilelanggym-softlib-simt`, section "Groups ahead"
- Not this card: a within-group `float` versus `float2` pair. That comparison is not indexed here.
