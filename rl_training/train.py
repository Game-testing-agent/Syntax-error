"""
train.py — Reinforcement Learning Training Loop for Godot 2D Platformer

Trains the QLearningAgent inside the simulated GodotPlatformerEnv.
Outputs:
  - q_table.json            : Saved Q-table for deployment
  - training_metrics.csv    : Episode-by-episode training telemetry & rewards
"""

import os
import csv
import json
import time
import argparse
from typing import Dict, Any, List

from environment import GodotPlatformerEnv
from agent import QLearningAgent


def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """Loads RL training hyperparameters from JSON config."""
    if not os.path.isabs(config_path):
        config_path = os.path.join(os.path.dirname(__file__), config_path)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def train(
    episodes: int = 300,
    config_file: str = "config.json",
    output_dir: str = "",
    verbose: bool = True,
) -> None:
    """Executes the Q-learning training loop and persists metrics and model."""
    if not output_dir:
        output_dir = os.path.dirname(__file__)

    cfg = load_config(config_file)
    episodes = episodes or cfg.get("episodes", 300)

    env = GodotPlatformerEnv(cfg)
    agent = QLearningAgent(
        learning_rate=cfg.get("learning_rate", 0.1),
        discount_factor=cfg.get("discount_factor", 0.95),
        epsilon_initial=cfg.get("epsilon_initial", 1.0),
        epsilon_decay=cfg.get("epsilon_decay", 0.995),
        epsilon_min=cfg.get("epsilon_min", 0.05),
    )

    metrics_csv_path = os.path.join(output_dir, "training_metrics.csv")
    q_table_path = os.path.join(output_dir, "q_table.json")

    print("======================================================================")
    print("  GODOT 2D PLATFORMER - REINFORCEMENT LEARNING TRAINING LOOP")
    print(f"  Level Target    : {cfg.get('level_target', 'Level01')}")
    print(f"  Episodes        : {episodes}")
    print(f"  Learning Rate   : {agent.alpha}")
    print(f"  Discount Factor : {agent.gamma}")
    print(f"  Initial Epsilon : {agent.epsilon}")
    print("======================================================================\n")

    metrics_rows: List[Dict[str, Any]] = []
    recent_goals = 0
    start_time = time.time()

    for ep in range(1, episodes + 1):
        state = env.reset()
        total_reward = 0.0
        steps = 0
        done = False
        outcome = "time_limit"

        while not done:
            action = agent.choose_action(state)
            next_state, reward, done, info = env.step(action)
            agent.update(state, action, reward, next_state, done)

            state = next_state
            total_reward += reward
            steps += 1

            if done:
                outcome = info.get("event", "finished")
                if info.get("goal_reached"):
                    recent_goals += 1

        agent.decay_epsilon()

        # Log metrics
        metrics_rows.append({
            "episode": ep,
            "total_reward": round(total_reward, 2),
            "steps": steps,
            "epsilon": round(agent.epsilon, 4),
            "outcome": outcome,
            "score": env.score,
            "states_learned": len(agent.q_table),
        })

        # Periodic status print
        if verbose and (ep % 25 == 0 or ep == 1 or ep == episodes):
            window_size = 25 if ep >= 25 else ep
            success_rate = (recent_goals / window_size) * 100.0
            print(
                f"[Episode {ep:03d}/{episodes:03d}]  "
                f"Reward: {total_reward:6.1f} | "
                f"Steps: {steps:3d} | "
                f"Eps: {agent.epsilon:.3f} | "
                f"States: {len(agent.q_table):3d} | "
                f"Recent Success: {success_rate:4.1f}% | "
                f"Outcome: {outcome}"
            )
            recent_goals = 0

    elapsed = time.time() - start_time
    print(f"\n[OK] Training completed in {elapsed:.2f}s across {episodes} episodes.")

    # 1. Save Training Metrics CSV
    fieldnames = ["episode", "total_reward", "steps", "epsilon", "outcome", "score", "states_learned"]
    with open(metrics_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(metrics_rows)
    print(f"[OK] Training metrics saved to: {metrics_csv_path}")

    # 2. Save Learned Q-Table JSON
    agent.save_q_table(q_table_path)
    print(f"[OK] Trained Q-table saved to: {q_table_path}")

    # 3. Demonstration Evaluation Run (Greedy Policy)
    print("\n======================================================================")
    print("  RUNNING EVALUATION ON LEARNED POLICY (GREEDY = NO EXPLORATION)")
    print("======================================================================")
    eval_state = env.reset()
    eval_reward = 0.0
    eval_steps = 0
    eval_done = False
    trajectory = []

    while not eval_done:
        eval_action = agent.choose_action(eval_state, greedy=True)
        act_name = agent.get_action_name(eval_action)
        trajectory.append((eval_steps, round(env.player_x, 1), round(env.player_y, 1), act_name))

        eval_state, r, eval_done, eval_info = env.step(eval_action)
        eval_reward += r
        eval_steps += 1

    print(f"Eval Steps    : {eval_steps}")
    print(f"Eval Reward   : {eval_reward:.1f}")
    print(f"Eval Outcome  : {eval_info.get('event', 'finished')}")
    print(f"Final Player X: {env.player_x:.1f}, Y: {env.player_y:.1f}")
    print(f"Goal Reached  : {eval_info.get('goal_reached', False)}")
    print("\nSample Learned Trajectory Checkpoints (Step, X, Y, Action):")
    for t in trajectory[::max(1, len(trajectory) // 8)]:
        print(f"  Step {t[0]:02d} | X={t[1]:6.1f}, Y={t[2]:6.1f} | Action: {t[3]}")
    print("======================================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Godot 2D Platformer RL Agent")
    parser.add_argument("--episodes", type=int, default=300, help="Number of episodes to train")
    parser.add_argument("--config", type=str, default="config.json", help="Path to config.json")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose episode prints")
    args = parser.parse_args()

    train(episodes=args.episodes, config_file=args.config, verbose=not args.quiet)
