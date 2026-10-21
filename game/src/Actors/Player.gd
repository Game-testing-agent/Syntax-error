extends Actor


export var stomp_impulse: = 600.0


func _ready() -> void:
	add_to_group("player")
	if has_node("/root/GameLogger"):
		get_node("/root/GameLogger").register_player(self)


func _exit_tree() -> void:
	if has_node("/root/GameLogger"):
		get_node("/root/GameLogger").unregister_player(self)


func _on_StompDetector_area_entered(area: Area2D) -> void:
	_velocity = calculate_stomp_velocity(_velocity, stomp_impulse)
	if has_node("/root/GameLogger"):
		get_node("/root/GameLogger").log_player_stomp(global_position, _velocity)


func _on_EnemyDetector_body_entered(body: PhysicsBody2D) -> void:
	die()


func _physics_process(delta: float) -> void:
	var is_jump_interrupted: = Input.is_action_just_released("jump") and _velocity.y < 0.0
	var direction: = get_direction()
	_velocity = calculate_move_velocity(_velocity, direction, speed, is_jump_interrupted)
	var snap: Vector2 = Vector2.DOWN * 60.0 if direction.y == 0.0 else Vector2.ZERO
	_velocity = move_and_slide_with_snap(
		_velocity, snap, FLOOR_NORMAL, true
	)


func get_direction() -> Vector2:
	var jump_pressed = is_on_floor() and Input.is_action_just_pressed("jump")
	if jump_pressed and has_node("/root/GameLogger"):
		get_node("/root/GameLogger").log_player_jump(global_position, Vector2(_velocity.x, -speed.y))
	return Vector2(
		Input.get_action_strength("move_right") - Input.get_action_strength("move_left"),
		-Input.get_action_strength("jump") if jump_pressed else 0.0
	)


func calculate_move_velocity(
		linear_velocity: Vector2,
		direction: Vector2,
		speed: Vector2,
		is_jump_interrupted: bool
	) -> Vector2:
	var velocity: = linear_velocity
	velocity.x = speed.x * direction.x
	if direction.y != 0.0:
		velocity.y = speed.y * direction.y
	if is_jump_interrupted:
		velocity.y = 0.0
	return velocity


func calculate_stomp_velocity(linear_velocity: Vector2, stomp_impulse: float) -> Vector2:
	var stomp_jump: = -speed.y if Input.is_action_pressed("jump") else -stomp_impulse
	return Vector2(linear_velocity.x, stomp_jump)


func die() -> void:
	if has_node("/root/GameLogger"):
		get_node("/root/GameLogger").log_player_died(global_position)
	PlayerData.deaths += 1
	queue_free()
