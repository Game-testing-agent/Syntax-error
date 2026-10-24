@tool
extends Area2D

@export var next_scene: PackedScene
@onready var anim_player: AnimationPlayer = $AnimationPlayer
var is_teleporting: bool = false
@export var is_map4_portal: bool = false
var portal_touch_count: int = 0
# Unpaused physics fall during airborne portal transition
@export var bug_airborne_portal_unpause: bool = false


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

	if BugFlags and BugFlags.map4_portal_second_touch and is_map4_portal:
		portal_touch_count += 1
		if portal_touch_count < 2:
			if GameLogger:
				GameLogger.log_bug_trigger("4B", {
					"touch_count": portal_touch_count,
					"teleport_triggered": false,
					"required_touches": 2
				})
			return
		else:
			if GameLogger:
				GameLogger.log_bug_trigger("4B", {
					"touch_count": portal_touch_count,
					"teleport_triggered": true
				})

	teleport()


func _get_configuration_warning() -> String:
	return "The property Next Level can't be empty" if not next_scene else ""


func teleport() -> void:
	if is_teleporting:
		return
	is_teleporting = true

	if not next_scene or next_scene.resource_path == "":
		if GameLogger:
			GameLogger.log_anomaly("missing_expected_object", {
				"node": name,
				"missing_property": "next_scene",
				"expected": "Valid PackedScene assigned to next_scene",
				"observed": "next_scene is null or empty"
			}, "error")
			GameLogger.log_event("portal_target_missing", "portal", {
				"portal_name": name
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

	# TRICKY  5: Airborne Portal Transition Fall-Through

	# If the player touches the portal while airborne and moving downward, pausing

	# the scene tree is skipped, allowing gravity to pull the player into the pit

	# below the portal during the 0.5s fade-out sequence before the scene switch.

	var should_pause = true

	if bug_airborne_portal_unpause:

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
		GameLogger.log_anomaly("runtime_error_observed", {
			"error_code": err,
			"operation": "change_scene_to_packed",
			"target_scene": target_path,
			"expected": "Error code OK (0)",
			"observed": "Error code " + str(err)
		}, "error")
