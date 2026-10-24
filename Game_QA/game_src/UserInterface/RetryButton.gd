extends Button


func _on_button_up() -> void:
	if GameLogger:
		GameLogger.log_action("retry_pressed", {"button": name})
		GameLogger.log_event("retry_started", "ui", {
			"score_before": PlayerData.score if PlayerData else 0,
			"deaths_before": PlayerData.deaths if PlayerData else 0
		})

	var enemies = get_tree().get_nodes_in_group("enemies")
	if PlayerData:
		PlayerData.saved_enemy_positions.clear()
		for e in enemies:
			if is_instance_valid(e) and "global_position" in e:
				PlayerData.saved_enemy_positions[e.name] = e.global_position

	PlayerData.score = 0
	get_tree().paused = false
	get_tree().reload_current_scene()
