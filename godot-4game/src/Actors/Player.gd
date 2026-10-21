extends Actor


@export var stomp_impulse: = 600.0


func _ready() -> void:
	add_to_group("player")
	if GameLogger:
		GameLogger.register_player(self)


func _exit_tree() -> void:
	if GameLogger:
		GameLogger.unregister_player(self)


func _on_StompDetector_area_entered(_area: Area2D) -> void:
	velocity = calculate_stomp_velocity(velocity, stomp_impulse)
	if GameLogger:
		GameLogger.log_player_stomp(global_position, velocity)


func _on_EnemyDetector_body_entered(_body: PhysicsBody2D) -> void:
	die()


func _physics_process(delta: float) -> void:
	super._physics_process(delta)
	var is_jump_interrupted: = Input.is_action_just_released("jump") and velocity.y < 0.0
	var direction: = get_direction()
	velocity = calculate_move_velocity(velocity, direction, speed, is_jump_interrupted)
	var snap: Vector2 = Vector2.DOWN * 60.0 if direction.y == 0.0 else Vector2.ZERO
	move_and_slide()
	set_floor_snap_length(snap.y)


func get_direction() -> Vector2:
	var jump_pressed = is_on_floor() and Input.is_action_just_pressed("jump")
	if jump_pressed and GameLogger:
		GameLogger.log_player_jump(global_position, Vector2(velocity.x, -speed.y))
	return Vector2(
		Input.get_action_strength("move_right") - Input.get_action_strength("move_left"),
		-Input.get_action_strength("jump") if jump_pressed else 0.0
	)


func calculate_move_velocity(
		linear_velocity: Vector2,
		direction: Vector2,
		_speed: Vector2,
		is_jump_interrupted: bool
	) -> Vector2:
	var _velocity: = linear_velocity
	_velocity.x = _speed.x * direction.x
	if direction.y != 0.0:
		_velocity.y = _speed.y * direction.y
	if is_jump_interrupted:
		_velocity.y = 0.0
	return _velocity


func calculate_stomp_velocity(linear_velocity: Vector2, impulse: float) -> Vector2:
	var stomp_jump: = -speed.y if Input.is_action_pressed("jump") else -impulse
	return Vector2(linear_velocity.x, stomp_jump)


func die() -> void:
	if GameLogger:
		GameLogger.log_player_died(global_position)
	PlayerData.deaths += 1
	queue_free()
