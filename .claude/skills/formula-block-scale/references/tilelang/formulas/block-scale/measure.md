# block-scale — measured grid

VF is `VF` or `VF_SIMT` completion minus start, both ticks included, veccore0 (`core == 0`, `sub == 1`). el/cyc is N/VF. Bold is the lower VF. 

## Flat reduce — loop versus cross

Threads = 128 (loop) versus threads = N (cross). `REDUX` stays 5 and `BAR` stays 16 on the loop as N grows.

| N | Cross VF | Loop VF | Cross REDUX | Loop REDUX | Cross BAR | Loop BAR |
|---:|---:|---:|---:|---:|---:|---:|
| 128 | 633 | **632** | 5 | 5 | 16 | 16 |
| 256 | 701 | **576** | 9 | 5 | 32 | 16 |
| 512 | 835 | **663** | 17 | 5 | 64 | 16 |
| 1024 | 988 | **535** | 64 | 5 | 128 | 16 |
| 2048 | 1549 | **503** | 128 | 5 | 256 | 16 |

Last-element probe, `X[N-1] = 4`, rest 0: cross at N=2048 returns eps; the loop returns 4.

## 2D keep, threads = 128

| Rows | N | Method | LDK | MRF | VF | el/cyc |
|---:|---:|---|---:|---|---:|---:|
| 32 | 4096 | unroll | 0 | 21.5KB / 17% | 1806 | 2.27 |
| 64 | 8192 | unroll | 0 | 47.5KB / 37% | 2474 | 3.31 |
| 128 | 16384 | unroll | 88 | 63.5KB / 50% | 4963 | 3.30 |
| 256 | 32768 | GM | 996 | 63.5KB / 50% | 113398 | 0.29 |

## 2D thread sweep

Same N, so rows × threads stays fixed. Bold is the lowest VF inside that N.

| N | Threads | Rows | VF | el/cyc | IPC | REDUX | BAR |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4096 | 128 | 32 | 1806 | 2.27 | 0.49 | 5 | 16 |
| 4096 | 256 | 16 | **856** | 4.79 | 1.16 | 9 | 32 |
| 4096 | 512 | 8 | 904 | 4.53 | 1.35 | 17 | 64 |
| 4096 | 1024 | 4 | 1190 | 3.44 | 1.40 | 64 | 128 |
| 16384 | 128 | 128 | 4963 | 3.30 | 0.68 | 5 | 16 |
| 16384 | 1024 | 16 | **2363** | 6.93 | 1.68 | 64 | 128 |

Issue shape, `W = threads / 32`, `R = N / threads`: `REDUX = W+1` up to 16 warps, `REDUX = 2W` at 32 warps, `BAR = 4×W`. Row issues fall as each thread owns fewer rows. Reduce issues grow with the warp count.

## Stage flush

N=16384, 1024 threads, 16 rows. An empty compiler fence is deleted in this body. Fused and split are one binary, VF 2360. Flushing the 16 loads is VF 8355. Flushing the 16 quotients is VF 7158. Flushing the block scale is VF 2368. The stock kernel is VF 2363 and is a different binary from the handwritten uncut kernel.
