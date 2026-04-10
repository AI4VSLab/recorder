# Maintain experiment status
# When new experiment starts, set the status to active and start new variables with inputs
# Start a new csv file with the experiment name and current time
# When the experiment progresses, update the current count, and update the csv file
# When experiment ends, set experiment to inactive

from __future__ import annotations

from pathlib import Path
from datetime import datetime

import pandas as pd

from tobii_stimuli import TobiiStimulusTracker


class Experiment:

    ACTIVE = False

    def __init__(
        self,
        tot_count: int = 20,
        stimuli_template: str = "/path/to/amd/stimuli/{slide_id}.png",
        history_size: int = 5,
    ) -> None:
        self.tot_count = tot_count
        self.cur_count = 0
        self.exp_name = "debug"
        self.exp_id = "debug"
        self.csv_path = "saves/" + self.exp_id + ".csv"
        self.stimuli_template = stimuli_template
        self.stimulus_ids: list[str] = []
        self.current_stimulus_index = -1
        self.stimulus_tracker = TobiiStimulusTracker(
            stimulus_template=stimuli_template,
            history_size=history_size,
        )
        self.create_df()

    def create_df(self):
        self.df = pd.DataFrame(columns=["text", "score", "time"])
        if self.ACTIVE:
            self.df.to_csv(self.csv_path, index=True)

    def update_empty(self, text="Empty", score="Empty"):
        # First append empty as soon as any update is to be made
        self.cur_count += 1
        new_row = {"text": text, "score": score, "time": self.get_time()}
        self.df = pd.concat([self.df, pd.DataFrame([new_row])], ignore_index=True)
        if self.ACTIVE:
            self.df.to_csv(self.csv_path, index=True)

    def update_last_row(self, text="Empty", score="Empty"):
        # Then replace the last row if successfully submitted the form
        self.df.iloc[-1, self.df.columns.get_loc("text")] = text
        self.df.iloc[-1, self.df.columns.get_loc("score")] = score
        self.df.iloc[-1, self.df.columns.get_loc("time")] = self.get_time()

        if self.ACTIVE:
            self.df.to_csv(self.csv_path, index=True)

    def get_status(self):
        if self.ACTIVE:
            return self.cur_count, self.tot_count, self.exp_id, self.get_df()
        return "exp inactive", "exp inactive", "exp inactive", self.get_df()

    def get_df(self):
        if self.ACTIVE:
            return self.df.to_dict(orient="records")

        inactive_df = pd.DataFrame(
            {"text": "exp inactive", "score": "exp inactive", "time": "exp inactive"},
            index=[0],
        )
        return inactive_df.to_dict(orient="records")

    def get_time(self):
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def start(self, exp_name="demo", total=20, stimuli_template: str | None = None):
        self.ACTIVE = True
        self.cur_count = 0
        self.tot_count = int(total)
        self.exp_name = exp_name
        self.exp_id = self.exp_name + "_" + self.get_time()
        self.csv_path = "saves/" + self.exp_id + ".csv"
        if stimuli_template:
            self.set_stimuli_template(stimuli_template)
        self.create_df()
        self.reset_stimulus_history()

    def end(self):
        self.ACTIVE = False
        self.cur_count = 0
        self.tot_count = 20
        self.exp_name = "debug"
        self.exp_id = "debug"
        self.csv_path = "saves/" + self.exp_id + ".csv"
        self.df = pd.DataFrame(columns=["text", "score", "time"])
        self.reset_stimulus_history()

    def set_stimuli_template(self, stimuli_template: str) -> None:
        self.stimuli_template = stimuli_template
        self.stimulus_tracker.stimulus_template = stimuli_template

    def set_stimulus_sequence(self, stimulus_ids: list[str]) -> None:
        self.stimulus_ids = [str(slide_id) for slide_id in stimulus_ids]
        self.current_stimulus_index = -1

    def register_stimulus(
        self,
        slide_id: str | None = None,
        image_path: str | None = None,
        metadata: dict | None = None,
        source: str = "flask",
    ) -> dict:
        if slide_id is None:
            if not self.stimulus_ids:
                raise ValueError("No stimulus_id provided and no stimulus sequence is configured.")
            next_index = self.current_stimulus_index + 1
            if next_index >= len(self.stimulus_ids):
                raise IndexError("Stimulus sequence is exhausted.")
            slide_id = self.stimulus_ids[next_index]
            self.current_stimulus_index = next_index
        else:
            slide_id = str(slide_id)
            if slide_id in self.stimulus_ids:
                self.current_stimulus_index = self.stimulus_ids.index(slide_id)
            else:
                self.stimulus_ids.append(slide_id)
                self.current_stimulus_index = len(self.stimulus_ids) - 1

        event = self.stimulus_tracker.record_presented_stimulus(
            slide_id=slide_id,
            image_path=image_path,
            metadata=metadata,
            source=source,
        )
        return event.to_dict()

    def register_stimulus_from_filepath(
        self,
        filepath: str,
        slide_id: str | None = None,
        metadata: dict | None = None,
        source: str = "flask",
    ) -> dict:
        path = Path(filepath)
        resolved_slide_id = slide_id or path.stem
        return self.register_stimulus(
            slide_id=resolved_slide_id,
            image_path=str(path),
            metadata=metadata,
            source=source,
        )

    def get_recent_stimuli(self) -> list[dict]:
        return self.stimulus_tracker.get_recent_events()

    def get_recent_stimulus_images(self) -> list[str]:
        return self.stimulus_tracker.get_recent_image_paths()

    def get_recent_stimuli_case(self) -> dict:
        latest_event = self.stimulus_tracker.get_latest_event()
        return {
            "id": latest_event["slide_id"] if latest_event else None,
            "images": self.get_recent_stimulus_images(),
        }

    def get_current_stimulus(self) -> dict | None:
        return self.stimulus_tracker.get_latest_event()

    def get_tobii_status(self) -> dict:
        return self.stimulus_tracker.get_sdk_status()

    def resolve_stimulus_image_path(self, slide_id: str) -> str:
        slide_id = str(slide_id)
        for event in reversed(self.get_recent_stimuli()):
            if event["slide_id"] == slide_id:
                return event["image_path"]
        return self.stimulus_tracker.resolve_image_path(slide_id)

    def reset_stimulus_history(self) -> None:
        self.stimulus_tracker.reset()
        self.current_stimulus_index = -1
