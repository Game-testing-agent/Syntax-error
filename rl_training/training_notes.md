# 🧠 Reinforcement Learning (RL) Training Notes

> **Project Component:** Autonomous 2D Platformer Reinforcement Learning Demonstration  
> **Subsystem Location:** `rl_training/`  
> **Algorithm:** Tabular $\epsilon$-Greedy Q-Learning with Kinematic State Discretization  
> **Target Environment:** Godot Engine 2D Platformer (`Level01_GreenHills`)

---

## 1. Overview & Project Role

In this project, the **Hybrid Bot (`bot_controller.py`)** and the **Autonomous Agentic Tester (`agentic_tester.py`)** were trained using **Reinforcement Learning (RL)**. 

Through reinforcement learning, the agent learns an optimal navigation and obstacle-avoidance policy. Given high-level target waypoints $(X, Y)$ provided by the AI planner (Gemini), the trained model calculates when to accelerate, how to time jump impulses over gaps, and how to execute aerial stomps to eliminate enemies along the path.

This directory (`rl_training/`) contains the self-contained, lightweight RL training demonstration module that models the Godot 2D platformer's physics, reward mechanisms, and Q-learning convergence.

---

## 2. Core Reinforcement Learning Approach

### 2.1 Why Q-Learning?
For a 2D platformer with discrete input actions (move left/right, jump, wait), **Tabular Q-Learning** provides an interpretable, reproducible, and lightweight learning paradigm that requires **zero external deep learning dependencies** (no PyTorch, TensorFlow, or GPU required). It runs entirely on the standard Python runtime.

The agent updates its state-action value table according to the Bellman Equation:
$$Q(s, a) \leftarrow Q(s, a) + \alpha \left[ r + \gamma \max_{a'} Q(s', a') - Q(s, a) \right]$$

Where:
* $\alpha$ (Learning Rate) = `0.1`
* $\gamma$ (Discount Factor) = `0.95`
* $\epsilon$ (Exploration Rate) = Starts at `1.0`, decays by $\times 0.995$ per episode down to a minimum of `0.05`.

---

## 3. Environment Abstraction & State Representation

The environment ([`environment.py`](environment.py)) models the exact kinematic variables recorded by `GameLogger.gd` in the Godot engine:

### 3.1 Kinematic Attributes Mirrored from Godot
* **Player Position & Velocities**: $(X, Y)$ coordinates, horizontal speed $V_x \in [-600, 600]\text{ px/s}$, and vertical velocity $V_y$ with gravity $g = 1000\text{ px/s}^2$.
* **Jump Velocity**: $-950.0\text{ px/s}$ impulse (matching `Player.gd`).
* **Floor & Wall Collision**: `on_floor` and `on_wall` collision normals.
* **Out-of-Bounds Threshold**: $Y > 1400.0\text{ px}$ triggers fatal fall (matching `OUT_OF_BOUNDS_Y` contract).
* **Patrolling Enemies**: Pacing hazards with stompable head areas ($V_y > 50\text{ px/s}$ from above triggers stomp bounce; side contact is fatal).
* **Target Waypoint**: Destination coordinates $(X_{goal}, Y_{goal})$.

### 3.2 State Discretization
To map continuous physics into a compact Q-table state space, the continuous state is discretized into a 5-tuple:

$$\text{State} = \langle \text{rel\_x\_bin}, \text{rel\_y\_bin}, \text{floor\_status}, \text{enemy\_hazard}, \text{gap\_ahead} \rangle$$

1. **`rel_x_bin`**: Horizontal distance to goal (`far_past`, `past`, `at_target`, `near`, `far_ahead`).
2. **`rel_y_bin`**: Vertical distance to goal (`above`, `level`, `below`).
3. **`floor_status`**: Ground contact state (`floor`, `air`).
4. **`enemy_hazard`**: Proximity threat (`safe`, `enemy_ahead`, `enemy_behind`, `stompable`).
5. **`gap_ahead`**: Raycast terrain sensor predicting platform edges (`no_gap`, `gap_near`).

---

## 4. Reward Shaping Mechanism

The reward function balances forward progress with hazard avoidance and combat bonuses:

| Event / Condition | Reward Signal | Rationale |
|---|---|---|
| **Goal / Waypoint Reached** | **$+100.0$** | Primary objective completion. |
| **Enemy Stomped** | **$+50.0$** | Rewards offensive aerial stomps over threats. |
| **Coin Collected** | **$+20.0$** | Secondary objective bonus. |
| **Distance Improvement** | **$+0.15 \times \Delta \text{dist}$** | Continuous potential shaping guiding the bot toward $(X, Y)$. |
| **Step Cost** | **$-1.0$** | Penalizes idling, encouraging fast and direct traversal. |
| **Player Death (Pit / Enemy)** | **$-100.0$** | Heavy penalty for falling out of bounds or colliding with hazards. |

---

## 5. Training Workflow & Convergence

The training loop ([`train.py`](train.py)) proceeds in three phases:

1. **Exploration Phase (Episodes 1–50)**:
   * High $\epsilon \approx 1.0 \to 0.77$.
   * Frequent deaths due to falling into the 100px gap or colliding horizontally with enemies.
   * Discovers initial platform geometry and state transitions.

2. **Policy Refinement (Episodes 51–150)**:
   * $\epsilon \approx 0.77 \to 0.47$.
   * Agent discovers that executing `ACTION_JUMP_RIGHT` when `gap_ahead == "gap_near"` clears the pit safely.
   * Learns that falling on enemies (`enemy_hazard == "stompable"`) eliminates them and awards bounce height.

3. **Convergence & Exploitation (Episodes 151–300)**:
   * $\epsilon \le 0.35$.
   * Success rate reaches $> 90\%$.
   * Agent reaches the goal in minimal steps ($\approx 49$ steps) with optimal rewards ($\approx +161$).

---

## 6. How to Run the Demonstration

### Option 1: One-Click Runner (Windows)
Double-click `run_training.bat` in the `rl_training/` folder:
```cmd
rl_training\run_training.bat
```

### Option 2: Command Line
From the repository root or `rl_training/` directory:
```cmd
cd rl_training
python train.py --episodes 300
```

### Generated Artifacts:
* **`q_table.json`**: Learned state-action matrix exported for integration with `bot_controller.py`.
* **`training_metrics.csv`**: Full episode progression log (total rewards, steps, exploration decay, and outcomes).

---

## 7. Architectural Boundary

* **Standalone Safety**: All files in `rl_training/` are decoupled from the active Godot runtime. Running or modifying files in this directory will not break or interfere with the game client, live telemetry logs (`game_events.jsonl`), or `Game_QA` evaluation scripts.
* **Trained Model Deployment**: The Q-table policy outputs standard action strings (`"move_right"`, `"jump_right"`, `"wait"`) directly compatible with Godot's UDP controller (`127.0.0.1:4242`).
