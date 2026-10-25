"""
agent.py — Tabular Q-Learning Agent for Godot 2D Platformer

Implements an epsilon-greedy Q-learning algorithm that learns state-action values:
  Q(s, a) <- Q(s, a) + alpha * [reward + gamma * max_a' Q(s', a') - Q(s, a)]

Zero external dependencies: uses only Python Standard Library.
Trained policies output actions directly compatible with bot_controller.py and explorer.py.
"""

import json
import random
from typing import Dict, List, Any, Optional
from environment import NUM_ACTIONS, ACTION_NAMES, ACTION_IDLE


class QLearningAgent:
    """
    Q-Learning agent capable of learning optimal navigation, gap jumping,
    and enemy avoidance for 2D platformer levels.
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        discount_factor: float = 0.95,
        epsilon_initial: float = 1.0,
        epsilon_decay: float = 0.995,
        epsilon_min: float = 0.05,
        num_actions: int = NUM_ACTIONS,
    ):
        self.alpha = learning_rate
        self.gamma = discount_factor
        self.epsilon = epsilon_initial
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.num_actions = num_actions

        # Q-table: { state_string: [q_val_action_0, ..., q_val_action_N] }
        self.q_table: Dict[str, List[float]] = {}

    def get_q_values(self, state: str) -> List[float]:
        """Returns Q-values for a given state, initializing with zeros if unvisited."""
        if state not in self.q_table:
            self.q_table[state] = [0.0] * self.num_actions
        return self.q_table[state]

    def choose_action(self, state: str, greedy: bool = False) -> int:
        """
        Selects an action using an epsilon-greedy policy.
        If greedy=True, strictly chooses the action with the highest Q-value.
        """
        if not greedy and random.random() < self.epsilon:
            return random.randint(0, self.num_actions - 1)

        q_vals = self.get_q_values(state)
        max_q = max(q_vals)
        # Break ties randomly among best actions
        best_actions = [a for a, q in enumerate(q_vals) if q == max_q]
        return random.choice(best_actions)

    def update(
        self,
        state: str,
        action: int,
        reward: float,
        next_state: str,
        done: bool,
    ) -> float:
        """
        Updates the Q-table using the Bellman equation.
        Returns the TD error magnitude.
        """
        current_q = self.get_q_values(state)[action]

        if done:
            target = reward
        else:
            next_max_q = max(self.get_q_values(next_state))
            target = reward + self.gamma * next_max_q

        td_error = target - current_q
        self.q_table[state][action] = current_q + self.alpha * td_error
        return abs(td_error)

    def decay_epsilon(self) -> float:
        """Decays the exploration rate epsilon down to the configured minimum."""
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        return self.epsilon

    def get_action_name(self, action: int) -> str:
        """Returns the human-readable action name matching Godot input names."""
        return ACTION_NAMES.get(action, "unknown")

    def get_best_action_name(self, state: str) -> str:
        """Returns the best action name for deployment in bot_controller.py."""
        best_action = self.choose_action(state, greedy=True)
        return self.get_action_name(best_action)

    def save_q_table(self, filepath: str) -> None:
        """Saves the learned Q-table and agent hyper-parameters to JSON."""
        data = {
            "hyperparameters": {
                "alpha": self.alpha,
                "gamma": self.gamma,
                "epsilon": self.epsilon,
                "num_states_learned": len(self.q_table),
            },
            "q_table": self.q_table,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_q_table(self, filepath: str) -> None:
        """Loads a pre-trained Q-table from JSON."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.q_table = data.get("q_table", {})
            hp = data.get("hyperparameters", {})
            self.alpha = hp.get("alpha", self.alpha)
            self.gamma = hp.get("gamma", self.gamma)
            self.epsilon = hp.get("epsilon", self.epsilon_min)
