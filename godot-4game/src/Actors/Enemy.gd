extends Actor


@onready var stomp_area: Area2D = $StompArea2D

@export var score: = 100


func _ready() -> void:
	add_to_group("enemies")
	velocity.x = -speed.x


func _physics_process(delta: float) -> void:
	super._physics_process(delta)
	
	velocity.x *= -1 if is_on_wall() else 1
	move_and_slide()


func _on_StompArea2D_area_entered(area: Area2D) -> void:
	if area.global_position.y > stomp_area.global_position.y:
		return
	die()


func die() -> void:
	remove_from_group("enemies")
	if GameLogger:
		GameLogger.log_enemy_killed(global_position, name, score)
	PlayerData.score += score
	queue_free()
