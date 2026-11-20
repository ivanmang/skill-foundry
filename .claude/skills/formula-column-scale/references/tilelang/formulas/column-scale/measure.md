# column-scale — measured grid

VF is `VF` or `VF_SIMT` completion minus start, both ticks included, veccore0 (`core == 0`, `sub == 1`). el/cyc is N/VF. Bold is the lowest VF. 

## Keep, threads = 128

| Rows | N | Method | LDK | MRF | VF | el/cyc |
|---:|---:|---|---:|---|---:|---:|
| 32 | 4096 | unroll | 0 | 20.5KB / 16% | 1053 | 3.89 |
| 64 | 8192 | unroll | 0 | 37.0KB / 29% | 2153 | 3.80 |
| 128 | 16384 | unroll | 36 | 63.5KB / 50% | 4350 | 3.77 |
| 256 | 32768 | GM | 832 | 63.5KB / 50% | 144635 | 0.23 |

## Thread sweep

Same N, so rows × threads stays fixed. `REDUX` and `BAR` are 0 on every row. `LDK` is 0 except 36 at 128 threads and 128 rows. Bold is the lowest VF inside that N.

| N | Threads | Rows | VF | el/cyc | IPC |
|---:|---:|---:|---:|---:|---:|
| 4096 | 128 | 32 | 1053 | 3.89 | 0.76 |
| 4096 | 256 | 16 | **479** | 8.55 | 1.72 |
| 4096 | 512 | 8 | 591 | 6.93 | 1.49 |
| 4096 | 1024 | 4 | 626 | 6.54 | 1.58 |
| 8192 | 128 | 64 | 2153 | 3.80 | 0.73 |
| 8192 | 256 | 32 | 1426 | 5.74 | 1.12 |
| 8192 | 512 | 16 | **910** | 9.00 | 1.81 |
| 8192 | 1024 | 8 | 980 | 8.36 | 1.80 |
| 16384 | 128 | 128 | 4350 | 3.77 | 0.73 |
| 16384 | 256 | 64 | 2352 | 6.97 | 1.33 |
| 16384 | 512 | 32 | **1665** | 9.84 | 1.91 |
| 16384 | 1024 | 16 | 1690 | 9.69 | 1.95 |

The fence launch is the 1024-thread, 16-row row (VF 1690). The best SIMT row is 512 threads, 32 rows (VF 1665). Quote the matching launch.

## Stage flush

N=16384, 1024 threads, 16 rows. An empty compiler fence is deleted in this body. Fused is VF 1690. Split is a different binary, VF 1725. Flushing the 16 loads is VF 7694. Flushing the 16 products is VF 6403. Flushing the max is VF 1991. Flushing the inverse is VF 1971.
