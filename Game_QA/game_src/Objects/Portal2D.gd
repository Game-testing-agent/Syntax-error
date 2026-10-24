@tool
extends Area2D

@export var next_scene: PackedScene
@onready var anim_player: AnimationPlayer = $AnimationPlayer
var is_teleporting: bool = false
@export var is_map4_portal: bool = false
var portal_touch_count: int = 0
func _ready() -> void:
	if not Engine.is_editor_hint():
		add_to_group("portals")


func _on_body_entered(_body: PhysicsBody2D) -> void:
	if is_teleporting:
		return
	if GameLogger:
		GameLogger.log_event("portal_entered", "portal", {
			"position": GameLogger.vec2_to_dict(global_position),
			"target_scene": next_scene.resource_path if next_scene else ""
		}, self)

	if is_map4_portal:
		portal_touch_count += 1
		if portal_touch_count < 2:
			return

	teleport()


func _get_configuration_warning() -> String:
	return "The property Next Level can't be empty" if not next_scene else ""


func teleport() -> void:
	if is_teleporting:
		return
	is_teleporting = true

	if not next_scene or next_scene.resource_path == "":
		if GameLogger:
			GameLogger.log_event("portal_activation_failed", "portal", {
				"portal_name": name,
				"reason": "empty_target"
			}, self)
		return

	var current_scene = get_tree().current_scene if get_tree() else null
	var source_path = current_scene.scene_file_path if current_scene and current_scene.scene_file_path != "" else (current_scene.name if current_scene else "Unknown")
	var target_path = next_scene.resource_path

	if GameLogger:
		GameLogger.is_scene_transitioning = true
		GameLogger.transition_start_time_ms = Time.get_ticks_msec()
		GameLogger.log_event("portal_transition_started", "portal", {
			"source_scene": source_path,
			"target_scene": target_path
		}, self)

	# Mid-air transition handling
	var should_pause = true
	var player_nodes = get_tree().get_nodes_in_group("player")
	if player_nodes.size() > 0 and not player_nodes[0].is_on_floor() and player_nodes[0].velocity.y > 0:
		should_pause = false

	if should_pause:
		get_tree().paused = true

	if GameLogger:
		GameLogger.log_event("portal_fade_started", "portal", {
			"animation": "fade_out"
		}, self)

	anim_player.play("fade_out")
	await anim_player.animation_finished

	if should_pause:
		get_tree().paused = false

	if GameLogger:
		GameLogger.log_event("scene_change_requested", "portal", {
			"source_scene": source_path,
			"target_scene": target_path
		}, self)

		if "EndScreen" in target_path:
			GameLogger.log_event("level_completed", "portal", {
				"final_score": PlayerData.score if PlayerData else 0,
				"final_deaths": PlayerData.deaths if PlayerData else 0
			}, self)

	var err = get_tree().change_scene_to_packed(next_scene)
	if err != OK and GameLogger:
		GameLogger.log_event("scene_load_failed", "scene_lifecycle", {
			"error_code": err,
			"target_scene": target_path
		}, self)
