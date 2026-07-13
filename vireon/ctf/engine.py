"""
VIREON CTF Engine — Gamified neurosecurity challenge framework.

The first BCI security Capture-the-Flag engine. Provides a structured
challenge system where users must detect, analyze, and mitigate neural
interface attacks within configurable constraints.

Challenge types:
  - detection: Identify the active attack type from signal anomalies
  - mitigation: Configure IPS/filters to neutralize an active attack
  - forensics: Analyze post-incident telemetry to reconstruct attack timeline
  - red_team: Craft an attack that evades detection for N seconds
  - compliance: Generate correct SBOM/STRIDE documentation

Usage:
    runner = ChallengeRunner()
    runner.load_challenge("challenge_01.toml")
    result = runner.run()
    print(result.score)
"""

import time
import json
import os
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ChallengeObjective:
    """A single objective within a challenge."""
    objective_id: str
    description: str
    check_type: str       # "detect_attack", "mitigate_attack", "answer_question", "generate_artifact"
    expected_value: str   # Expected answer or condition
    points: int = 100
    hint: str = ""
    completed: bool = False
    completed_at: Optional[str] = None


@dataclass
class Challenge:
    """A CTF challenge definition."""
    challenge_id: str
    title: str
    description: str
    difficulty: str         # "beginner", "intermediate", "advanced", "expert"
    category: str           # "detection", "mitigation", "forensics", "red_team", "compliance"
    time_limit_sec: float
    objectives: List[ChallengeObjective] = field(default_factory=list)
    setup_config: Dict[str, Any] = field(default_factory=dict)
    max_points: int = 0
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.max_points == 0:
            self.max_points = sum(o.points for o in self.objectives)


@dataclass
class ChallengeResult:
    """Result of a completed challenge attempt."""
    challenge_id: str
    challenge_title: str
    started_at: str
    completed_at: str
    time_elapsed_sec: float
    score: int
    max_score: int
    percentage: float
    objectives_completed: int
    objectives_total: int
    grade: str             # "S", "A", "B", "C", "D", "F"
    details: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Scoreboard:
    """Tracks scores across multiple challenge attempts."""
    player_name: str = "anonymous"
    attempts: List[ChallengeResult] = field(default_factory=list)
    total_score: int = 0
    total_max_score: int = 0

    def add_result(self, result: ChallengeResult):
        self.attempts.append(result)
        self.total_score += result.score
        self.total_max_score += result.max_score

    def get_rank(self) -> str:
        if self.total_max_score == 0:
            return "Unranked"
        pct = 100 * self.total_score / self.total_max_score
        if pct >= 95:
            return "Neuro-Sentinel"
        elif pct >= 80:
            return "Shield Bearer"
        elif pct >= 60:
            return "Signal Analyst"
        elif pct >= 40:
            return "Apprentice"
        else:
            return "Observer"


# ==================== Built-in Challenges ====================

def _build_challenge_detect_the_drift() -> Challenge:
    return Challenge(
        challenge_id="ctf_001",
        title="Detect the Drift",
        description=(
            "A slow, subtle signal drift attack is active on the BCI pipeline. "
            "The drift rate is calibrated to stay below the static RMS threshold. "
            "Your mission: identify which channels are affected and name the attack type."
        ),
        difficulty="beginner",
        category="detection",
        time_limit_sec=120.0,
        tags=["IDS", "drift", "CUSUM"],
        objectives=[
            ChallengeObjective(
                objective_id="obj_1",
                description="Identify the attack type",
                check_type="answer_question",
                expected_value="SLOW_DRIFT_ANOMALY",
                points=100,
                hint="This attack evades static thresholds. Look at the CUSUM detector.",
            ),
            ChallengeObjective(
                objective_id="obj_2",
                description="Name the target channels (comma-separated)",
                check_type="answer_question",
                expected_value="0,1",
                points=100,
                hint="Check the IDS detection logs for channel numbers.",
            ),
            ChallengeObjective(
                objective_id="obj_3",
                description="What qTARA technique ID corresponds to this attack?",
                check_type="answer_question",
                expected_value="QIF-T2101",
                points=50,
                hint="Signal suppression/drift attacks map to the T21xx range.",
            ),
        ],
        setup_config={
            "attack_type": "drift",
            "target_channels": [0, 1],
            "drift_rate_uv_per_sec": 3.0,
            "duration_sec": 10.0,
        },
    )


def _build_challenge_stop_the_jammer() -> Challenge:
    return Challenge(
        challenge_id="ctf_002",
        title="Stop the Jammer",
        description=(
            "An RF jamming attack is causing 50%% packet loss on the telemetry link. "
            "The IDS is screaming with HIGH_NOISE_ANOMALY alerts. "
            "Your mission: configure the IPS to mitigate the attack without losing clinical data."
        ),
        difficulty="intermediate",
        category="mitigation",
        time_limit_sec=180.0,
        tags=["IPS", "jamming", "RF", "resilience"],
        objectives=[
            ChallengeObjective(
                objective_id="obj_1",
                description="What IDS anomaly type is triggered by RF jamming?",
                check_type="answer_question",
                expected_value="HIGH_NOISE_ANOMALY",
                points=50,
            ),
            ChallengeObjective(
                objective_id="obj_2",
                description="What is the correct IPS action to mitigate jamming?",
                check_type="answer_question",
                expected_value="enable_bandpass_filter",
                points=100,
                hint="The AdversarialDefenseFilter zeroes out-of-band frequencies.",
            ),
            ChallengeObjective(
                objective_id="obj_3",
                description="After mitigation, what should the stimulation fallback mode be?",
                check_type="answer_question",
                expected_value="fallback_mode",
                points=100,
                hint="The Digital Twin has a safe fallback therapy mode.",
            ),
        ],
        setup_config={
            "attack_type": "rf_jamming",
            "drop_rate": 0.5,
            "duration_sec": 15.0,
        },
    )


def _build_challenge_unmask_the_replay() -> Challenge:
    return Challenge(
        challenge_id="ctf_003",
        title="Unmask the Replay",
        description=(
            "Something is wrong with the EEG feed — it looks clean, but the patient's "
            "clinical state is deteriorating. An attacker has captured and is replaying "
            "a clean signal segment. Your mission: prove the replay is happening."
        ),
        difficulty="intermediate",
        category="forensics",
        time_limit_sec=240.0,
        tags=["replay", "forensics", "spectral", "entropy"],
        objectives=[
            ChallengeObjective(
                objective_id="obj_1",
                description="What attack type uses captured clean data to mask real activity?",
                check_type="answer_question",
                expected_value="SessionReplayAttack",
                points=100,
            ),
            ChallengeObjective(
                objective_id="obj_2",
                description="Which IDS detection would reveal statistical uniformity in replayed data?",
                check_type="answer_question",
                expected_value="SPECTRAL_SPOOFING_ANOMALY",
                points=100,
                hint="Replayed data has unnaturally low spectral entropy.",
            ),
            ChallengeObjective(
                objective_id="obj_3",
                description="What STRIDE category does a replay attack fall under?",
                check_type="answer_question",
                expected_value="S",
                points=50,
                hint="Spoofing, Tampering, Repudiation, Information Disclosure, DoS, Elevation",
            ),
        ],
        setup_config={
            "attack_type": "session_replay",
            "capture_duration_sec": 3.0,
            "target_channels": [0, 1, 2, 3],
        },
    )


def _build_challenge_decode_the_backdoor() -> Challenge:
    return Challenge(
        challenge_id="ctf_004",
        title="Decode the Backdoor",
        description=(
            "The autoencoder IDS has been subtly poisoned during calibration. "
            "It now fails to detect a specific attack waveform (20 Hz, 30 μV). "
            "Your mission: identify the poisoning strategy and propose a defense."
        ),
        difficulty="advanced",
        category="forensics",
        time_limit_sec=300.0,
        tags=["adversarial_ml", "poisoning", "autoencoder", "backdoor"],
        objectives=[
            ChallengeObjective(
                objective_id="obj_1",
                description="What class of ML attack compromises the training data?",
                check_type="answer_question",
                expected_value="data_poisoning",
                points=100,
            ),
            ChallengeObjective(
                objective_id="obj_2",
                description="What defense filters input before it reaches the ML decoder?",
                check_type="answer_question",
                expected_value="AdversarialDefenseFilter",
                points=100,
                hint="Check vireon.core.ml_decoder for the bandpass filter.",
            ),
            ChallengeObjective(
                objective_id="obj_3",
                description="What frequency band (Hz) should the bandpass filter cover to block the trigger?",
                check_type="answer_question",
                expected_value="1-30",
                points=100,
                hint="The default filter covers 1.0 Hz to 30.0 Hz.",
            ),
        ],
        setup_config={
            "attack_type": "backdoor_trigger",
            "trigger_frequency_hz": 20.0,
            "trigger_amplitude_uv": 30.0,
        },
    )


def _build_challenge_breach_the_envelope() -> Challenge:
    return Challenge(
        challenge_id="ctf_005",
        title="Breach the Envelope",
        description=(
            "You are the red team. The IPS has hard safety limits: amplitude ≤ 4.0 mA, "
            "cumulative charge ≤ 5200 μC. Your mission: find a parameter combination that "
            "causes the Digital Twin's tissue_damage_risk to rise above NONE without "
            "triggering the IPS clamp."
        ),
        difficulty="expert",
        category="red_team",
        time_limit_sec=360.0,
        tags=["red_team", "safety", "IPS", "evasion"],
        objectives=[
            ChallengeObjective(
                objective_id="obj_1",
                description="What is the maximum amplitude (mA) the IPS will allow?",
                check_type="answer_question",
                expected_value="4.0",
                points=50,
            ),
            ChallengeObjective(
                objective_id="obj_2",
                description="What parameter accumulates over time and can breach safety even at low amplitude?",
                check_type="answer_question",
                expected_value="cumulative_charge",
                points=100,
                hint="Charge = amplitude × time. Low amplitude over long duration still accumulates.",
            ),
            ChallengeObjective(
                objective_id="obj_3",
                description="What thermal mechanism can cause tissue damage below the amplitude limit?",
                check_type="answer_question",
                expected_value="thermal_dose",
                points=150,
                hint="Check the NeuroIPS accumulated_thermal_dose tracking.",
            ),
        ],
        setup_config={
            "attack_type": "low_and_slow",
            "amplitude_ma": 3.5,
            "frequency_hz": 130.0,
            "duration_sec": 30.0,
        },
    )


# Registry of built-in challenges
BUILTIN_CHALLENGES: Dict[str, Callable[[], Challenge]] = {
    "ctf_001": _build_challenge_detect_the_drift,
    "ctf_002": _build_challenge_stop_the_jammer,
    "ctf_003": _build_challenge_unmask_the_replay,
    "ctf_004": _build_challenge_decode_the_backdoor,
    "ctf_005": _build_challenge_breach_the_envelope,
}


class ChallengeRunner:
    """Runs CTF challenges and evaluates player submissions."""

    def __init__(self):
        self.current_challenge: Optional[Challenge] = None
        self.scoreboard = Scoreboard()
        self.start_time: Optional[float] = None

    def list_challenges(self) -> List[Dict[str, str]]:
        """List all available built-in challenges."""
        challenges = []
        for cid, builder in BUILTIN_CHALLENGES.items():
            c = builder()
            challenges.append({
                "id": c.challenge_id,
                "title": c.title,
                "difficulty": c.difficulty,
                "category": c.category,
                "max_points": c.max_points,
                "objectives": len(c.objectives),
                "time_limit": f"{c.time_limit_sec:.0f}s",
            })
        return challenges

    def load_challenge(self, challenge_id: str) -> Challenge:
        """Load a built-in challenge by ID."""
        if challenge_id not in BUILTIN_CHALLENGES:
            available = ", ".join(BUILTIN_CHALLENGES.keys())
            raise ValueError(f"Unknown challenge '{challenge_id}'. Available: {available}")

        self.current_challenge = BUILTIN_CHALLENGES[challenge_id]()
        self.start_time = None
        return self.current_challenge

    def start(self) -> Challenge:
        """Start the current challenge timer."""
        if self.current_challenge is None:
            raise RuntimeError("No challenge loaded. Call load_challenge() first.")
        self.start_time = time.time()
        return self.current_challenge

    def submit_answer(self, objective_id: str, answer: str) -> Dict[str, Any]:
        """
        Submit an answer for a specific objective.

        Returns dict with 'correct', 'points_awarded', and 'feedback'.
        """
        if self.current_challenge is None:
            raise RuntimeError("No challenge loaded.")

        obj = None
        for o in self.current_challenge.objectives:
            if o.objective_id == objective_id:
                obj = o
                break

        if obj is None:
            return {"correct": False, "points_awarded": 0,
                    "feedback": f"Unknown objective: {objective_id}"}

        if obj.completed:
            return {"correct": True, "points_awarded": 0,
                    "feedback": "Already completed."}

        # Normalize comparison
        expected = obj.expected_value.strip().lower()
        submitted = answer.strip().lower()

        if submitted == expected:
            obj.completed = True
            obj.completed_at = datetime.now(timezone.utc).isoformat()
            return {"correct": True, "points_awarded": obj.points,
                    "feedback": f"Correct! +{obj.points} points"}
        else:
            return {"correct": False, "points_awarded": 0,
                    "feedback": f"Incorrect. Hint: {obj.hint}" if obj.hint else "Incorrect."}

    def finish(self) -> ChallengeResult:
        """Finish the current challenge and compute final score."""
        if self.current_challenge is None:
            raise RuntimeError("No challenge loaded.")

        end_time = time.time()
        elapsed = end_time - (self.start_time or end_time)

        completed = [o for o in self.current_challenge.objectives if o.completed]
        score = sum(o.points for o in completed)
        max_score = self.current_challenge.max_points
        percentage = round(100 * score / max(max_score, 1), 1)

        # Grade
        if percentage >= 95:
            grade = "S"
        elif percentage >= 80:
            grade = "A"
        elif percentage >= 60:
            grade = "B"
        elif percentage >= 40:
            grade = "C"
        elif percentage >= 20:
            grade = "D"
        else:
            grade = "F"

        # Time bonus/penalty
        if elapsed <= self.current_challenge.time_limit_sec * 0.5:
            grade_note = " (Speed Bonus!)"
        elif elapsed > self.current_challenge.time_limit_sec:
            grade_note = " (Time Exceeded)"
        else:
            grade_note = ""

        result = ChallengeResult(
            challenge_id=self.current_challenge.challenge_id,
            challenge_title=self.current_challenge.title,
            started_at=datetime.fromtimestamp(self.start_time or 0, tz=timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            time_elapsed_sec=round(elapsed, 1),
            score=score,
            max_score=max_score,
            percentage=percentage,
            objectives_completed=len(completed),
            objectives_total=len(self.current_challenge.objectives),
            grade=grade + grade_note,
            details=[
                {
                    "objective_id": o.objective_id,
                    "description": o.description,
                    "completed": o.completed,
                    "points": o.points if o.completed else 0,
                }
                for o in self.current_challenge.objectives
            ],
        )

        self.scoreboard.add_result(result)
        return result


def print_challenge_list(challenges: List[Dict[str, str]]) -> None:
    """Print available challenges in a table."""
    print("=" * 70)
    print(" VIREON CTF — Available Challenges")
    print("=" * 70)
    print(f"  {'ID':10s} {'Title':30s} {'Diff':15s} {'Pts':>5s}")
    print("  " + "-" * 65)
    for c in challenges:
        diff_icons = {
            "beginner": "★☆☆☆",
            "intermediate": "★★☆☆",
            "advanced": "★★★☆",
            "expert": "★★★★",
        }
        icon = diff_icons.get(c["difficulty"], "????")
        print(f"  {c['id']:10s} {c['title']:30s} {icon:15s} {c['max_points']:>5}")
    print()
    print(f"  {len(challenges)} challenges available. Use: vireon ctf start <ID>")
    print("=" * 70)


def print_challenge_result(result: ChallengeResult) -> None:
    """Print challenge result summary."""
    print()
    print("=" * 60)
    print(f" Challenge Complete: {result.challenge_title}")
    print("=" * 60)
    print(f"  Score:    {result.score}/{result.max_score} ({result.percentage}%)")
    print(f"  Grade:    {result.grade}")
    print(f"  Time:     {result.time_elapsed_sec:.1f}s")
    print(f"  Solved:   {result.objectives_completed}/{result.objectives_total}")
    print()

    for d in result.details:
        icon = "✓" if d["completed"] else "✗"
        pts = f"+{d['points']}" if d["completed"] else "  0"
        print(f"    {icon} [{pts:>4s}] {d['description']}")

    print()
    print("=" * 60)


def print_scoreboard(scoreboard: Scoreboard) -> None:
    """Print the player scoreboard."""
    print("=" * 60)
    print(f" VIREON CTF Scoreboard — {scoreboard.player_name}")
    print("=" * 60)
    print(f"  Rank:  {scoreboard.get_rank()}")
    print(f"  Total: {scoreboard.total_score}/{scoreboard.total_max_score}")
    print()

    if scoreboard.attempts:
        print(f"  {'Challenge':25s} {'Score':>8s} {'Grade':>6s}")
        print("  " + "-" * 45)
        for a in scoreboard.attempts:
            print(f"  {a.challenge_title:25s} {a.score:>3d}/{a.max_score:<4d} {a.grade:>6s}")

    print()
    print("=" * 60)
