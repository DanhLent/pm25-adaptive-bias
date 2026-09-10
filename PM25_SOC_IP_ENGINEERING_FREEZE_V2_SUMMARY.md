# PM2.5 SoC-IP Engineering Freeze V2 Summary

Freeze V2 is a narrow verification and packaging hotfix over Freeze V1. The
native PM2.5 core, UART implementation, APB RTL/register map, algorithm,
thresholds, ALPHA_SHIFT=3 deployment value, fixed-point behavior, packets,
pins, and constraints are unchanged.

The clean-archive sanitizer bug was confirmed: its POSIX regex sanitized its
own source and broke the extracted tool. The regex is now assembled from
non-matchable source fragments, and recursive archive tests prove that an
extracted tool still sanitizes POSIX home paths and regenerates a byte-identical
archive.

The APB independence concern was also confirmed. The reference core now
receives CAMS, PurpleAir, hour, SAMPLE_VALID, QC_OK, and its request pulse from
testbench-owned transaction intent. DUT snapshots and request/decode signals
are observed for wiring checks but never drive the reference. Results are
validated through actual APB STATUS/result/bias reads. APB coverage increased
from 56 transactions / 178 checks to 89 transactions / 325 checks. No APB RTL
bug was found or changed.

Verification improved from 94 to 96 passing Python tests. Native-core coverage
remains 18 vectors / 941 samples; ALPHA_SHIFT 2-6 remains 5 vectors / 450
samples; UART packet, wrapper, and full serial regressions pass. RTL cleanliness
passes. Gowin, Yosys, and Verilator are unavailable, so APB synthesis and
physical validation remain explicitly unverified.

The V2 clean archive excludes the retained historical
`docs/design_notes/legacy_context/` tree, previous/nested ZIPs, runtime data,
caches, logs, and generated products. Its 228 selected files plus manifest pass
ZIP integrity, all extracted Python/RTL regressions, POSIX sanitizer recursion,
and byte-for-byte archive regeneration.

Detailed evidence is in `reports/engineering_freeze_v2/`.
