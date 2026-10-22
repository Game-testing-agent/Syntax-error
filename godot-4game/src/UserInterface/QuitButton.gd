extends Button


func _on_button_up() -> void:
	if GameLogger:
		GameLogger.log_action("quit_pressed", {"button": name})
	get_tree().quit()
