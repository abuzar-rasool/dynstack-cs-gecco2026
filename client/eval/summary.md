# Evaluation results

Last updated: 2026-08-22 14:59 UTC

## Average rank

| Strategy | Train | Held-out |
|---|---:|---:|
| `cmaes_champion` | 2.00 | 1.33 |
| `nearest_crane` | 8.00 | 8.00 |
| `pham_rule_based` | 6.33 | 7.00 |
| `sca_gphh_stage_a` | 6.33 | 6.00 |
| `sca_gphh_stage_b` | 4.50 | 5.00 |
| `sca_gphh_stage_c` | 4.08 | 4.00 |
| `sca_gphh_stage_d` | 2.83 | 2.33 |
| `sca_gphh_stage_e` | 1.92 | 2.33 |

## Per strategy

### `cmaes_champion`

Train scenarios

| Scenario | Errors | Blocks | Parking (s) | Rank |
|---|---:|---:|---:|---:|
| `busy` | 0 | 215.1 +/- 11.62 | 3394.9 | 1 |
| `busy_uniform_interleaved` | 0 | 288.4 +/- 3.03 | 3599.0 | 6 |
| `default` | 0 | 180.5 +/- 7.79 | 2279.1 | 2 |
| `default_uniform_interleaved` | 0 | 184.5 +/- 9.56 | 2727.3 | 1 |
| `empty_buffer` | 0 | 191.8 +/- 11.84 | 1645.1 | 1 |
| `high_buffer` | 0 | 171.7 +/- 11.62 | 2981.2 | 1 |
| `high_buffer_uniform_interleaved` | 0 | 170.7 +/- 8.39 | 3183.6 | 2 |
| `large_vehicle` | 0 | 220.1 +/- 9.5 | 3380.2 | 1 |
| `quiet` | 0 | 138.5 +/- 9.13 | 1217.0 | 2 |
| `quiet_uniform_interleaved` | 0 | 133.2 +/- 10.56 | 1215.6 | 2 |
| `saturation` | 0 | 256.5 +/- 10.31 | 3432.8 | 3 |
| `shallow_stacks` | 0 | 172.5 +/- 11.94 | 2589.1 | 2 |

Held-out scenarios

| Scenario | Errors | Blocks | Parking (s) | Rank |
|---|---:|---:|---:|---:|
| `comp_scenario_1` | 0 | 173.8 +/- 15.92 | 1996.8 | 1 |
| `comp_scenario_2` | 0 | 180.9 +/- 7.19 | 2433.2 | 2 |
| `comp_scenario_3` | 0 | 171.2 +/- 10.44 | 1704.5 | 1 |

### `nearest_crane`

Train scenarios

| Scenario | Errors | Blocks | Parking (s) | Rank |
|---|---:|---:|---:|---:|
| `busy` | 0 | 95.6 +/- 8.34 | 1543.7 | 8 |
| `busy_uniform_interleaved` | 0 | 98.1 +/- 8.14 | 1536.2 | 8 |
| `default` | 0 | 95.3 +/- 7.59 | 1457.6 | 8 |
| `default_uniform_interleaved` | 0 | 95.8 +/- 6.56 | 1470.2 | 8 |
| `empty_buffer` | 0 | 117.1 +/- 3.73 | 1215.4 | 8 |
| `high_buffer` | 0 | 85.8 +/- 5.05 | 1726.0 | 8 |
| `high_buffer_uniform_interleaved` | 0 | 84 +/- 5.93 | 1721.2 | 8 |
| `large_vehicle` | 0 | 97.3 +/- 4.3 | 2221.5 | 8 |
| `quiet` | 0 | 103.1 +/- 6.61 | 1204.1 | 8 |
| `quiet_uniform_interleaved` | 0 | 97.5 +/- 8.09 | 1131.1 | 8 |
| `saturation` | 0 | 97 +/- 7.23 | 1507.1 | 8 |
| `shallow_stacks` | 0 | 108.8 +/- 5.61 | 1199.1 | 8 |

Held-out scenarios

| Scenario | Errors | Blocks | Parking (s) | Rank |
|---|---:|---:|---:|---:|
| `comp_scenario_1` | 0 | 96.9 +/- 4.84 | 1478.3 | 8 |
| `comp_scenario_2` | 0 | 101.4 +/- 4.17 | 1443.3 | 8 |
| `comp_scenario_3` | 0 | 96.4 +/- 4.5 | 1453.0 | 8 |

### `pham_rule_based`

Train scenarios

| Scenario | Errors | Blocks | Parking (s) | Rank |
|---|---:|---:|---:|---:|
| `busy` | 0 | 179.4 +/- 10.65 | 2698.0 | 6 |
| `busy_uniform_interleaved` | 0 | 299.4 +/- 8.57 | 3599.0 | 2 |
| `default` | 0 | 140.5 +/- 21.59 | 1781.6 | 7 |
| `default_uniform_interleaved` | 0 | 141.2 +/- 10.41 | 2474.1 | 7 |
| `empty_buffer` | 0 | 150.5 +/- 8.24 | 2370.1 | 7 |
| `high_buffer` | 0 | 124.1 +/- 31.47 | 2723.4 | 7 |
| `high_buffer_uniform_interleaved` | 0 | 136 +/- 7.63 | 2566.6 | 7 |
| `large_vehicle` | 0 | 177.4 +/- 35.04 | 2960.2 | 6 |
| `quiet` | 0 | 121.9 +/- 5.4 | 1377.3 | 7 |
| `quiet_uniform_interleaved` | 0 | 121.7 +/- 7.09 | 1102.0 | 7 |
| `saturation` | 0 | 242.1 +/- 5.88 | 3396.7 | 6 |
| `shallow_stacks` | 0 | 132.6 +/- 32.01 | 1574.4 | 7 |

Held-out scenarios

| Scenario | Errors | Blocks | Parking (s) | Rank |
|---|---:|---:|---:|---:|
| `comp_scenario_1` | 0 | 136.9 +/- 27.18 | 1628.2 | 7 |
| `comp_scenario_2` | 0 | 146.1 +/- 7.99 | 2343.0 | 7 |
| `comp_scenario_3` | 0 | 126.7 +/- 32.28 | 2311.6 | 7 |

### `sca_gphh_stage_a`

Train scenarios

| Scenario | Errors | Blocks | Parking (s) | Rank |
|---|---:|---:|---:|---:|
| `busy` | 0 | 164.1 +/- 6.37 | 3488.0 | 7 |
| `busy_uniform_interleaved` | 0 | 177.4 +/- 7.2 | 3586.1 | 7 |
| `default` | 0 | 144.4 +/- 5.83 | 2391.8 | 6 |
| `default_uniform_interleaved` | 0 | 147.9 +/- 5.57 | 2215.0 | 6 |
| `empty_buffer` | 0 | 163.6 +/- 6.22 | 2677.7 | 6 |
| `high_buffer` | 0 | 138 +/- 7.41 | 2304.7 | 6 |
| `high_buffer_uniform_interleaved` | 0 | 139.7 +/- 7.76 | 2312.8 | 6 |
| `large_vehicle` | 0 | 169.2 +/- 7.13 | 3537.0 | 7 |
| `quiet` | 0 | 134.2 +/- 7.74 | 1475.7 | 6 |
| `quiet_uniform_interleaved` | 0 | 128.8 +/- 6.6 | 1936.0 | 6 |
| `saturation` | 0 | 169.4 +/- 4.35 | 3483.9 | 7 |
| `shallow_stacks` | 0 | 148.2 +/- 7.66 | 2344.9 | 6 |

Held-out scenarios

| Scenario | Errors | Blocks | Parking (s) | Rank |
|---|---:|---:|---:|---:|
| `comp_scenario_1` | 0 | 146.2 +/- 6.7 | 2193.1 | 6 |
| `comp_scenario_2` | 0 | 154 +/- 4.88 | 2126.1 | 6 |
| `comp_scenario_3` | 0 | 142.7 +/- 5.52 | 1994.8 | 6 |

### `sca_gphh_stage_b`

Train scenarios

| Scenario | Errors | Blocks | Parking (s) | Rank |
|---|---:|---:|---:|---:|
| `busy` | 0 | 190.3 +/- 8.37 | 2672.7 | 5 |
| `busy_uniform_interleaved` | 0 | 305.6 +/- 5.58 | 3599.0 | 1 |
| `default` | 0 | 161.9 +/- 5.04 | 1789.6 | 5 |
| `default_uniform_interleaved` | 0 | 160.5 +/- 6.2 | 1937.3 | 5 |
| `empty_buffer` | 0 | 167.9 +/- 6.72 | 1829.6 | 5 |
| `high_buffer` | 0 | 150.9 +/- 7.42 | 1732.8 | 5 |
| `high_buffer_uniform_interleaved` | 0 | 148.9 +/- 7.96 | 2204.3 | 4 |
| `large_vehicle` | 0 | 200.9 +/- 5.93 | 3053.2 | 5 |
| `quiet` | 0 | 136.1 +/- 7.99 | 1423.3 | 5 |
| `quiet_uniform_interleaved` | 0 | 130.5 +/- 9.36 | 1087.9 | 5 |
| `saturation` | 0 | 244.8 +/- 6.18 | 3240.0 | 5 |
| `shallow_stacks` | 0 | 159.1 +/- 8.14 | 2260.5 | 4 |

Held-out scenarios

| Scenario | Errors | Blocks | Parking (s) | Rank |
|---|---:|---:|---:|---:|
| `comp_scenario_1` | 0 | 158.4 +/- 9.02 | 1981.6 | 5 |
| `comp_scenario_2` | 0 | 160.8 +/- 6.78 | 1899.9 | 5 |
| `comp_scenario_3` | 0 | 153.7 +/- 8.46 | 1816.0 | 5 |

### `sca_gphh_stage_c`

Train scenarios

| Scenario | Errors | Blocks | Parking (s) | Rank |
|---|---:|---:|---:|---:|
| `busy` | 0 | 193.6 +/- 8.26 | 2406.4 | 4 |
| `busy_uniform_interleaved` | 0 | 297 +/- 5.5 | 3599.0 | 3 |
| `default` | 0 | 163.2 +/- 5.49 | 1680.9 | 4 |
| `default_uniform_interleaved` | 0 | 161.4 +/- 8.02 | 2027.9 | 4 |
| `empty_buffer` | 0 | 171.6 +/- 8.36 | 1714.8 | 4 |
| `high_buffer` | 0 | 152.5 +/- 6.72 | 1959.4 | 4 |
| `high_buffer_uniform_interleaved` | 0 | 147 +/- 16.86 | 1710.9 | 5 |
| `large_vehicle` | 0 | 203.2 +/- 7.55 | 2782.8 | 4 |
| `quiet` | 0 | 137.2 +/- 8.74 | 1039.9 | 4 |
| `quiet_uniform_interleaved` | 0 | 130.6 +/- 8.4 | 1111.8 | 4 |
| `saturation` | 0 | 247.4 +/- 8.02 | 3283.5 | 4 |
| `shallow_stacks` | 0 | 148.4 +/- 36.86 | 2657.1 | 5 |

Held-out scenarios

| Scenario | Errors | Blocks | Parking (s) | Rank |
|---|---:|---:|---:|---:|
| `comp_scenario_1` | 0 | 160 +/- 10.8 | 1688.3 | 4 |
| `comp_scenario_2` | 0 | 165.4 +/- 5.95 | 1925.1 | 4 |
| `comp_scenario_3` | 0 | 155.5 +/- 7.29 | 1574.8 | 4 |

### `sca_gphh_stage_d`

Train scenarios

| Scenario | Errors | Blocks | Parking (s) | Rank |
|---|---:|---:|---:|---:|
| `busy` | 0 | 208.6 +/- 11.23 | 3005.4 | 3 |
| `busy_uniform_interleaved` | 0 | 293.5 +/- 5.62 | 3599.0 | 4 |
| `default` | 0 | 177.8 +/- 10.17 | 2392.0 | 3 |
| `default_uniform_interleaved` | 0 | 182 +/- 8.22 | 2617.5 | 3 |
| `empty_buffer` | 0 | 177.4 +/- 12.18 | 2561.8 | 3 |
| `high_buffer` | 0 | 165.3 +/- 9.14 | 2874.2 | 3 |
| `high_buffer_uniform_interleaved` | 0 | 170.6 +/- 11.71 | 2804.3 | 3 |
| `large_vehicle` | 0 | 215 +/- 12.21 | 3140.4 | 3 |
| `quiet` | 0 | 138.7 +/- 9.38 | 980.3 | 1 |
| `quiet_uniform_interleaved` | 0 | 132.4 +/- 10.64 | 1352.1 | 3 |
| `saturation` | 0 | 256.9 +/- 5.99 | 3491.7 | 2 |
| `shallow_stacks` | 0 | 170.1 +/- 11.36 | 2986.6 | 3 |

Held-out scenarios

| Scenario | Errors | Blocks | Parking (s) | Rank |
|---|---:|---:|---:|---:|
| `comp_scenario_1` | 0 | 171.6 +/- 15.81 | 1660.0 | 2 |
| `comp_scenario_2` | 0 | 178.2 +/- 6.76 | 1983.8 | 3 |
| `comp_scenario_3` | 0 | 169.7 +/- 8.49 | 1663.2 | 2 |

### `sca_gphh_stage_e`

Train scenarios

| Scenario | Errors | Blocks | Parking (s) | Rank |
|---|---:|---:|---:|---:|
| `busy` | 0 | 209.5 +/- 11.82 | 3160.5 | 2 |
| `busy_uniform_interleaved` | 0 | 289.3 +/- 3.92 | 3599.0 | 5 |
| `default` | 0 | 181.3 +/- 7.87 | 2097.5 | 1 |
| `default_uniform_interleaved` | 0 | 182.5 +/- 5.44 | 2621.7 | 2 |
| `empty_buffer` | 0 | 183.9 +/- 9.57 | 1785.8 | 2 |
| `high_buffer` | 0 | 171.6 +/- 9.41 | 2207.1 | 2 |
| `high_buffer_uniform_interleaved` | 0 | 171.2 +/- 8.26 | 2904.3 | 1 |
| `large_vehicle` | 0 | 216.7 +/- 12.53 | 3277.4 | 2 |
| `quiet` | 0 | 138.3 +/- 8.88 | 1256.6 | 3 |
| `quiet_uniform_interleaved` | 0 | 133.3 +/- 11.2 | 749.3 | 1 |
| `saturation` | 0 | 262 +/- 6.06 | 3454.1 | 1 |
| `shallow_stacks` | 0 | 173.5 +/- 11.21 | 2189.8 | 1 |

Held-out scenarios

| Scenario | Errors | Blocks | Parking (s) | Rank |
|---|---:|---:|---:|---:|
| `comp_scenario_1` | 0 | 171.1 +/- 14.19 | 1706.3 | 3 |
| `comp_scenario_2` | 0 | 181.4 +/- 7.34 | 2045.2 | 1 |
| `comp_scenario_3` | 0 | 169.3 +/- 12.88 | 1530.5 | 3 |
