extends Actor

@export var stomp_impulse: float = 600.0
@export var is_invincible: bool = false  # TEMPORARY: God mode (set to false to re-enable death)
# Wall-friction jump dampening
@export var bug_wall_friction_jump: bool = true

const MOVE_SAMPLE_DIST_THRESHOLD: float = 100.0
const MOVE_SAMPLE_FRAME_INTERVAL: int = 30
const FALL_DISTANCE_THRESHOLD: float = 400.0
const OUT_OF_BOUNDS_Y: float = 1400.0

var was_on_floor: bool = false
var is_jumping: bool = false
var is_falling: bool = false
var jump_start_pos: Vector2 = Vector2.ZERO
var fall_start_pos: Vector2 = Vector2.ZERO
var peak_jump_y: float = INF
var fall_threshold_logged: bool = false
var out_of_bounds_logged: bool = false
var is_wall_stuck: bool = false
var is_stair_stuck: bool = false
var stair_escape_count: int = 0
var tower_wall_jump_active: bool = false
var lava_timer: float = -1.0
var last_move_log_pos: Vector2 = Vector2.ZERO
var last_move_log_frame: int = 0


func _ready() -> void:
	add_to_group("player")
	was_on_floor = is_on_floor()
	last_move_log_pos = global_position
	last_move_log_frame = Engine.get_physics_frames()

	if GameLogger:
		GameLogger.register_player(self)
		GameLogger.log_event("player_spawned", "player_lifecycle", {
			"position": GameLogger.vec2_to_dict(global_position),
			"speed": GameLogger.vec2_to_dict(speed),
			"stomp_impulse": stomp_impulse
		})


func _exit_tree() -> void:
	if GameLogger:
		GameLogger.log_event("player_removed", "player_lifecycle", {
			"position": GameLogger.vec2_to_dict(global_position)
		})
		if not GameLogger.is_shutting_down and not GameLogger.expected_player_death and not GameLogger.is_scene_transitioning:
			GameLogger.log_anomaly("unexpected_player_removal", {
				"position": GameLogger.vec2_to_dict(global_position),
				"expected": "Player removal should occur on death or scene transition",
				"observed": "Player exited scene tree without death flag or transition"
			}, "error")
		GameLogger.expected_player_death = false
		GameLogger.unregister_player(self)


func _on_StompDetector_area_entered(area: Area2D) -> void:
	var enemy = area.get_parent()
	if GameLogger:
		GameLogger.log_event("stomp_attempted", "enemy", {
			"area_name": area.name,
			"player_position": GameLogger.vec2_to_dict(global_position),
			"enemy_position": GameLogger.vec2_to_dict(enemy.global_position) if enemy and "global_position" in enemy else null,
			"player_velocity_y": velocity.y
		}, enemy if enemy is Node else null)

	velocity = calculate_stomp_velocity(velocity, stomp_impulse)

	if GameLogger:
		GameLogger.log_event("enemy_stomped", "enemy", {
			"bounce_velocity": GameLogger.vec2_to_dict(velocity),
			"stomp_impulse": stomp_impulse
		}, enemy if enemy is Node else null)


func _on_EnemyDetector_body_entered(body: PhysicsBody2D) -> void:
	if is_invincible:
		return
	if BugFlags and BugFlags.map1_enemy4_no_kill:
		if body.name == "Enemy4" or body.get_index() == 3 or ("can_kill_player" in body and not body.can_kill_player):
			if GameLogger:
				GameLogger.log_bug_trigger("1A", {
					"enemy_name": body.name,
					"player_position": GameLogger.vec2_to_dict(global_position),
					"enemy_position": GameLogger.vec2_to_dict(body.global_position) if "global_position" in body else null
				})
			return
	if GameLogger:
		GameLogger.log_event("enemy_contact_started", "enemy", {
			"contact_type": "body",
			"player_position": GameLogger.vec2_to_dict(global_position),
			"enemy_position": GameLogger.vec2_to_dict(body.global_position) if "global_position" in body else null
		}, body)
		GameLogger.log_event("enemy_contact_death", "enemy", {
			"enemy_name": body.name,
			"score": PlayerData.score if PlayerData else 0,
			"deaths": PlayerData.deaths if PlayerData else 0
		}, body)
	die()


func trigger_lava_contact() -> void:
	if is_invincible:
		return
	if BugFlags and BugFlags.map4_delayed_lava_death:
		if lava_timer < 0.0:
			lava_timer = 3.0
			if GameLogger:
				GameLogger.log_bug_trigger("4A", {
					"delay_seconds": 3.0,
					"position": GameLogger.vec2_to_dict(global_position)
				})
		return
	die()


func _physics_process(delta: float) -> void:
	if lava_timer > 0.0:
		lava_timer -= delta
		if lava_timer <= 0.0:
			lava_timer = -1.0
			die()

	if BugFlags and BugFlags.map2_wall_stuck:
		if not is_wall_stuck and global_position.x >= 4360.0 and global_position.x <= 4440.0 and global_position.y >= 600.0 and global_position.y <= 680.0:
			is_wall_stuck = true
			if GameLogger:
				GameLogger.log_bug_trigger("2A", {
					"tile_coords": [55, 8],
					"position": GameLogger.vec2_to_dict(global_position),
					"stuck": true
				})
		if is_wall_stuck:
			velocity = Vector2.ZERO
			move_and_slide()
			return

	if BugFlags and BugFlags.map3_stair_stick:
		if not is_stair_stuck and is_on_floor() and global_position.x >= 5420.0 and global_position.x <= 5460.0 and global_position.y >= 540.0 and global_position.y <= 580.0:
			is_stair_stuck = true
			stair_escape_count = 0
			if GameLogger:
				GameLogger.log_bug_trigger("3A", {
					"stair_coords": [68, 7],
					"escape_presses_needed": 3,
					"position": GameLogger.vec2_to_dict(global_position)
				})
		if is_stair_stuck:
			if Input.is_action_just_pressed("move_left"):
				stair_escape_count += 1
				if stair_escape_count >= 3:
					is_stair_stuck = false
			if is_stair_stuck:
				velocity = Vector2.ZERO
				move_and_slide()
				return

	super._physics_process(delta)

	var is_jump_interrupted: bool = Input.is_action_just_released("jump") and velocity.y < 0.0
	if is_jump_interrupted and GameLogger:
		GameLogger.log_event("jump_interrupted", "player_movement", {
			"position": GameLogger.vec2_to_dict(global_position),
			"velocity_before": GameLogger.vec2_to_dict(velocity)
		})

	var direction: = get_direction()
	velocity = calculate_move_velocity(velocity, direction, speed, is_jump_interrupted)
	var snap: Vector2 = Vector2.DOWN * 60.0 if direction.y == 0.0 else Vector2.ZERO
	move_and_slide()
	set_floor_snap_length(snap.y)

	# Track peak jump height
	if velocity.y < 0.0 and global_position.y < peak_jump_y:
		peak_jump_y = global_position.y

	# Detect floor state transitions (landing and leaving floor)
	var current_on_floor = is_on_floor()

	if not was_on_floor and current_on_floor:
		# Player landed on floor
		var fall_dist = round((global_position.y - peak_jump_y) * 10.0) / 10.0 if peak_jump_y != INF else 0.0
		var horiz_disp = round(abs(global_position.x - jump_start_pos.x) * 10.0) / 10.0 if is_jumping else 0.0
		if GameLogger:
			GameLogger.log_event("player_landed", "player_movement", {
				"position": GameLogger.vec2_to_dict(global_position),
				"fall_distance": max(0.0, fall_dist),
				"horizontal_displacement": horiz_disp,
				"was_jumping": is_jumping
			})
		is_jumping = false
		is_falling = false
		fall_threshold_logged = false
		peak_jump_y = INF
	elif was_on_floor and not current_on_floor:
		# Player left floor without jumping
		if not is_jumping and GameLogger:
			GameLogger.log_event("player_left_floor", "player_movement", {
				"position": GameLogger.vec2_to_dict(global_position),
				"velocity": GameLogger.vec2_to_dict(velocity)
			})

	# Detect falling phase
	if not current_on_floor and velocity.y > 0.0:
		if not is_falling:
			is_falling = true
			fall_start_pos = global_position
			if peak_jump_y == INF:
				peak_jump_y = global_position.y
			if GameLogger:
				GameLogger.log_event("fall_started", "player_movement", {
					"start_position": GameLogger.vec2_to_dict(fall_start_pos),
					"velocity": GameLogger.vec2_to_dict(velocity)
				})
		else:
			var cur_fall_dist = global_position.y - fall_start_pos.y
			if cur_fall_dist >= FALL_DISTANCE_THRESHOLD and not fall_threshold_logged:
				fall_threshold_logged = true
				if GameLogger:
					GameLogger.log_event("fall_distance_threshold_reached", "player_movement", {
						"fall_distance": round(cur_fall_dist * 10.0) / 10.0,
						"threshold": FALL_DISTANCE_THRESHOLD,
						"position": GameLogger.vec2_to_dict(global_position)
					})

	# Rate-limited / threshold-based movement sampling
	var dist_moved = global_position.distance_to(last_move_log_pos)
	var current_frame = Engine.get_physics_frames()
	if dist_moved >= MOVE_SAMPLE_DIST_THRESHOLD or (dist_moved >= 25.0 and current_frame - last_move_log_frame >= MOVE_SAMPLE_FRAME_INTERVAL):
		if GameLogger:
			GameLogger.log_event("player_moved", "player_movement", {
				"from_position": GameLogger.vec2_to_dict(last_move_log_pos),
				"to_position": GameLogger.vec2_to_dict(global_position),
				"velocity": GameLogger.vec2_to_dict(velocity),
				"distance": round(dist_moved * 10.0) / 10.0
			})
		last_move_log_pos = global_position
		last_move_log_frame = current_frame

	# Out of bounds anomaly detection
	if global_position.y > OUT_OF_BOUNDS_Y and not out_of_bounds_logged and GameLogger:
		out_of_bounds_logged = true
		if BugFlags and BugFlags.map1_floor_hole:
			GameLogger.log_bug_trigger("1B", {
				"position": GameLogger.vec2_to_dict(global_position),
				"threshold_y": OUT_OF_BOUNDS_Y
			})
		GameLogger.log_anomaly("player_out_of_bounds", {
			"position": GameLogger.vec2_to_dict(global_position),
			"threshold_y": OUT_OF_BOUNDS_Y,
			"expected": "Player position Y <= " + str(OUT_OF_BOUNDS_Y),
			"observed": "Player position Y exceeded limit: " + str(round(global_position.y * 10.0) / 10.0)
		}, "error")

	was_on_floor = current_on_floor


func get_direction() -> Vector2:
	var jump_pressed = is_on_floor() and Input.is_action_just_pressed("jump")
	tower_wall_jump_active = false
	if BugFlags and BugFlags.map3_tower_wall_jump and is_on_wall() and Input.is_action_just_pressed("jump"):
		if global_position.x >= 15550.0 and global_position.x <= 15650.0:
			jump_pressed = true
			tower_wall_jump_active = true
			if GameLogger:
				GameLogger.log_bug_trigger("3C", {
					"wall_coords": [195, 8],
					"jump_multiplier": 2.0,
					"position": GameLogger.vec2_to_dict(global_position)
				})
	if jump_pressed:
		is_jumping = true
		is_falling = false
		jump_start_pos = global_position
		peak_jump_y = global_position.y
		fall_threshold_logged = false
		if GameLogger:
			GameLogger.log_event("jump_started", "player_movement", {
				"start_position": GameLogger.vec2_to_dict(global_position),
				"initial_velocity": GameLogger.vec2_to_dict(Vector2(velocity.x, -speed.y)),
				"speed": GameLogger.vec2_to_dict(speed)
			})

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
		var mult = 2.0 if tower_wall_jump_active else 1.0
		_velocity.y = _speed.y * direction.y * mult
	if is_jump_interrupted:
		_velocity.y = 0.0
	elif bug_wall_friction_jump and is_on_wall() and _velocity.y < -50.0 and direction.x != 0.0:
		# TRICKY  2: Wall-Friction Jump Dampening
		# Pressing towards a wall during ascent dampens upward impulse by 35%,
		# subtly stunting jump height only when wall-scraping.
		_velocity.y *= 0.65
	return _velocity


func calculate_stomp_velocity(linear_velocity: Vector2, impulse: float) -> Vector2:
	var stomp_jump: = -speed.y if Input.is_action_pressed("jump") else -impulse
	return Vector2(linear_velocity.x, stomp_jump)


func die(force: bool = false) -> void:
	if is_invincible and not force:
		return
	if GameLogger:
		GameLogger.expected_player_death = true
		GameLogger.log_event("player_died", "player_lifecycle", {
			"position": GameLogger.vec2_to_dict(global_position),
			"score_at_death": PlayerData.score if PlayerData else 0,
			"total_deaths_before": PlayerData.deaths if PlayerData else 0
		})
	PlayerData.deaths += 1
	queue_free()
