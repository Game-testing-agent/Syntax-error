extends Node

## GameLogger - Structured JSON Event & State Logger for AI Game Tester Agent
##
## Centralized telemetry foundation for:
##  - Structured JSON Lines logging (game_events.jsonl)
##  - Real-time atomic state snapshots (latest_state.json)
##  - Anomaly detection, input tracing, and physics state reconstruction

@export var enable_logging: bool = true
@export var enable_snapshots: bool = true
@export var snapshot_interval_frames: int = 60 # ~1 second at 60 FPS
@export var state_export_interval_frames: int = 4 # ~15 Hz at 60 FPS for latest_state.json
@export var max_recent_actions: int = 20

const SCHEMA_VERSION: String = "1.0"

# Session & Monotonic Counter
var session_id: String = ""
var session_start_unix_ms: int = 0
var session_start_ticks: int = 0
var event_id: int = 0
var frame_count: int = 0

# Paths & File Output
var output_dirs: Array[String] = []
var log_file_paths: Array[String] = []
var custom_log_dir: String = ""
var human_log_path: String = ""

# State Tracking & Entities
var active_player: CharacterBody2D = null
var recent_actions: Array[Dictionary] = []
var last_scene_path: String = ""
var last_scene_name: String = ""
var is_shutting_down: bool = false
var is_scene_transitioning: bool = false
var transition_start_time_ms: int = 0
var expected_player_death: bool = false

# Stuck Detection Tracking
var stuck_input_name: String = ""
var stuck_frames: int = 0
var stuck_check_pos: Vector2 = Vector2.ZERO

# Recursion Guard
var is_logging_internal: bool = false

# Agent Control Server (UDP & Command File IPC)
@export var enable_agent_control: bool = true
@export var agent_udp_port: int = 4242
var _agent_udp: PacketPeerUDP = null
var _currently_pressed_agent_actions: Array[String] = []


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS # Keep logging even when game is paused!
	session_start_ticks = Time.get_ticks_msec()
	session_start_unix_ms = int(Time.get_unix_time_from_system() * 1000.0)
	session_id = "session_%d_%d" % [int(Time.get_unix_time_from_system()), randi() % 90000 + 10000]

	_setup_output_paths()

	if enable_agent_control:
		_setup_agent_server()

	# Connect PlayerData signals if available
	if PlayerData:
		PlayerData.updated.connect(_on_player_data_updated)
		PlayerData.died.connect(_on_player_died)
		PlayerData.reset.connect(_on_player_reset)

	# Emit initial session_start lifecycle event
	log_lifecycle("session_start", {
		"project_name": ProjectSettings.get_setting("application/config/name", "2D Platformer"),
		"godot_version": Engine.get_version_info()["string"],
		"os": OS.get_name(),
		"log_destinations": log_file_paths,
		"schema_version": SCHEMA_VERSION
	})


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_PREDELETE:
		is_shutting_down = true
		_release_all_agent_actions()
		if _agent_udp:
			_agent_udp.close()
		if enable_logging and session_id != "":
			log_lifecycle("session_end", {
				"total_events": event_id,
				"session_duration_ms": Time.get_ticks_msec() - session_start_ticks
			})
			generate_coverage_report()  # Auto-generate on clean shutdown


func _setup_output_paths() -> void:
	output_dirs.clear()
	log_file_paths.clear()

	# Check for --log-dir CLI argument
	var user_args = OS.get_cmdline_user_args()
	for i in range(user_args.size()):
		var arg = user_args[i]
		if arg.begins_with("--log-dir="):
			custom_log_dir = arg.substr(10).strip_edges().trim_prefix('\"').trim_suffix('\"')
		elif arg == "--log-dir" and i + 1 < user_args.size():
			custom_log_dir = user_args[i + 1].strip_edges().trim_prefix('\"').trim_suffix('\"')

	if custom_log_dir != "":
		if not custom_log_dir.is_absolute_path():
			var base_dir = ProjectSettings.globalize_path("res://..")
			custom_log_dir = base_dir.path_join(custom_log_dir)
		if not DirAccess.dir_exists_absolute(custom_log_dir):
			DirAccess.make_dir_recursive_absolute(custom_log_dir)
		output_dirs.append(custom_log_dir)
		log_file_paths.append(custom_log_dir.path_join("game_events.jsonl"))

		var dt = Time.get_datetime_dict_from_system()
		var ts = "%04d%02d%02d_%02d%02d%02d" % [dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second]
		human_log_path = custom_log_dir.path_join("run_%s.log" % ts)
		_write_human_log("=== RUN LOG STARTED [%s] ===" % ts)

		# Also write directly to root workspace (Syntax-error/) for global log consolidation
		var parent_dir = ProjectSettings.globalize_path("res://..")
		if parent_dir != "" and not output_dirs.has(parent_dir):
			output_dirs.append(parent_dir)
			log_file_paths.append(parent_dir.path_join("game_events.jsonl"))
			log_file_paths.append(parent_dir.path_join("game-events.jsonl"))
		return

	# 1. Primary writable Godot user-data directory (user://)
	var user_dir = OS.get_user_data_dir()
	if user_dir != "":
		if not DirAccess.dir_exists_absolute(user_dir):
			DirAccess.make_dir_recursive_absolute(user_dir)
		output_dirs.append(user_dir)

	# 2. Project directory (res://)
	var res_dir = ProjectSettings.globalize_path("res://")
	if res_dir != "":
		if not output_dirs.has(res_dir):
			output_dirs.append(res_dir)

	# 3. Parent workspace directory (e.g. Syntax-error/)
	var parent_dir = ProjectSettings.globalize_path("res://..")
	if parent_dir != "" and not output_dirs.has(parent_dir):
		output_dirs.append(parent_dir)

	for dir in output_dirs:
		log_file_paths.append(dir.path_join("game_events.jsonl"))
		if dir == parent_dir:
			log_file_paths.append(dir.path_join("game-events.jsonl"))


func get_log_paths() -> Array[String]:
	return log_file_paths.duplicate()


# ==============================================================================
# INPUT HANDLING (Passive Observer)
# ==============================================================================

func _input(event: InputEvent) -> void:
	if not enable_logging:
		return

	var tracked_actions = ["move_left", "move_right", "jump", "pause"]
	for action in tracked_actions:
		if event.is_action(action) and not event.is_echo():
			if event.is_pressed():
				log_action(action + "_pressed", {
					"action": action,
					"pressed": true,
					"strength": Input.get_action_strength(action)
				})
			elif event.is_released():
				log_action(action + "_released", {
					"action": action,
					"pressed": false
				})


# ==============================================================================
# PROCESS & PHYSICS UPDATE (Periodic Snapshots, Scene Tracking, Anomaly Checks)
# ==============================================================================

func _process(_delta: float) -> void:
	if enable_agent_control:
		_poll_agent_commands()

	if not enable_logging:
		return

	frame_count += 1

	var tree = get_tree() if is_inside_tree() else null

	# Scene lifecycle monitoring
	var current_scene = tree.current_scene if tree else null
	if current_scene:
		var scene_path = current_scene.scene_file_path if current_scene.scene_file_path != "" else current_scene.name
		if scene_path != last_scene_path:
			var prev_path = last_scene_path
			last_scene_path = scene_path
			last_scene_name = current_scene.name
			is_scene_transitioning = false

			log_lifecycle("scene_loaded", {
				"scene": scene_path,
				"previous_scene": prev_path
			})

			if "MainScreen" in scene_path or scene_path == "MainScreen":
				log_lifecycle("main_screen_loaded", {"scene": scene_path})
			elif "Level01" in scene_path or "Level02" in scene_path or "Level" in scene_path:
				log_lifecycle("level_loaded", {"scene": scene_path})
			elif "EndScreen" in scene_path or scene_path == "EndScreen":
				log_lifecycle("end_screen_loaded", {"scene": scene_path})

	# Scene transition timeout detection
	if is_scene_transitioning:
		if Time.get_ticks_msec() - transition_start_time_ms > 5000:
			is_scene_transitioning = false
			log_anomaly("scene_transition_timeout", {
				"elapsed_ms": Time.get_ticks_msec() - transition_start_time_ms,
				"expected": "Scene should load within 5000ms",
				"observed": "Scene transition timed out"
			}, "error")

	# Periodic real-time state polling export for agents (latest_state.json)
	if frame_count % state_export_interval_frames == 0:
		var full_state = extract_game_state()
		_write_latest_state(full_state)


func _physics_process(_delta: float) -> void:
	if not enable_logging:
		return

	var phys_frame = Engine.get_physics_frames()

	# Periodic structured state snapshot in JSONL
	if enable_snapshots and phys_frame > 0 and phys_frame % snapshot_interval_frames == 0:
		log_state_snapshot()

	# Stuck player anomaly detection (sustained movement input with near-zero displacement)
	_check_player_stuck()


func _check_player_stuck() -> void:
	if not active_player or not is_instance_valid(active_player) or not active_player.is_inside_tree():
		stuck_frames = 0
		return

	var tree = get_tree() if is_inside_tree() else null
	if tree and tree.paused:
		stuck_frames = 0
		return

	var moving_left = Input.is_action_pressed("move_left")
	var moving_right = Input.is_action_pressed("move_right")
	var is_trying_to_move = moving_left or moving_right

	# Only check if player is grounded and not pressing into a normal obstacle wall
	if is_trying_to_move and active_player.is_on_floor() and not active_player.is_on_wall():
		if stuck_frames == 0:
			stuck_check_pos = active_player.global_position
			stuck_input_name = "move_right" if moving_right else "move_left"
		stuck_frames += 1

		if stuck_frames >= 60: # 60 frames = 1.0 second of sustained movement input
			var displacement = active_player.global_position.distance_to(stuck_check_pos)
			if displacement < 8.0:
				log_anomaly("player_stuck_detected", {
					"held_input": stuck_input_name,
					"held_frames": stuck_frames,
					"displacement": round(displacement * 10.0) / 10.0,
					"position": vec2_to_dict(active_player.global_position),
					"expected": "Player should move horizontally when " + stuck_input_name + " is held and unobstructed",
					"observed": "Player remained stationary (displacement < 8px)"
				}, "warning")
			stuck_check_pos = active_player.global_position
			stuck_frames = 0
	else:
		stuck_frames = 0


# ==============================================================================
# CORE LOGGING OPERATIONS
# ==============================================================================

## Standard event logging operation adhering to Schema 1.0
func log_event(event_name: String, category: String, data: Dictionary = {}, entity: Node = null) -> Dictionary:
	if not enable_logging or is_logging_internal:
		return {}

	is_logging_internal = true
	var record = _build_record(event_name, category, data, entity)
	_write_record(record)
	is_logging_internal = false
	return record


## Periodic state snapshot operation
func log_state_snapshot() -> Dictionary:
	var snapshot_data = extract_game_state("state_snapshot")
	return log_event("state_snapshot", "state_snapshot", snapshot_data)


## Lightweight rule-based anomaly logging operation
func log_anomaly(anomaly_type: String, data: Dictionary = {}, severity: String = "warning") -> Dictionary:
	var anomaly_payload = {
		"anomaly_type": anomaly_type,
		"severity": severity,
		"expected": data.get("expected", null),
		"observed": data.get("observed", null),
		"details": data
	}
	return log_event(anomaly_type, "anomaly", anomaly_payload)


## Input and UI action logging operation
func log_action(action_name: String, data: Dictionary = {}) -> Dictionary:
	var action_entry = {
		"action": action_name,
		"physics_frame": Engine.get_physics_frames(),
		"timestamp_unix_ms": int(Time.get_unix_time_from_system() * 1000.0)
	}
	recent_actions.append(action_entry)
	if recent_actions.size() > max_recent_actions:
		recent_actions.pop_front()

	return log_event(action_name, "input", data)


## Scene and session lifecycle logging operation
func log_lifecycle(event_name: String, data: Dictionary = {}) -> Dictionary:
	return log_event(event_name, "scene_lifecycle", data)


# ==============================================================================
# SCHEMA BUILDER & RECORD SERIALIZATION
# ==============================================================================

func _build_record(event_name: String, category: String, data: Dictionary, entity: Node) -> Dictionary:
	event_id += 1
	_track_event(event_name)  # Coverage tracking
	var now_unix_ms = int(Time.get_unix_time_from_system() * 1000.0)
	var elapsed_ms = Time.get_ticks_msec() - session_start_ticks
	var phys_frame = Engine.get_physics_frames()

	var tree = get_tree() if is_inside_tree() else null
	var current_scene = tree.current_scene if tree else null
	var scene_path: String = ""
	if current_scene:
		scene_path = current_scene.scene_file_path if current_scene.scene_file_path != "" else current_scene.name

	# Player state (null if player is dead or does not exist)
	var player_dict = null
	if active_player and is_instance_valid(active_player) and active_player.is_inside_tree():
		player_dict = {
			"instance_id": int(active_player.get_instance_id()),
			"position": vec2_to_dict(active_player.global_position),
			"velocity": vec2_to_dict(active_player.velocity),
			"grounded": active_player.is_on_floor()
		}

	# Game state
	var game_state_dict = {
		"score": PlayerData.score if PlayerData else 0,
		"deaths": PlayerData.deaths if PlayerData else 0,
		"paused": tree.paused if tree else false
	}

	# Entity context
	var entity_dict = null
	if entity and is_instance_valid(entity):
		var ent_type = entity.get_class()
		if entity.get_script() != null:
			var global_script_name = entity.get_script().get_global_name()
			if global_script_name != "":
				ent_type = global_script_name
			elif "Enemy" in entity.name:
				ent_type = "Enemy"
			elif "Coin" in entity.name:
				ent_type = "Coin"
			elif "Portal" in entity.name:
				ent_type = "Portal2D"

		entity_dict = {
			"instance_id": int(entity.get_instance_id()),
			"name": entity.name,
			"type": ent_type,
			"position": vec2_to_dict(entity.global_position) if "global_position" in entity else null
		}

	# Complete standard schema record
	var record = {
		"schema_version": SCHEMA_VERSION,
		"session_id": session_id,
		"event_id": event_id,
		"event_name": event_name,
		"category": category,
		"timestamp_unix_ms": now_unix_ms,
		"elapsed_ms": elapsed_ms,
		"physics_frame": phys_frame,
		"scene": scene_path,
		"player": player_dict,
		"game_state": game_state_dict,
		"entity": entity_dict,
		"action_context": {
			"recent_actions": recent_actions.duplicate()
		},
		"evidence": {
			"screenshot_path": null # Kept null as optional per configuration
		},
		"data": data
	}

	return record


func _write_human_log(line: String) -> void:
	if human_log_path == "":
		return
	var file = FileAccess.open(human_log_path, FileAccess.READ_WRITE)
	if not file:
		file = FileAccess.open(human_log_path, FileAccess.WRITE)
	else:
		file.seek_end()
	if file:
		file.store_line(line)
		file.flush()
		file.close()




func _write_record(record: Dictionary) -> void:
	if human_log_path != "":
		var line = "[%06d] [%-16s] %s %s" % [
			record.get("physics_frame", 0),
			record.get("category", ""),
			record.get("event_name", ""),
			JSON.stringify(record.get("data", {}))
		]
		_write_human_log(line)
	var json_line = JSON.stringify(record)
	var write_failed = false

	var targets: Array[String] = []
	for dir in output_dirs:
		targets.append(dir.path_join("game_events.jsonl"))
		var parent_dir = ProjectSettings.globalize_path("res://..")
		if dir == parent_dir:
			targets.append(dir.path_join("game-events.jsonl"))

	for target_path in targets:
		var file = FileAccess.open(target_path, FileAccess.READ_WRITE)
		if not file:
			file = FileAccess.open(target_path, FileAccess.WRITE)
		else:
			file.seek_end()

		if file:
			file.store_line(json_line)
			file.flush()
			file.close()
		else:
			write_failed = true

	if write_failed and not is_logging_internal:
		push_warning("[GameLogger] Failed to write event line to one or more output paths.")


# ==============================================================================
# PLAYER REGISTRATION & COMPATIBILITY HELPERS
# ==============================================================================

func register_player(player: CharacterBody2D) -> void:
	active_player = player


func unregister_player(player: CharacterBody2D) -> void:
	if active_player == player:
		active_player = null


func log_player_jump(pos: Vector2, vel: Vector2) -> void:
	log_event("jump_started", "player_movement", {
		"start_position": vec2_to_dict(pos),
		"initial_velocity": vec2_to_dict(vel)
	})


func log_player_stomp(pos: Vector2, bounce_vel: Vector2) -> void:
	log_event("enemy_stomped", "enemy", {
		"position": vec2_to_dict(pos),
		"bounce_velocity": vec2_to_dict(bounce_vel)
	})


func log_player_died(pos: Vector2) -> void:
	log_event("player_died", "player_lifecycle", {
		"position": vec2_to_dict(pos),
		"score_at_death": PlayerData.score if PlayerData else 0,
		"total_deaths_before": PlayerData.deaths if PlayerData else 0
	})


func log_enemy_killed(pos: Vector2, enemy_name: String, score_gain: int) -> void:
	log_event("enemy_killed", "enemy", {
		"enemy_name": enemy_name,
		"position": vec2_to_dict(pos),
		"score_gain": score_gain,
		"score_after": PlayerData.score + score_gain if PlayerData else score_gain
	})


func log_coin_collected(pos: Vector2, score_gain: int) -> void:
	log_event("coin_picked", "collectible", {
		"position": vec2_to_dict(pos),
		"score_gain": score_gain
	})


func log_level_cleared(pos: Vector2, next_scene_path: String) -> void:
	log_event("level_completed", "portal", {
		"portal_position": vec2_to_dict(pos),
		"next_scene": next_scene_path
	})


# ==============================================================================
# PLAYER DATA SIGNALS
# ==============================================================================

func _on_player_data_updated() -> void:
	pass


func _on_player_died() -> void:
	_release_all_agent_actions()


func _on_player_reset() -> void:
	pass


# ==============================================================================
# STATE EXTRACTION FOR AGENTS & SNAPSHOTS
# ==============================================================================

func extract_game_state(current_event: String = "") -> Dictionary:
	var tree = get_tree() if is_inside_tree() else null
	var current_scene = tree.current_scene if tree else null
	var scene_name = current_scene.name if current_scene else "Unknown"

	# Determine current game state string
	var state_str = "playing"
	if scene_name == "MainScreen":
		state_str = "main_menu"
	elif scene_name == "EndScreen":
		state_str = "victory"
	elif tree and tree.paused:
		if active_player == null:
			state_str = "player_died"
		else:
			state_str = "paused"
	elif active_player == null and (scene_name == "Level01" or scene_name == "Level02"):
		state_str = "player_died"

	# Resolve Player
	var player = active_player
	if player == null and is_instance_valid(current_scene):
		player = current_scene.get_node_or_null("Player") as CharacterBody2D
		if player == null and tree:
			var players = tree.get_nodes_in_group("player")
			if players.size() > 0 and is_instance_valid(players[0]):
				player = players[0] as CharacterBody2D

	var player_data: Dictionary = {
		"alive": player != null and is_instance_valid(player)
	}

	var player_pos = Vector2.ZERO
	if player_data["alive"]:
		player_pos = player.global_position
		player_data["position"] = vec2_to_dict(player.global_position)
		player_data["velocity"] = vec2_to_dict(player.velocity)
		player_data["on_floor"] = player.is_on_floor()
		player_data["on_wall"] = player.is_on_wall()
		player_data["on_ceiling"] = player.is_on_ceiling()
		player_data["facing"] = 1 if player.velocity.x >= 0 else -1
		player_data["stomp_impulse"] = player.stomp_impulse if "stomp_impulse" in player else 1600.0
		player_data["speed_max"] = {
			"x": player.speed.x if "speed" in player else 700.0,
			"y": player.speed.y if "speed" in player else 1350.0
		}
		player_data["hitbox"] = {"width": 80.0, "height": 82.0}

		# Raycast perception (floor distance & wall distance)
		var perception = _get_player_perception(player)
		player_data["distance_to_ground"] = perception["distance_to_ground"]
		player_data["distance_to_wall_ahead"] = perception["distance_to_wall_ahead"]

	# Inputs
	var inputs_data = {
		"move_left": Input.is_action_pressed("move_left"),
		"move_right": Input.is_action_pressed("move_right"),
		"jump": Input.is_action_pressed("jump"),
		"jump_just_pressed": Input.is_action_just_pressed("jump"),
		"pause": Input.is_action_pressed("pause"),
		"raw_direction": {
			"x": Input.get_action_strength("move_right") - Input.get_action_strength("move_left"),
			"y": -Input.get_action_strength("jump") if Input.is_action_just_pressed("jump") else 0.0
		}
	}

	# Collectibles (Coins)
	var coins_data: Array[Dictionary] = []
	var coin_nodes = tree.get_nodes_in_group("coins") if tree else []
	for coin in coin_nodes:
		if is_instance_valid(coin) and coin.is_inside_tree():
			var c_pos = coin.global_position
			var dist = round(player_pos.distance_to(c_pos) * 10.0) / 10.0 if player_data["alive"] else 0.0
			coins_data.append({
				"id": int(coin.get_instance_id()),
				"x": round(c_pos.x * 10.0) / 10.0,
				"y": round(c_pos.y * 10.0) / 10.0,
				"distance": dist,
				"relative_x": round((c_pos.x - player_pos.x) * 10.0) / 10.0 if player_data["alive"] else 0.0,
				"relative_y": round((c_pos.y - player_pos.y) * 10.0) / 10.0 if player_data["alive"] else 0.0
			})

	if player_data["alive"]:
		coins_data.sort_custom(func(a, b): return a["distance"] < b["distance"])

	var nearest_coin = coins_data[0] if coins_data.size() > 0 else null

	# Enemies
	var enemies_data: Array[Dictionary] = []
	var enemy_nodes = tree.get_nodes_in_group("enemies") if tree else []
	for enemy in enemy_nodes:
		if is_instance_valid(enemy) and enemy.is_inside_tree():
			var e_pos = enemy.global_position
			var dist = round(player_pos.distance_to(e_pos) * 10.0) / 10.0 if player_data["alive"] else 0.0
			var dx = round((e_pos.x - player_pos.x) * 10.0) / 10.0 if player_data["alive"] else 0.0
			var dy = round((e_pos.y - player_pos.y) * 10.0) / 10.0 if player_data["alive"] else 0.0
			var is_above = (player_pos.y < (e_pos.y - 20.0)) if player_data["alive"] else false
			var vel_x = enemy.velocity.x if "velocity" in enemy else 0.0
			enemies_data.append({
				"id": int(enemy.get_instance_id()),
				"name": enemy.name,
				"x": round(e_pos.x * 10.0) / 10.0,
				"y": round(e_pos.y * 10.0) / 10.0,
				"vel_x": round(vel_x * 10.0) / 10.0,
				"distance": dist,
				"relative_x": dx,
				"relative_y": dy,
				"player_is_above": is_above,
				"is_stompable": is_above and player_data["alive"] and player.velocity.y > 0,
				"is_threat": dist < 450.0 and not is_above and player_data["alive"]
			})

	if player_data["alive"]:
		enemies_data.sort_custom(func(a, b): return a["distance"] < b["distance"])

	var closest_enemy = enemies_data[0] if enemies_data.size() > 0 else null

	# Goal / Portal2D
	var goal_data = {
		"found": false,
		"portal_x": 0.0,
		"portal_y": 0.0,
		"distance_to_portal": 0.0,
		"relative_x": 0.0,
		"relative_y": 0.0
	}
	var portal_nodes = tree.get_nodes_in_group("portals") if tree else []
	if portal_nodes.size() > 0 and is_instance_valid(portal_nodes[0]):
		var portal = portal_nodes[0]
		var p_pos = portal.global_position
		goal_data["found"] = true
		goal_data["portal_x"] = round(p_pos.x * 10.0) / 10.0
		goal_data["portal_y"] = round(p_pos.y * 10.0) / 10.0
		if player_data["alive"]:
			goal_data["distance_to_portal"] = round(player_pos.distance_to(p_pos) * 10.0) / 10.0
			goal_data["relative_x"] = round((p_pos.x - player_pos.x) * 10.0) / 10.0
			goal_data["relative_y"] = round((p_pos.y - player_pos.y) * 10.0) / 10.0

	var result_data = {
		"frame": frame_count,
		"physics_frame": Engine.get_physics_frames(),
		"timestamp": Time.get_unix_time_from_system(),
		"session_time": round((Time.get_ticks_msec() - session_start_ticks) / 10.0) / 100.0,
		"fps": Engine.get_frames_per_second(),
		"game_state": state_str,
		"scene": scene_name,
		"stats": {
			"score": PlayerData.score if PlayerData else 0,
			"deaths": PlayerData.deaths if PlayerData else 0
		},
		"player": player_data,
		"inputs": inputs_data,
		"coins": {
			"coins_collected": PlayerData.score / 100 if PlayerData else 0,
			"coins_remaining": coins_data.size(),
			"nearest_coin": nearest_coin,
			"all": coins_data.slice(0, 8)
		},
		"enemies": {
			"count": enemies_data.size(),
			"closest_enemy": closest_enemy,
			"all": enemies_data
		},
		"goal": goal_data
	}

	if current_event != "":
		result_data["event"] = current_event

	return result_data


func _get_player_perception(player: CharacterBody2D) -> Dictionary:
	var res = {
		"distance_to_ground": -1.0,
		"distance_to_wall_ahead": -1.0
	}
	if not player or not is_instance_valid(player) or not player.is_inside_tree():
		return res

	var world = player.get_world_2d()
	if not world:
		return res
	var space_state = world.direct_space_state
	if not space_state:
		return res

	var from_pos = player.global_position
	# Downward raycast (1200px) on layer 1 (World terrain)
	var to_ground = from_pos + Vector2(0, 1200)
	var query_ground = PhysicsRayQueryParameters2D.create(from_pos, to_ground, 1)
	query_ground.exclude = [player.get_rid()]
	var hit_ground = space_state.intersect_ray(query_ground)
	if hit_ground:
		res["distance_to_ground"] = round((hit_ground.position.y - from_pos.y) * 10.0) / 10.0

	# Forward raycast
	var facing = 1.0
	if player.velocity.x < -10.0 or Input.is_action_pressed("move_left"):
		facing = -1.0
	elif player.velocity.x > 10.0 or Input.is_action_pressed("move_right"):
		facing = 1.0

	var from_wall = from_pos + Vector2(0, -30)
	var to_wall = from_wall + Vector2(facing * 400, 0)
	var query_wall = PhysicsRayQueryParameters2D.create(from_wall, to_wall, 1)
	query_wall.exclude = [player.get_rid()]
	var hit_wall = space_state.intersect_ray(query_wall)
	if hit_wall:
		res["distance_to_wall_ahead"] = round(abs(hit_wall.position.x - from_pos.x) * 10.0) / 10.0

	return res


func _write_latest_state(data: Dictionary) -> void:
	var json_str = JSON.stringify(data, "  ")
	for dir in output_dirs:
		var target_path = dir.path_join("latest_state.json")
		var tmp_path = dir.path_join("latest_state.json.tmp")
		var file = FileAccess.open(tmp_path, FileAccess.WRITE)
		if file:
			file.store_string(json_str)
			file.flush()
			file.close()
			if FileAccess.file_exists(target_path):
				DirAccess.remove_absolute(target_path)
			DirAccess.rename_absolute(tmp_path, target_path)


func vec2_to_dict(v: Vector2) -> Dictionary:
	return {
		"x": round(v.x * 100.0) / 100.0,
		"y": round(v.y * 100.0) / 100.0
	}


# ==============================================================================
# COVERAGE TRACKING & REPORTING
# ==============================================================================

## Full inventory of expected Schema 1.0 event names organised by category.
## Used by generate_coverage_report() to compute PASS/MISSING per event.
const EXPECTED_EVENTS: Dictionary = {
	"input": [
		"move_left_pressed", "move_left_released",
		"move_right_pressed", "move_right_released",
		"jump_pressed", "jump_released", "pause_pressed",
		"retry_pressed", "quit_pressed", "main_menu_pressed"
	],
	"player_movement": [
		"jump_started", "jump_interrupted", "fall_started",
		"fall_distance_threshold_reached", "player_landed",
		"player_left_floor", "player_moved"
	],
	"player_lifecycle": [
		"player_spawned", "player_died", "player_removed",
		"death_counter_incremented"
	],
	"enemy": [
		"enemy_spawned", "enemy_started_moving", "enemy_reversed_at_wall",
		"stomp_attempted", "enemy_stomp_area_entered", "enemy_stomped",
		"enemy_contact_started", "enemy_contact_death",
		"enemy_killed", "enemy_removed"
	],
	"collectible": [
		"coin_spawned", "coin_overlap_started", "coin_picked",
		"coin_score_awarded", "coin_animation_started",
		"coin_remaining_count_changed", "coin_removed"
	],
	"portal": [
		"portal_entered", "portal_transition_started", "portal_fade_started",
		"portal_fade_completed", "scene_change_requested", "level_completed",
		"portal_target_missing", "scene_load_failed"
	],
	"scene_lifecycle": [
		"session_start", "session_end", "scene_loaded",
		"level_loaded", "main_screen_loaded", "end_screen_loaded"
	],
	"ui": [
		"pause_opened", "pause_closed", "death_overlay_shown",
		"death_menu_opened", "score_label_updated", "retry_started",
		"global_state_reset", "return_to_main_menu"
	],
	"state_snapshot": ["state_snapshot"],
	"anomaly": [
		"player_stuck_detected", "player_out_of_bounds",
		"unexpected_player_removal", "unexpected_score_change",
		"duplicate_pickup_attempt", "missing_expected_object",
		"scene_transition_timeout", "runtime_error_observed"
	]
}

## In-memory set of event names observed during this session
var _observed_events: Dictionary = {}


## Override _build_record to also track coverage
func _track_event(event_name: String) -> void:
	_observed_events[event_name] = _observed_events.get(event_name, 0) + 1


## Generate and write a machine-readable coverage_report.json to all output dirs.
## Call at session_end or from a test script to get a PASS/MISSING audit.
func generate_coverage_report() -> Dictionary:
	var report = {
		"schema_version": SCHEMA_VERSION,
		"session_id": session_id,
		"generated_at_unix_ms": int(Time.get_unix_time_from_system() * 1000.0),
		"session_duration_ms": Time.get_ticks_msec() - session_start_ticks,
		"total_events_logged": event_id,
		"categories": {}
	}

	var total_expected = 0
	var total_observed = 0

	for category in EXPECTED_EVENTS:
		var cat_result = {
			"expected": [],
			"observed": [],
			"missing": [],
			"extra": [],
			"pass_count": 0,
			"missing_count": 0
		}
		for ev_name in EXPECTED_EVENTS[category]:
			total_expected += 1
			cat_result["expected"].append(ev_name)
			if _observed_events.has(ev_name):
				cat_result["observed"].append(ev_name)
				cat_result["pass_count"] += 1
				total_observed += 1
			else:
				cat_result["missing"].append(ev_name)
				cat_result["missing_count"] += 1

		# Check for events emitted that were not in the expected list
		for obs_ev in _observed_events:
			if obs_ev in EXPECTED_EVENTS[category]:
				continue
			# Simple heuristic: if the observed event was not in any category, list as extra
			var in_any = false
			for cat2 in EXPECTED_EVENTS:
				if obs_ev in EXPECTED_EVENTS[cat2]:
					in_any = true
					break
			if not in_any and not cat_result["extra"].has(obs_ev):
				cat_result["extra"].append(obs_ev)

		report["categories"][category] = cat_result

	report["summary"] = {
		"total_expected": total_expected,
		"total_observed_and_matched": total_observed,
		"total_missing": total_expected - total_observed,
		"coverage_percent": round(float(total_observed) / float(max(total_expected, 1)) * 1000.0) / 10.0
	}

	# Persist to disk
	var json_str = JSON.stringify(report, "  ")
	for dir in output_dirs:
		var path = dir.path_join("coverage_report.json")
		var f = FileAccess.open(path, FileAccess.WRITE)
		if f:
			f.store_string(json_str)
			f.flush()
			f.close()

	return report


# ==============================================================================
# AGENT CONTROL ADAPTER (UDP & File-based IPC)
# ==============================================================================

func _setup_agent_server() -> void:
	_agent_udp = PacketPeerUDP.new()
	var err = _agent_udp.bind(agent_udp_port, "*")
	if err == OK:
		print("[GameLogger] Agent control server listening on UDP port %d" % agent_udp_port)
	else:
		print("[GameLogger] Agent UDP port %d unavailable (code %d), mailbox active" % [agent_udp_port, err])


func _poll_agent_commands() -> void:
	# 1. Check UDP packets
	if _agent_udp and _agent_udp.is_bound():
		while _agent_udp.get_available_packet_count() > 0:
			var sender_ip = _agent_udp.get_packet_ip()
			var sender_port = _agent_udp.get_packet_port()
			var pkt = _agent_udp.get_packet().get_string_from_utf8()
			var json = JSON.new()
			if json.parse(pkt) == OK and typeof(json.data) == TYPE_DICTIONARY:
				var resp = _execute_agent_command(json.data)
				if resp != null and sender_ip != "" and sender_port > 0:
					_agent_udp.set_dest_address(sender_ip, sender_port)
					_agent_udp.put_packet(JSON.stringify(resp).to_utf8_buffer())

	# 2. Check agent_command.json mailbox fallback
	for dir in output_dirs:
		var cmd_path = dir.path_join("agent_command.json")
		if FileAccess.file_exists(cmd_path):
			var f = FileAccess.open(cmd_path, FileAccess.READ)
			if f:
				var txt = f.get_as_text()
				f.close()
				DirAccess.remove_absolute(cmd_path)
				var json = JSON.new()
				if json.parse(txt) == OK and typeof(json.data) == TYPE_DICTIONARY:
					_execute_agent_command(json.data)
			break


func _execute_agent_command(cmd: Dictionary) -> Dictionary:
	var cmd_type = cmd.get("command", cmd.get("action", ""))

	# Ping / Handshake / State query
	if cmd_type == "ping" or cmd_type == "get_state":
		var tree = get_tree() if is_inside_tree() else null
		var cur_scene = tree.current_scene.name if tree and tree.current_scene else ""
		return {
			"status": "ok",
			"type": "pong",
			"frame": frame_count,
			"session_id": session_id,
			"scene": cur_scene,
			"player_alive": is_instance_valid(active_player) and active_player.is_inside_tree(),
			"score": PlayerData.score if PlayerData else 0,
			"deaths": PlayerData.deaths if PlayerData else 0,
			"paused": tree.paused if tree else false,
			"active_actions": _currently_pressed_agent_actions.duplicate()
		}

	# Retry / Restart current level
	if cmd_type == "retry":
		_release_all_agent_actions()
		if PlayerData:
			PlayerData.score = 0
		var tree = get_tree() if is_inside_tree() else null
		if tree:
			tree.paused = false
			if tree.current_scene and tree.current_scene.scene_file_path != "":
				tree.change_scene_to_file(tree.current_scene.scene_file_path)
			else:
				tree.reload_current_scene()
		log_action("retry_pressed", {"source": "agent"})
		log_event("retry_started", "ui", {"source": "agent"})
		return {"status": "ok", "action": "retry"}

	# Pause toggle / set
	if cmd_type == "pause":
		var tree = get_tree() if is_inside_tree() else null
		if tree:
			if cmd.has("value"):
				tree.paused = bool(cmd["value"])
			else:
				tree.paused = not tree.paused
			log_action("pause_pressed", {"source": "agent", "paused": tree.paused})
		return {"status": "ok", "action": "pause", "paused": tree.paused if tree else false}

	# Start Game / Go to Level 1
	if cmd_type == "start_game" or cmd_type == "play":
		var tree = get_tree() if is_inside_tree() else null
		if tree:
			tree.paused = false
			tree.change_scene_to_file("res://src/Levels/Level01.tscn")
		return {"status": "ok", "action": "start_game"}

	# Main Menu
	if cmd_type == "main_menu":
		_release_all_agent_actions()
		var tree = get_tree() if is_inside_tree() else null
		if tree:
			tree.paused = false
			tree.change_scene_to_file("res://src/Screens/MainScreen.tscn")
			log_action("main_menu_pressed", {"source": "agent"})
		return {"status": "ok", "action": "main_menu"}

	# Release all actions
	if cmd_type == "release_all" or cmd.get("release_all", false):
		_release_all_agent_actions()
		return {"status": "ok", "action": "release_all"}

	# Multi-action list: "actions": ["move_right", "jump"]
	if cmd.has("actions") and typeof(cmd["actions"]) == TYPE_ARRAY:
		var target_actions: Array = cmd["actions"]
		# Release any currently pressed not in target
		for act in _currently_pressed_agent_actions.duplicate():
			if not (act in target_actions):
				_set_agent_action_state(act, false)
		# Press any in target
		for act in target_actions:
			if typeof(act) == TYPE_STRING:
				_set_agent_action_state(act, true)
		return {"status": "ok", "active_actions": _currently_pressed_agent_actions.duplicate()}

	# Explicit press and release arrays: {"press": ["jump"], "release": ["move_left"]}
	if cmd.has("press") or cmd.has("release"):
		if cmd.has("release") and typeof(cmd["release"]) == TYPE_ARRAY:
			for act in cmd["release"]:
				if typeof(act) == TYPE_STRING:
					_set_agent_action_state(act, false)
		if cmd.has("press") and typeof(cmd["press"]) == TYPE_ARRAY:
			for act in cmd["press"]:
				if typeof(act) == TYPE_STRING:
					_set_agent_action_state(act, true)
		return {"status": "ok", "active_actions": _currently_pressed_agent_actions.duplicate()}

	# Single action with pressed bool: {"action": "move_right", "pressed": true}
	if cmd.has("action") and typeof(cmd["action"]) == TYPE_STRING:
		var act = cmd["action"]
		var is_pressed = cmd.get("pressed", true)
		_set_agent_action_state(act, is_pressed)
		return {"status": "ok", "action": act, "pressed": is_pressed}

	return {"status": "ignored", "reason": "unknown_command"}


func _set_agent_action_state(action: String, is_pressed: bool) -> void:
	if action == "retry":
		if is_pressed:
			_execute_agent_command({"command": "retry"})
		return
	elif action == "pause":
		if is_pressed:
			_execute_agent_command({"command": "pause"})
		return
	elif action == "main_menu":
		if is_pressed:
			_execute_agent_command({"command": "main_menu"})
		return
	elif action == "release_all":
		_release_all_agent_actions()
		return

	if not (action in ["move_left", "move_right", "jump"]):
		return

	var currently_pressed = _currently_pressed_agent_actions.has(action)
	if is_pressed and not currently_pressed:
		_currently_pressed_agent_actions.append(action)
		Input.action_press(action, 1.0)
		var ev = InputEventAction.new()
		ev.action = action
		ev.pressed = true
		ev.strength = 1.0
		Input.parse_input_event(ev)
	elif not is_pressed and currently_pressed:
		_currently_pressed_agent_actions.erase(action)
		Input.action_release(action)
		var ev = InputEventAction.new()
		ev.action = action
		ev.pressed = false
		ev.strength = 0.0
		Input.parse_input_event(ev)


func _release_all_agent_actions() -> void:
	for action in _currently_pressed_agent_actions.duplicate():
		Input.action_release(action)
		var ev = InputEventAction.new()
		ev.action = action
		ev.pressed = false
		ev.strength = 0.0
		Input.parse_input_event(ev)
	_currently_pressed_agent_actions.clear()

