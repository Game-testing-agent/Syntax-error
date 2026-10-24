extends Button


func _on_button_up() -> void:
	if GameLogger:
		GameLogger.log_action("retry_pressed", {"button": name})
		GameLogger.log_event("retry_started", "ui", {
			"score_before": PlayerData.score if PlayerData else 0,
			"deaths_before": PlayerData.deaths if PlayerData else 0
		})

	var is_map4 = ("Map4" in get_tree().current_scene.name) if (get_tree() and get_tree().current_scene) else false
	if BugFlags and BugFlags.map4_retry_retains_enemies and is_map4:
		var enemies = get_tree().get_nodes_in_group("enemies")
		BugFlags.retained_enemy_transforms.clear()
		for e in enemies:
			if is_instance_valid(e) and "global_position" in e:
				BugFlags.retained_enemy_transforms[e.name] = e.global_position
		if GameLogger and enemies.size() > 0:
			GameLogger.log_bug_trigger("4C", {
				"retained_enemies_count": enemies.size()
			})

	PlayerData.score = 0
	get_tree().paused = false
	get_tree().reload_current_scene()
