extends Node

signal updated
signal died
signal reset

var score: = 0: set = set_score
var deaths: = 0: set = set_deaths
var is_resetting: bool = false
# Milestone score regression
var bug_milestone_score_tax: bool = true


func reset_data() -> void:
	is_resetting = true
	var score_before = score
	var deaths_before = deaths
	self.score = 0
	self.deaths = 0
	is_resetting = false

	if GameLogger:
		GameLogger.log_event("global_state_reset", "ui", {
			"score_before": score_before,
			"deaths_before": deaths_before,
			"reason": "player_reset"
		})

	reset.emit()


func set_score(new_score: int) -> void:
	var old_score = score
	var final_score = new_score

	# TRICKY  4: Milestone Score Regression
	# On collecting subsequent collectibles after reaching or exceeding 500 points,
	# an erroneous tier-adjustment logic applies a -10 deduction instead of full addition,
	# creating an unexpected score decrease anomaly in telemetry.
	if bug_milestone_score_tax and not is_resetting and old_score >= 500 and new_score > old_score:
		final_score = old_score - 10

	score = final_score

	if is_inside_tree() and GameLogger:
		var delta = score - old_score
		if delta < 0 and not is_resetting:
			GameLogger.log_anomaly("unexpected_score_change", {
				"old_score": old_score,
				"new_score": new_score,
				"delta": delta,
				"expected": "Score should only increase or reset to 0",
				"observed": "Score decreased by " + str(abs(delta))
			}, "warning")

	updated.emit()


func set_deaths(new_value: int) -> void:
	var old_deaths = deaths
	deaths = new_value

	if is_inside_tree() and GameLogger and deaths != old_deaths:
		GameLogger.log_event("death_counter_incremented", "player_lifecycle", {
			"deaths_before": old_deaths,
			"deaths_after": deaths
		})

	died.emit()
