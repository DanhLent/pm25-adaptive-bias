# APB3 Register Map

All registers are 32-bit aligned. Reserved bits read as zero. Signed x16 values
represent PM2.5 as `signed_integer / 16`.

| Address | Name | Access | Reset | Fields |
| --- | --- | --- | --- | --- |
| `0x00` | IP_ID | RO | `0x504D3235` | ASCII `PM25` |
| `0x04` | VERSION | RO | `0x00010000` | version 1.0.0 |
| `0x08` | CONTROL | RW/command | 0 | [0] PROCESS (reads 0), [1] SAMPLE_VALID, [2] QC_OK |
| `0x0C` | CAMS_PM25_X16 | RW | 0 | signed CAMS input |
| `0x10` | PA_PM25_X16 | RW | 0 | signed PurpleAir input |
| `0x14` | HOUR | RW | 0 | [4:0] hour metadata |
| `0x18` | STATUS | RO | 0 | [0] BUSY, [1] DONE, [2] RESULT_VALID, [3] ACCEPTED, [4] ALERT_STATE, [7:5] ALERT_LEVEL |
| `0x1C` | PM25_RESULT_X16 | RO | 0 | signed corrected/fused result |
| `0x20` | BIAS_STATE_X16 | RO | 0 | signed post-command bias state |
| `0x24` | CONFIG | RO | `0x00001003` | [7:0] ALPHA_SHIFT, [15:8] scale (=16) |

## Example transaction

```text
write 0x0C = CAMS x16
write 0x10 = PurpleAir x16
write 0x14 = hour
write 0x08 = PROCESS | SAMPLE_VALID | QC_OK
poll  0x18 until DONE=1
read  0x18, 0x1C, 0x20
```

SAMPLE_VALID=0 is legal when PROCESS=1: the command completes, RESULT_VALID is
zero, and adaptive state holds according to the native-core contract.
