# group-scale-broadcast — measured grid

G is 32. Float32. VF is `VF_SIMT` completion minus start, both ticks included, veccore0 (`core == 0`, `sub == 1`). el/cyc is N/VF. Bold is the lower VF in the pair. 

## Load-ahead versus dual-drain

The 64×64 cell at 2048 threads is load-2, marked `*`.

| Shape | Threads | Dual-drain VF | Load-4 VF |
| --- | ---: | ---: | ---: |
| 64×64 | 128 | **941** | 1352 |
| 64×64 | 512 | 665 | **645** |
| 64×64 | 1024 | 691 | **635** |
| 64×64 | 2048 | 1055 | **1044** * |
| 64×128 | 256 | **1405** | 1555 |
| 64×128 | 512 | 1214 | **1208** |
| 64×128 | 1024 | 1239 | **1044** |
| 64×128 | 2048 | 1202 | **1111** |
| 128×128 | 512 | 2683 | **2140** |
| 128×128 | 1024 | 2624 | **2010** |
| 128×128 | 2048 | 3208 | **1887** |

Load-4 is shorter than dual-drain from 512 threads up. It is shorter at 128 threads on 64×64 and at 256 threads on 64×128 in the dual-drain rows. On 128×128 dual-drain spills (`LDK`/`STK` 48, 96, 192 at 512, 1024, 2048); load-4 does not spill on these cells. Load-4 is not shorter than keeplive on 64×64 or pack on 64×128.

## Depth, one launch

Same kernel, three depths, 64×128, 256 threads, float32, 8 warps. The only change is how many groups are loaded before the max. Warp 0, lane 0, on load-4 reads elements 0, 256, 512, 768. Lane 1 reads 1, 257, 513, 769.

| Schedule | Groups before the max | VF | el/cyc |
| --- | ---: | ---: | ---: |
| one at a time | 1 | 3721 | 2.20 |
| load-2 | 2 | 2134 | 3.84 |
| load-4 | 4 | 1555 | 5.27 |

## Load count

The number of `SIMT_LDS` issues stays equal to the number of groups. Doubling the threads does not halve that count, and it does not halve the window.

## Within-group width

On the one-thread-one-group stride, LDS.64 halves the issued `SIMT_LDS` count against LDS.32 and does not change VF. A wider load does not shorten that window.
