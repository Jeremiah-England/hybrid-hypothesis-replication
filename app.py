import json
import multiprocessing as mp
import os
import random
import signal
from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import repeat
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename

from genome_comparison import compare_chunk, read_genome

app = Flask(__name__)
socketio = SocketIO(app)


@dataclass(frozen=True)
class SimulationState:
    human_only: int = 0
    human_genome1: int = 0
    human_genome2: int = 0
    human_genome1_genome2: int = 0
    total_comparisons: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "Human only": self.human_only,
            f"Human-{simulation.config.genome1_name}": self.human_genome1,
            f"Human-{simulation.config.genome2_name}": self.human_genome2,
            f"Human-{simulation.config.genome1_name}-{simulation.config.genome2_name}": self.human_genome1_genome2,
        }


@dataclass(frozen=True)
class SimulationConfig:
    chunk_size: int = 40
    max_differences: int = 5
    num_processes: int = mp.cpu_count()
    update_interval: int = 100
    human_genome_path: str = ""
    genome1_path: str = ""
    genome2_path: str = ""
    genome1_name: str = "Genome1"
    genome2_name: str = "Genome2"


class Simulation:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.state = SimulationState()
        self.human_genome: str = ""
        self.genome1: str = ""
        self.genome2: str = ""

    def load_genomes(self) -> None:
        self.human_genome = read_genome(self.config.human_genome_path)
        self.genome1 = read_genome(self.config.genome1_path)
        self.genome2 = read_genome(self.config.genome2_path)

    def run_comparison(self) -> tuple[bool, bool]:
        print("Running comparison")
        import time

        time.sleep(0.01)

        import random

        return random.choice([True, False]), random.choice([True, False])

    # def run_comparison(self) -> tuple[bool, bool]:
    #     print("Running comparison")
    #     chunk_start = random.randint(0, len(self.human_genome) - self.config.chunk_size)
    #     chunk = self.human_genome[chunk_start : chunk_start + self.config.chunk_size]

    #     genome1_match = compare_chunk(chunk, self.genome1, self.config.max_differences)
    #     genome2_match = compare_chunk(chunk, self.genome2, self.config.max_differences)

    #     return genome1_match, genome2_match

    def update_state(self, genome1_match: bool, genome2_match: bool) -> None:
        if genome1_match and genome2_match:
            self.state = SimulationState(
                **{**self.state.__dict__, "human_genome1_genome2": self.state.human_genome1_genome2 + 1}
            )
        elif genome1_match:
            self.state = SimulationState(**{**self.state.__dict__, "human_genome1": self.state.human_genome1 + 1})
        elif genome2_match:
            self.state = SimulationState(**{**self.state.__dict__, "human_genome2": self.state.human_genome2 + 1})
        else:
            self.state = SimulationState(**{**self.state.__dict__, "human_only": self.state.human_only + 1})

        self.state = SimulationState(**{**self.state.__dict__, "total_comparisons": self.state.total_comparisons + 1})

    def run_simulation(self, callback: Callable[[SimulationState], Any]) -> None:
        print("Starting simulation")
        # self.load_genomes()  # Load genomes before starting the simulation
        print("Genomes loaded")
        from concurrent.futures import ProcessPoolExecutor, as_completed

        with ProcessPoolExecutor(max_workers=self.config.num_processes) as executor:
            for future in as_completed(executor.submit(self.run_comparison) for _ in range(10_000)):
                genome1_match, genome2_match = future.result()
                print("Updating state")
                self.update_state(genome1_match, genome2_match)
                print("State updated")
                if self.state.total_comparisons % self.config.update_interval == 0:
                    print("Calling callback")
                    callback(self.state)


# Add this function to load the configuration from a file
def load_config() -> SimulationConfig:
    try:
        with open("config.json", "r") as f:
            config_dict = json.load(f)
        return SimulationConfig(**config_dict)
    except FileNotFoundError:
        return SimulationConfig()


# Add this function to save the configuration to a file
def save_config(config: SimulationConfig) -> None:
    with open("config.json", "w") as f:
        json.dump(config.__dict__, f)


# Initialize simulation with loaded config
simulation = Simulation(load_config())


@app.route("/")
def index() -> str:
    return render_template("index.html", config=simulation.config)


@app.route("/configure", methods=["POST"])
def configure() -> str:
    global simulation

    # Function to save uploaded file and return its path
    def save_uploaded_file(file_key: str) -> str:
        if file_key not in request.files:
            return simulation.config.__dict__[file_key.replace("_file", "_path")]
        file = request.files[file_key]
        if file.filename == "":
            return simulation.config.__dict__[file_key.replace("_file", "_path")]
        filename = secure_filename(file.filename)
        save_path = os.path.join("uploads", filename)
        file.save(save_path)
        return save_path

    config = SimulationConfig(
        chunk_size=int(request.form["chunk_size"]),
        max_differences=int(request.form["max_differences"]),
        num_processes=int(request.form["num_processes"]),
        update_interval=int(request.form["update_interval"]),
        human_genome_path=save_uploaded_file("human_genome_file"),
        genome1_path=save_uploaded_file("genome1_file"),
        genome2_path=save_uploaded_file("genome2_file"),
        genome1_name=request.form["genome1_name"],
        genome2_name=request.form["genome2_name"],
    )
    simulation = Simulation(config)
    save_config(config)  # Save the new configuration
    return jsonify({"message": "Configuration updated successfully", "config": config.__dict__})


@app.route("/browse", methods=["POST"])
def browse_filesystem() -> dict[str, list[str] | str]:
    current_path = request.json.get("current_path", "/")
    try:
        path = Path(current_path).resolve()
        if not path.is_dir():
            path = path.parent

        items = []
        for item in path.iterdir():
            items.append({"name": item.name, "path": str(item), "type": "directory" if item.is_dir() else "file"})

        return {"items": sorted(items, key=lambda x: (x["type"] == "file", x["name"])), "current_path": str(path)}
    except Exception as e:
        return {"error": str(e)}


@socketio.on("start_simulation")
def handle_start_simulation() -> None:
    def update_client(state: SimulationState) -> None:
        socketio.emit("update", {"state": state.to_dict(), "total": state.total_comparisons})

    try:
        simulation.run_simulation(update_client)
    except FileNotFoundError as e:
        socketio.emit("error", {"message": f"File not found: {str(e)}"})
    except Exception as e:
        socketio.emit("error", {"message": f"An error occurred: {str(e)}"})


@socketio.on("kill_application")
def handle_kill_application():
    print("Killing application...")
    socketio.emit("application_killed")
    os.kill(os.getpid(), signal.SIGINT)


if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)  # Ensure uploads directory exists
    socketio.run(app, debug=True)
