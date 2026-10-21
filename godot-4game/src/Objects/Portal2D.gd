@tool
extends Area2D

@export var next_scene: PackedScene

@onready var anim_player: AnimationPlayer = $AnimationPlayer


func _ready() -> void:
	if not Engine.is_editor_hint():
		add_to_group("portals")


func _on_body_entered(_body: PhysicsBody2D):
	teleport()


func _get_configuration_warning() -> String:
	return "The property Next Level can't be empty" if not next_scene else ""


func teleport() -> void:
	if GameLogger:
		GameLogger.log_level_cleared(global_position, next_scene.resource_path if next_scene else "")
	get_tree().paused = true
	anim_player.play("fade_out")
	await anim_player.animation_finished
	get_tree().paused = false
	get_tree().change_scene_to_packed(next_scene)
