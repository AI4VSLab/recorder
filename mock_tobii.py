from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib import request


def post_json(url: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mock Tobii stimulus presenter for local Flask testing."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:5500",
        help="Flask app base URL.",
    )
    parser.add_argument(
        "--stimuli-dir",
        default="mock_stimuli",
        help="Directory of sample stimulus files.",
    )
    args = parser.parse_args()

    stimuli_dir = Path(args.stimuli_dir).resolve()
    stimulus_files = sorted(stimuli_dir.glob("*.svg"))

    if not stimulus_files:
        raise SystemExit(f"No mock stimuli found in {stimuli_dir}")

    print(f"Loaded {len(stimulus_files)} mock stimuli from {stimuli_dir}")
    print("Press Enter to send the next stimulus to Flask. Ctrl+C exits.")

    for stimulus_file in stimulus_files:
        input(f"Next stimulus: {stimulus_file.stem} ")
        result = post_json(
            f"{args.base_url}/stimuli/show",
            {
                "slide_id": stimulus_file.stem,
                "image_path": str(stimulus_file),
                "metadata": {"mock": True},
            },
        )
        print(
            f"Registered {stimulus_file.stem}; "
            f"history now has {len(result['recent_images'])} image(s)."
        )

    print("All mock stimuli sent.")


if __name__ == "__main__":
    main()
