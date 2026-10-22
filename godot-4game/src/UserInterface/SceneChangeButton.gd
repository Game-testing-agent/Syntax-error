@tool
extends Button

@export_file var next_scene_path: = ""


func _on_button_up() -> void:
	if GameLogger:
		if "MainScreen" in next_scene_path:
			GameLogger.log_action("main_menu_pressed", {"target_scene": next_scene_path})
			GameLogger.log_event("return_to_main_menu", "ui", {"target_scene": next_scene_path})
		else:
			GameLogger.log_action("scene_change_pressed", {"target_scene": next_scene_path})

	PlayerData.reset_data()
	get_tree().change_scene_to_file(next_scene_path)


func _get_configuration_warning() -> String:
	return "The property Next Level can't be empty" if next_scene_path == "" else ""
