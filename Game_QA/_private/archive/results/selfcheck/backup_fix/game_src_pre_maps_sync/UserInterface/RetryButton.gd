extends Button


func _on_button_up() -> void:
	if GameLogger:
		GameLogger.log_action("retry_pressed", {"button": name})
		GameLogger.log_event("retry_started", "ui", {
			"score_before": PlayerData.score if PlayerData else 0,
			"deaths_before": PlayerData.deaths if PlayerData else 0
		})

	PlayerData.score = 0
	get_tree().paused = false
	get_tree().reload_current_scene()
