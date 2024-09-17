import json
import multiprocessing as mp
import os
import random
import signal
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from itertools import repeat
from multiprocessing import shared_memory
from pathlib import Path
from typing import Any

import numpy as np
import plotly.graph_objects as go
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename

from genome_comparison import compare_chunk, read_and_encode_genome

app = Flask(__name__)
socketio = SocketIO(app)


@dataclass(frozen=True)
class SimulationState:
    human_only: int = 0
    human_genome1: int = 0
    human_genome2: int = 0
    human_genome3: int = 0
    human_genome1_genome2: int = 0
    human_genome1_genome3: int = 0
    human_genome2_genome3: int = 0
    human_genome1_genome2_genome3: int = 0
    total_comparisons: int = 0

    def to_dict(self) -> dict[str, int]:
        result = {
            "Human only": self.human_only,
            f"Human-{simulation.config.genome1_name}": self.human_genome1,
            f"Human-{simulation.config.genome2_name}": self.human_genome2,
            f"Human-{simulation.config.genome1_name}-{simulation.config.genome2_name}": self.human_genome1_genome2,
        }
        if simulation.config.genome3_path:
            result.update(
                {
                    f"Human-{simulation.config.genome3_name}": self.human_genome3,
                    f"Human-{simulation.config.genome1_name}-{simulation.config.genome3_name}": self.human_genome1_genome3,
                    f"Human-{simulation.config.genome2_name}-{simulation.config.genome3_name}": self.human_genome2_genome3,
                    f"Human-{simulation.config.genome1_name}-{simulation.config.genome2_name}-{simulation.config.genome3_name}": self.human_genome1_genome2_genome3,
                }
            )
        return result


@dataclass(frozen=True)
class SimulationConfig:
    chunk_size: int = 40
    max_differences: int = 5
    num_processes: int = mp.cpu_count()
    update_interval: int = 100
    human_genome_path: str = ""
    genome1_path: str = ""
    genome2_path: str = ""
    genome3_path: str = ""
    genome1_name: str = "Genome1"
    genome2_name: str = "Genome2"
    genome3_name: str = "Genome3"


class Simulation:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.state = SimulationState()
        self.human_genome_shm: shared_memory.SharedMemory | None = None
        self.genome1_shm: shared_memory.SharedMemory | None = None
        self.genome2_shm: shared_memory.SharedMemory | None = None
        self.genome3_shm: shared_memory.SharedMemory | None = None
        self.human_genome_size: int = 0
        self.genome1_size: int = 0
        self.genome2_size: int = 0
        self.genome3_size: int = 0

    def load_genomes(self) -> None:
        try:
            print("Loading genomes")
            print(f"Human genome path: {self.config.human_genome_path}")
            human_genome = read_and_encode_genome(self.config.human_genome_path)
            print("Human genome loaded")
            print(f"Genome1 path: {self.config.genome1_path}")
            genome1 = read_and_encode_genome(self.config.genome1_path)
            print("Genome1 loaded")
            print(f"Genome2 path: {self.config.genome2_path}")
            genome2 = read_and_encode_genome(self.config.genome2_path)
            print("Genome2 loaded")

            self.human_genome_size = len(human_genome)
            self.genome1_size = len(genome1)
            self.genome2_size = len(genome2)

            self.human_genome_shm = shared_memory.SharedMemory(create=True, size=self.human_genome_size)
            self.genome1_shm = shared_memory.SharedMemory(create=True, size=self.genome1_size)
            self.genome2_shm = shared_memory.SharedMemory(create=True, size=self.genome2_size)

            self.human_genome_shm.buf[:] = human_genome.tobytes()
            self.genome1_shm.buf[:] = genome1.tobytes()
            self.genome2_shm.buf[:] = genome2.tobytes()

            if self.config.genome3_path:
                print(f"Genome3 path: {self.config.genome3_path}")
                genome3 = read_and_encode_genome(self.config.genome3_path)
                print("Genome3 loaded")
                self.genome3_size = len(genome3)
                self.genome3_shm = shared_memory.SharedMemory(create=True, size=self.genome3_size)
                self.genome3_shm.buf[:] = genome3.tobytes()
        except Exception as e:
            print(f"Error loading genomes: {e}")
            raise e

    def run_comparison(self) -> tuple[bool, bool, bool]:
        # human_genome_shm = shared_memory.SharedMemory(name=human_genome_name)
        # genome1_shm = shared_memory.SharedMemory(name=genome1_name)
        # genome2_shm = shared_memory.SharedMemory(name=genome2_name)

        human_genome = np.frombuffer(self.human_genome_shm.buf[: self.human_genome_size], dtype=np.int8)
        genome1 = np.frombuffer(self.genome1_shm.buf[: self.genome1_size], dtype=np.int8)
        genome2 = np.frombuffer(self.genome2_shm.buf[: self.genome2_size], dtype=np.int8)

        chunk_start = random.randint(0, len(human_genome) - self.config.chunk_size)
        chunk = human_genome[chunk_start : chunk_start + self.config.chunk_size]

        genome1_match = compare_chunk(chunk, genome1, self.config.max_differences)
        genome2_match = compare_chunk(chunk, genome2, self.config.max_differences)

        genome3_match = False
        if self.config.genome3_path:
            genome3 = np.frombuffer(self.genome3_shm.buf[: self.genome3_size], dtype=np.int8)
            genome3_match = compare_chunk(chunk, genome3, self.config.max_differences)

        print(
            f"Chunk: {chunk}, Genome1 match: {genome1_match}, Genome2 match: {genome2_match}, Genome3 match: {genome3_match}"
        )

        return genome1_match, genome2_match, genome3_match

    def update_state(self, genome1_match: bool, genome2_match: bool, genome3_match: bool) -> None:
        new_state = {}
        if self.config.genome3_path:
            if genome1_match and genome2_match and genome3_match:
                new_state["human_genome1_genome2_genome3"] = self.state.human_genome1_genome2_genome3 + 1
            elif genome1_match and genome2_match:
                new_state["human_genome1_genome2"] = self.state.human_genome1_genome2 + 1
            elif genome1_match and genome3_match:
                new_state["human_genome1_genome3"] = self.state.human_genome1_genome3 + 1
            elif genome2_match and genome3_match:
                new_state["human_genome2_genome3"] = self.state.human_genome2_genome3 + 1
            elif genome1_match:
                new_state["human_genome1"] = self.state.human_genome1 + 1
            elif genome2_match:
                new_state["human_genome2"] = self.state.human_genome2 + 1
            elif genome3_match:
                new_state["human_genome3"] = self.state.human_genome3 + 1
            else:
                new_state["human_only"] = self.state.human_only + 1
        else:
            if genome1_match and genome2_match:
                new_state["human_genome1_genome2"] = self.state.human_genome1_genome2 + 1
            elif genome1_match:
                new_state["human_genome1"] = self.state.human_genome1 + 1
            elif genome2_match:
                new_state["human_genome2"] = self.state.human_genome2 + 1
            else:
                new_state["human_only"] = self.state.human_only + 1

        new_state["total_comparisons"] = self.state.total_comparisons + 1
        self.state = SimulationState(**{**self.state.__dict__, **new_state})

    def run_simulation(self, callback: Callable[[SimulationState], Any]) -> None:
        print("Starting simulation")
        self.load_genomes()
        print("Genomes loaded")

        with ProcessPoolExecutor(max_workers=self.config.num_processes) as executor:
            for future in as_completed(executor.submit(self.run_comparison) for _ in range(10_000)):
                genome1_match, genome2_match, genome3_match = future.result()
                print("Updating state")
                self.update_state(genome1_match, genome2_match, genome3_match)
                print("State updated")
                if self.state.total_comparisons % self.config.update_interval == 0:
                    print("Calling callback")
                    callback(self.state)

        # Clean up shared memory
        self.human_genome_shm.close()
        self.genome1_shm.close()
        self.genome2_shm.close()
        self.human_genome_shm.unlink()
        self.genome1_shm.unlink()
        self.genome2_shm.unlink()
        if self.genome3_shm:
            self.genome3_shm.close()
            self.genome3_shm.unlink()


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
        genome3_path=save_uploaded_file("genome3_file"),
        genome1_name=request.form["genome1_name"],
        genome2_name=request.form["genome2_name"],
        genome3_name=request.form["genome3_name"],
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
