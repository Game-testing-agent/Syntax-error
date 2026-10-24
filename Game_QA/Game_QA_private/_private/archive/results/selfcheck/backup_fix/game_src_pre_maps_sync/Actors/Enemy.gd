extends Actor

@onready var stomp_area: Area2D = $StompArea2D
@export var score: int = 100
@export var can_kill_player: bool = true
# [TEMPORARY BUG 1 TOGGLE] High-speed stomp tunneling miss
@export var bug_stomp_tunneling: bool = true

var is_dead: bool = false


func _ready() -> void:
	add_to_group("enemies")
	velocity.x = -speed.x

	if GameLogger:
		GameLogger.log_event("enemy_spawned", "enemy", {
			"position": GameLogger.vec2_to_dict(global_position),
			"speed": GameLogger.vec2_to_dict(speed),
			"score_value": score
		}, self)
		GameLogger.log_event("enemy_started_moving", "enemy", {
			"direction_x": -1.0,
			"velocity_x": velocity.x
		}, self)


func _physics_process(delta: float) -> void:
	super._physics_process(delta)

	if is_on_wall():
		var old_dir = sign(velocity.x)
		velocity.x *= -1.0
		if GameLogger:
			GameLogger.log_event("enemy_reversed_at_wall", "enemy", {
				"position": GameLogger.vec2_to_dict(global_position),
				"old_direction": old_dir,
				"new_direction": sign(velocity.x)
			}, self)

	move_and_slide()


func _on_StompArea2D_area_entered(area: Area2D) -> void:
	if GameLogger:
		GameLogger.log_event("enemy_stomp_area_entered", "enemy", {
			"stomp_area_y": stomp_area.global_position.y,
			"attacker_area_y": area.global_position.y
		}, self)

	# TRICKY BUG 1: Stomp Tunneling Miss on Fast Descent
	# When falling at high downward speed (> 500 px/s), discrete physics integration
	# causes the attacker's area to overlap deeper into the enemy hitbox.
	# Shifting the threshold causes stomps at terminal fall speeds to bypass die()
	# while the player's StompDetector still registers and bounces.
	var stomp_threshold = stomp_area.global_position.y
	if bug_stomp_tunneling:
		var attacker = area.get_parent()
		if attacker and "velocity" in attacker and attacker.velocity.y > 500.0:
			stomp_threshold -= 14.0

	if area.global_position.y > stomp_threshold:
		return
	die()


func die() -> void:
	if is_dead:
		return
	is_dead = true
	remove_from_group("enemies")

	var score_before = PlayerData.score if PlayerData else 0
	PlayerData.score += score

	if GameLogger:
		GameLogger.log_event("enemy_killed", "enemy", {
			"score_gain": score,
			"score_before": score_before,
			"score_after": PlayerData.score if PlayerData else score,
			"position": GameLogger.vec2_to_dict(global_position)
		}, self)

	queue_free()


func _exit_tree() -> void:
	if GameLogger:
		GameLogger.log_event("enemy_removed", "enemy", {
			"position": GameLogger.vec2_to_dict(global_position),
			"was_killed": is_dead
		}, self)
