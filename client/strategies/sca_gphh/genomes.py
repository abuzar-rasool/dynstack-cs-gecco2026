"""Evolved tree strings for each stage champion. Data only, no imports."""

STAGE_A_TREE4 = (
    "sub(nearest_crane_dist, max2(is_downstream, "
    "max2(max2(nearest_crane_dist, is_upstream), abs(is_downstream))))"
)
STAGE_A_TREE5 = "sub(mul(min2(range_headroom, range_headroom), dist_dropoff), range_headroom)"

STAGE_B_TREE2 = (
    "mul(add(add(min2(protected_div(blocks_requested_in_buf, "
    "blocks_requested_in_buf), buf_free), dist_source), dist_handover), "
    "add(add(dist_source, abs(add(blocks_requested_in_buf, "
    "abs(mul(blocks_requested_in_buf, dist_source))))), "
    "add(blocks_requested_in_buf, dist_source)))"
)

STAGE_C_TREE2 = (
    "mul(add(protected_div(blocks_requested_in_buf, blocks_requested_in_buf), "
    "add(blocks_requested_in_buf, dist_source)), add(add(abs(dist_source), "
    "abs(dist_source)), add(blocks_requested_in_buf, dist_source)))"
)
STAGE_C_TREE4 = (
    "sub(nearest_crane_dist, max2(max2(is_downstream, abs(nearest_crane_dist)), "
    "max2(max2(nearest_crane_dist, -1.2945770001938692), is_upstream)))"
)
STAGE_C_TREE5 = (
    "sub(mul(mul(max2(dist_pickup, dist_dropoff), range_headroom), dist_dropoff), "
    "range_headroom)"
)

STAGE_D_TREE2 = (
    'mul(add(add(abs(dist_source), abs(is_empty)), add(blocks_requested_in_buf, add(add(abs(blocks_requested_in_buf), abs(add(add(abs(dist_source), abs(is_empty)), add(blocks_requested_in_buf, add(add(abs(blocks_requested_in_buf), abs(add(abs(dist_source), abs(dist_source)))), add(blocks_requested_in_buf, dist_source)))))), add(blocks_requested_in_buf, dist_source)))), add(add(blocks_requested_in_buf, abs(dist_source)), add(dist_source, dist_source)))'
)
STAGE_D_TREE4 = (
    'sub(pd_dist, max2(abs(max2(nearest_crane_dist, max2(abs(max2(nearest_crane_dist, is_upstream)), nearest_crane_dist))), nearest_crane_dist))'
)
STAGE_D_TREE5 = (
    'sub(mul(mul(dist_dropoff, range_headroom), range_headroom), range_headroom)'
)

STAGE_E_TREE2 = (
    'mul(add(dist_source, blocks_requested_in_buf), '
    'add(add(blocks_requested_in_buf, abs(dist_source)), add(dist_source, dist_source)))'
)
STAGE_E_TREE4 = 'sub(pd_dist, is_upstream)'
STAGE_E_TREE5 = 'sub(mul(dist_dropoff, mul(dist_dropoff, range_headroom)), range_headroom)'
