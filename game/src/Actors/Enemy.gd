extends Actor


onready var stomp_area: Area2D = $StompArea2D

export var score: = 100


func _ready() -> void:
	add_to_group("enemies")
	set_physics_process(false)
	_velocity.x = -speed.x


func _physics_process(delta: float) -> void:
	_velocity.x *= -1 if is_on_wall() else 1
	_velocity.y = move_and_slide(_velocity, FLOOR_NORMAL).y


func _on_StompArea2D_area_entered(area: Area2D) -> void:
	if area.global_position.y > stomp_area.global_position.y:
		return
	die()


func die() -> void:
	remove_from_group("enemies")
	if has_node("/root/GameLogger"):
		get_node("/root/GameLogger").log_enemy_killed(global_position, name, score)
	PlayerData.score += score
	queue_free()
