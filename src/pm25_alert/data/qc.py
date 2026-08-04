from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from pm25_alert.data.loading import infer_purpleair_pm25_columns


def _numeric_source(frame: pd.DataFrame, preferred: str, fallback: str | None) -> tuple[pd.Series, pd.Series]:
    column = preferred if preferred in frame.columns else fallback
    if not column or column not in frame.columns:
        missing = pd.Series(np.nan, index=frame.index, dtype="float64")
        return missing, pd.Series(False, index=frame.index, dtype="bool")
    raw = frame[column]
    numeric = pd.to_numeric(raw, errors="coerce")
    non_numeric = raw.notna() & raw.astype(str).str.strip().ne("") & numeric.isna()
    return numeric, non_numeric


def _reason_text(reasons: Iterable[str]) -> str:
    return ";".join(dict.fromkeys(reason for reason in reasons if reason)) or "ok"


def qc_purpleair_samples(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Apply explainable sample-level QC without mutating raw A/B values."""
    out = df.copy()
    policy = config.get("purpleair_qc_policy", {})
    value_min = float(policy.get("valid_pm25_min", 0.0))
    value_max = float(policy.get("valid_pm25_max", 1000.0))
    abs_min = float(policy.get("severe_abs_diff_min", 10.0))
    rel_min = float(policy.get("severe_rel_diff_min", 0.35))
    full_score = float(policy.get("full_channel_qc_score", 1.0))
    single_score = float(policy.get("single_channel_qc_score", 0.6))

    mapping = infer_purpleair_pm25_columns(out)
    fallback_a = mapping.get("a")
    fallback_b = mapping.get("b")
    fallback_aggregate = mapping.get("best")
    if fallback_aggregate in {
        fallback_a,
        fallback_b,
        "pa_pm25_a_raw",
        "pa_pm25_b_raw",
    }:
        fallback_aggregate = None
    a, a_non_numeric = _numeric_source(out, "pa_pm25_a_raw", fallback_a)
    b, b_non_numeric = _numeric_source(out, "pa_pm25_b_raw", fallback_b)
    aggregate, aggregate_non_numeric = _numeric_source(
        out,
        "pa_pm25_raw",
        fallback_aggregate,
    )

    out["pa_pm25_a"] = a
    out["pa_pm25_b"] = b
    out["pa_pm25_aggregate"] = aggregate

    has_a = a.notna()
    has_b = b.notna()
    has_aggregate = aggregate.notna()
    valid_a = has_a & a.between(value_min, value_max, inclusive="both")
    valid_b = has_b & b.between(value_min, value_max, inclusive="both")
    valid_aggregate = has_aggregate & aggregate.between(value_min, value_max, inclusive="both")

    out["pa_abs_diff_ab"] = (a - b).abs()
    out["pa_mean_ab"] = pd.concat([a, b], axis=1).mean(axis=1)
    out["pa_rel_diff_ab"] = np.where(
        valid_a & valid_b & (out["pa_mean_ab"] > 0),
        out["pa_abs_diff_ab"] / out["pa_mean_ab"],
        np.nan,
    )
    out["channel_disagree"] = (
        valid_a
        & valid_b
        & (out["pa_abs_diff_ab"] >= abs_min)
        & (out["pa_rel_diff_ab"] >= rel_min)
    )

    selected = aggregate.where(valid_aggregate)
    selected = selected.combine_first(out["pa_mean_ab"].where(valid_a & valid_b))
    selected = selected.combine_first(a.where(valid_a))
    selected = selected.combine_first(b.where(valid_b))
    out["pa_pm25_qc"] = selected

    timestamp = (
        pd.to_datetime(out["time"], errors="coerce", utc=True)
        if "time" in out.columns
        else pd.Series(pd.NaT, index=out.index, dtype="datetime64[ns, UTC]")
    )
    timestamp_invalid = timestamp.isna()
    range_invalid = (
        (has_a & ~a.between(value_min, value_max, inclusive="both"))
        | (has_b & ~b.between(value_min, value_max, inclusive="both"))
        | (has_aggregate & ~aggregate.between(value_min, value_max, inclusive="both"))
    )
    non_numeric = a_non_numeric | b_non_numeric | aggregate_non_numeric
    no_usable_value = selected.isna()
    # A bad auxiliary channel must not erase a usable aggregate or companion
    # channel. Keep such a sample for display/fallback, but mark it non-strict so
    # it cannot update the hardware-aligned bias.
    hard_invalid = timestamp_invalid | no_usable_value
    degraded_source = range_invalid | non_numeric
    single_channel = ~valid_aggregate & (valid_a ^ valid_b)

    flagged = pd.Series(False, index=out.index, dtype="bool")
    for column in ("channel_flags", "channel_flags_auto", "channel_flags_manual"):
        if column not in out.columns:
            continue
        raw_flags = out[column]
        numeric_flags = pd.to_numeric(raw_flags, errors="coerce").fillna(0)
        text_flags = raw_flags.fillna("").astype(str).str.strip().str.lower()
        flagged |= numeric_flags.ne(0) | ~text_flags.isin({"", "0", "none", "nan", "false"})

    score = pd.Series(full_score, index=out.index, dtype="float64")
    score.loc[single_channel] = single_score
    score.loc[out["channel_disagree"]] = np.minimum(score.loc[out["channel_disagree"]], 0.25)
    score.loc[degraded_source] *= 0.5
    score.loc[flagged] *= 0.5
    if "confidence" in out.columns:
        confidence = pd.to_numeric(out["confidence"], errors="coerce").clip(0.0, 1.0)
        score *= confidence.fillna(1.0)
    score.loc[hard_invalid] = 0.0

    out["pa_timestamp_invalid_flag"] = timestamp_invalid
    out["pa_non_numeric_flag"] = non_numeric
    out["pa_range_invalid_flag"] = range_invalid
    out["pa_missing_flag"] = no_usable_value
    out["pa_negative_flag"] = (
        (has_a & (a < value_min))
        | (has_b & (b < value_min))
        | (has_aggregate & (aggregate < value_min))
    )
    out["pa_extreme_flag"] = (
        (has_a & (a > value_max))
        | (has_b & (b > value_max))
        | (has_aggregate & (aggregate > value_max))
    )
    out["pa_single_channel_flag"] = single_channel
    out["pa_api_channel_flag"] = flagged
    out["pa_hard_invalid_flag"] = hard_invalid
    out["pa_qc_bad_flag"] = (
        hard_invalid | degraded_source | out["channel_disagree"] | flagged
    )
    out["pa_sample_good"] = ~out["pa_qc_bad_flag"]
    out["qc_score"] = score.clip(0.0, 1.0)

    reason_codes: list[str] = []
    for idx in out.index:
        reasons = []
        if bool(timestamp_invalid.loc[idx]):
            reasons.append("invalid_timestamp")
        if bool(non_numeric.loc[idx]):
            reasons.append("non_numeric")
        if bool(range_invalid.loc[idx]):
            reasons.append("out_of_range")
        if bool(no_usable_value.loc[idx]):
            reasons.append("no_usable_value")
        if bool(out.at[idx, "channel_disagree"]):
            reasons.append("severe_ab_disagreement")
        if bool(single_channel.loc[idx]):
            reasons.append("single_channel_fallback")
        if bool(flagged.loc[idx]):
            reasons.append("api_channel_flag")
        reason_codes.append(_reason_text(reasons))
    out["qc_reason_codes"] = reason_codes
    return out


def aggregate_purpleair_hourly(
    samples: pd.DataFrame,
    config: dict,
    *,
    source_type: str = "purpleair_10min",
) -> pd.DataFrame:
    """Aggregate sample QC into one row per UTC hour using a single robust policy."""
    policy = config.get("purpleair_qc_policy", {})
    min_good = int(policy.get("min_good_samples_per_hour", 4))
    min_coverage = int(policy.get("min_coverage_minutes_per_hour", 30))
    statistic = str(policy.get("hourly_statistic", "median"))
    if samples.empty:
        return pd.DataFrame()

    qc = samples if "pa_sample_good" in samples.columns else qc_purpleair_samples(samples, config)
    qc = qc.copy()
    qc["time"] = pd.to_datetime(qc["time"], errors="coerce", utc=True)
    qc = qc.dropna(subset=["time"]).sort_values("time")
    qc["hour_utc"] = qc["time"].dt.floor("h")

    rows: list[dict[str, object]] = []
    for hour, group in qc.groupby("hour_utc", sort=True):
        valid = ~group["pa_hard_invalid_flag"].fillna(True)
        good = group["pa_sample_good"].fillna(False)
        display = valid & ~group["channel_disagree"].fillna(False)
        good_values = group.loc[good, "pa_pm25_qc"].dropna()
        display_values = group.loc[display, "pa_pm25_qc"].dropna()
        good_times = group.loc[good, "time"]
        coverage = (
            float((good_times.max() - good_times.min()).total_seconds() / 60.0)
            if len(good_times) >= 2
            else 0.0
        )
        qc_ok = len(good_values) >= min_good and coverage >= min_coverage

        values = good_values if qc_ok else display_values
        if values.empty:
            hourly_value = np.nan
        elif statistic == "mean":
            hourly_value = float(values.mean())
        else:
            hourly_value = float(values.median())

        reasons = []
        if len(good_values) < min_good:
            reasons.append("insufficient_good_samples")
        if coverage < min_coverage:
            reasons.append("insufficient_coverage")
        if pd.isna(hourly_value):
            reasons.append("no_hourly_value")

        completeness = min(len(good_values) / max(min_good, 1), 1.0)
        sample_score = float(group["qc_score"].fillna(0.0).mean())
        hourly_score = min(max(sample_score * completeness, 0.0), 1.0)
        rows.append(
            {
                "time": hour,
                "pa_pm25_hourly": hourly_value,
                "pa_pm25_hourly_strict": hourly_value if qc_ok else np.nan,
                "pa_pm25_hourly_loose": hourly_value,
                "pa_pm25_hourly_source": (
                    f"{source_type}_strict" if qc_ok else f"{source_type}_non_strict"
                ),
                "source_type": source_type,
                "qc_score": hourly_score,
                "qc_ok": int(qc_ok),
                "pa_total_samples_per_hour": int(len(group)),
                "pa_valid_samples_per_hour": int(valid.sum()),
                "pa_good_samples_per_hour": int(good.sum()),
                "pa_single_channel_count": int(group["pa_single_channel_flag"].fillna(False).sum()),
                "pa_severe_disagree_count": int(group["channel_disagree"].fillna(False).sum()),
                "pa_bad_samples_per_hour": int((~good).sum()),
                "pa_bad_fraction_per_hour": float((~good).mean()),
                "pa_coverage_minutes": coverage,
                "channel_disagree_count": int(group["channel_disagree"].fillna(False).sum()),
                "qc_reason_codes": _reason_text(reasons),
            }
        )
    return pd.DataFrame(rows).sort_values("time").reset_index(drop=True)


def qc_purpleair(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Backward-compatible name for the sample-level policy."""
    return qc_purpleair_samples(df, config)


__all__ = [
    "aggregate_purpleair_hourly",
    "qc_purpleair",
    "qc_purpleair_samples",
]
