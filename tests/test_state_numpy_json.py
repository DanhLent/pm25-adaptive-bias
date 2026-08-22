import json

import numpy as np

from pm25_alert.state import write_json_atomic


def test_write_json_atomic_serializes_numpy_scalar(tmp_path):
    output = tmp_path / "state.json"

    write_json_atomic(
        output,
        {
            "native": 123,
            "numpy_int64": np.int64(456),
            "nested": [np.int64(7)],
        },
    )

    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["native"] == 123
    assert payload["numpy_int64"] == 456
    assert payload["nested"] == [7]
