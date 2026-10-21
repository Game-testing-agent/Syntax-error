extends Node

## GameLogger (Godot 3.5 Compatible) - Real-Time State & Telemetry Logger for AI Agents
## Exports state to latest_state.json and game_events.jsonl

export var log_every_n_frames: int = 4
export var enable_logging: bool = true

var frame_count: int = 0
var output_dirs: Array = []
var session_start_ticks: int = 0
var last_score: int = 0
var last_deaths: int = 0
var last_scene_name: String = ""
var active_player: KinematicBody2D = null


func _ready() -> void:
	pause_mode = Node.PAUSE_MODE_PROCESS
	session_start_ticks = OS.get_ticks_msec()

	var res_dir = ProjectSettings.globalize_path("res://")
	output_dirs.append(res_dir)
	var parent_dir = res_dir.plus_file("..")
	var dir = Directory.new()
	if dir.dir_exists(parent_dir):
		output_dirs.append(parent_dir)

	if has_node("/root/PlayerData"):
		var pd = get_node("/root/PlayerData")
		pd.connect("updated", self, "_on_player_data_updated")
		pd.connect("died", self, "_on_player_died")
		pd.connect("reset", self, "_on_player_reset")

	log_event("session_start", {
		"game": "Your First Game - 2D Platformer (Godot 3)",
		"timestamp": OS.get_unix_time()
	})


func _process(_delta: float) -> void:
	if not enable_logging:
		return

	frame_count += 1

	var current_scene = get_tree().current_scene
	var current_scene_name = current_scene.name if current_scene else "Unknown"
	if current_scene_name != last_scene_name:
		last_scene_name = current_scene_name
		var pd = get_node_or_null("/root/PlayerData")
		log_event("scene_changed", {
			"scene": current_scene_name,
			"score": pd.score if pd else 0,
			"deaths": pd.deaths if pd else 0
		})

	if frame_count % log_every_n_frames == 0:
		var state = extract_game_state()
		_write_latest_state(state)
		if frame_count % (log_every_n_frames * 15) == 0:
			var event_copy = state.duplicate(true)
			event_copy["event"] = "periodic_snapshot"
			_append_event(event_copy)


func register_player(player: KinematicBody2D) -> void:
	active_player = player
	log_event("player_spawned", {
		"x": round(player.global_position.x),
		"y": round(player.global_position.y)
	})


func unregister_player(player: KinematicBody2D) -> void:
	if active_player == player:
		active_player = null


func log_event(event_name: String, details: Dictionary = {}) -> void:
	if not enable_logging:
		return

	var pd = get_node_or_null("/root/PlayerData")
	var event_data = {
		"event": event_name,
		"frame": frame_count,
		"timestamp": OS.get_unix_time(),
		"session_time": round((OS.get_ticks_msec() - session_start_ticks) / 10.0) / 100.0,
		"scene": get_tree().current_scene.name if get_tree().current_scene else "Unknown",
		"score": pd.score if pd else 0,
		"deaths": pd.deaths if pd else 0
	}

	for key in details.keys():
		event_data[key] = details[key]

	_append_event(event_data)
	var state = extract_game_state(event_name)
	_write_latest_state(state)


func log_player_jump(pos: Vector2, vel: Vector2) -> void:
	log_event("player_jump", {
		"pos_x": round(pos.x),
		"pos_y": round(pos.y),
		"vel_x": round(vel.x),
		"vel_y": round(vel.y)
	})


func log_player_stomp(pos: Vector2, bounce_vel: Vector2) -> void:
	log_event("player_stomp", {
		"pos_x": round(pos.x),
		"pos_y": round(pos.y),
		"bounce_vel_y": round(bounce_vel.y)
	})


func log_player_died(pos: Vector2) -> void:
	var pd = get_node_or_null("/root/PlayerData")
	log_event("player_died", {
		"pos_x": round(pos.x),
		"pos_y": round(pos.y),
		"total_deaths": pd.deaths if pd else 1
	})


func log_enemy_killed(pos: Vector2, enemy_name: String, score_gain: int) -> void:
	var pd = get_node_or_null("/root/PlayerData")
	log_event("enemy_killed", {
		"enemy_name": enemy_name,
		"enemy_x": round(pos.x),
		"enemy_y": round(pos.y),
		"score_gain": score_gain,
		"new_score": pd.score + score_gain if pd else score_gain
	})


func log_coin_collected(pos: Vector2, score_gain: int) -> void:
	var pd = get_node_or_null("/root/PlayerData")
	log_event("coin_collected", {
		"coin_x": round(pos.x),
		"coin_y": round(pos.y),
		"score_gain": score_gain,
		"new_score": pd.score + score_gain if pd else score_gain
	})


func log_level_cleared(pos: Vector2, next_scene_path: String) -> void:
	log_event("level_cleared", {
		"portal_x": round(pos.x),
		"portal_y": round(pos.y),
		"next_scene": next_scene_path
	})


func _on_player_data_updated() -> void:
	var pd = get_node_or_null("/root/PlayerData")
	if pd and pd.score != last_score:
		last_score = pd.score


func _on_player_died() -> void:
	var pd = get_node_or_null("/root/PlayerData")
	if pd and pd.deaths != last_deaths:
		last_deaths = pd.deaths


func _on_player_reset() -> void:
	var pd = get_node_or_null("/root/PlayerData")
	log_event("player_reset", {
		"score": pd.score if pd else 0,
		"deaths": pd.deaths if pd else 0
	})


func extract_game_state(current_event: String = "") -> Dictionary:
	var current_scene = get_tree().current_scene
	var scene_name = current_scene.name if current_scene else "Unknown"

	var state_str = "playing"
	if scene_name == "MainScreen":
		state_str = "main_menu"
	elif scene_name == "EndScreen":
		state_str = "victory"
	elif get_tree().paused:
		if active_player == null:
			state_str = "player_died"
		else:
			state_str = "paused"
	elif active_player == null and (scene_name == "Level01" or scene_name == "Level02"):
		state_str = "player_died"

	var player = active_player
	if player == null and is_instance_valid(current_scene):
		player = current_scene.get_node_or_null("Player") as KinematicBody2D
		if player == null:
			var players = get_tree().get_nodes_in_group("player")
			if players.size() > 0 and is_instance_valid(players[0]):
				player = players[0] as KinematicBody2D

	var player_data = {
		"alive": player != null and is_instance_valid(player)
	}

	var player_pos = Vector2.ZERO
	if player_data["alive"]:
		player_pos = player.global_position
		player_data["x"] = round(player.global_position.x)
		player_data["y"] = round(player.global_position.y)
		player_data["vel_x"] = round(player.velocity.x * 10.0) / 10.0 if "velocity" in player else 0.0
		player_data["vel_y"] = round(player.velocity.y * 10.0) / 10.0 if "velocity" in player else 0.0
		player_data["on_floor"] = player.is_on_floor()
		player_data["on_wall"] = player.is_on_wall()
		player_data["on_ceiling"] = player.is_on_ceiling()
		player_data["facing"] = 1 if ("velocity" in player and player.velocity.x >= 0) else -1
		player_data["stomp_impulse"] = player.stomp_impulse if "stomp_impulse" in player else 600.0
		player_data["speed_max"] = {
			"x": player.speed.x if "speed" in player else 400.0,
			"y": player.speed.y if "speed" in player else 500.0
		}
		player_data["hitbox"] = {"width": 80.0, "height": 82.0}

		var perception = _get_player_perception(player)
		player_data["distance_to_ground"] = perception["distance_to_ground"]
		player_data["distance_to_wall_ahead"] = perception["distance_to_wall_ahead"]

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

	var coins_data: Array = []
	var coin_nodes = get_tree().get_nodes_in_group("coins")
	for coin in coin_nodes:
		if is_instance_valid(coin) and coin.is_inside_tree():
			var c_pos = coin.global_position
			var dist = round(player_pos.distance_to(c_pos) * 10.0) / 10.0 if player_data["alive"] else 0.0
			coins_data.append({
				"x": round(c_pos.x),
				"y": round(c_pos.y),
				"distance": dist,
				"relative_x": round(c_pos.x - player_pos.x) if player_data["alive"] else 0.0,
				"relative_y": round(c_pos.y - player_pos.y) if player_data["alive"] else 0.0
			})

	# Bubble sort coins by distance
	if player_data["alive"] and coins_data.size() > 1:
		for i in range(coins_data.size()):
			for j in range(i + 1, coins_data.size()):
				if coins_data[j]["distance"] < coins_data[i]["distance"]:
					var tmp = coins_data[i]
					coins_data[i] = coins_data[j]
					coins_data[j] = tmp

	var nearest_coin = coins_data[0] if coins_data.size() > 0 else null

	var enemies_data: Array = []
	var enemy_nodes = get_tree().get_nodes_in_group("enemies")
	for enemy in enemy_nodes:
		if is_instance_valid(enemy) and enemy.is_inside_tree():
			var e_pos = enemy.global_position
			var dist = round(player_pos.distance_to(e_pos) * 10.0) / 10.0 if player_data["alive"] else 0.0
			var dx = round(e_pos.x - player_pos.x) if player_data["alive"] else 0.0
			var dy = round(e_pos.y - player_pos.y) if player_data["alive"] else 0.0
			var is_above = (player_pos.y < (e_pos.y - 20.0)) if player_data["alive"] else false
			var vel_x = enemy.velocity.x if "velocity" in enemy else 0.0
			enemies_data.append({
				"name": enemy.name,
				"x": round(e_pos.x),
				"y": round(e_pos.y),
				"vel_x": round(vel_x),
				"distance": dist,
				"relative_x": dx,
				"relative_y": dy,
				"player_is_above": is_above,
				"is_stompable": is_above and player_data["alive"] and ("velocity" in player and player.velocity.y > 0),
				"is_threat": dist < 450.0 and not is_above and player_data["alive"]
			})

	if player_data["alive"] and enemies_data.size() > 1:
		for i in range(enemies_data.size()):
			for j in range(i + 1, enemies_data.size()):
				if enemies_data[j]["distance"] < enemies_data[i]["distance"]:
					var tmp = enemies_data[i]
					enemies_data[i] = enemies_data[j]
					enemies_data[j] = tmp

	var closest_enemy = enemies_data[0] if enemies_data.size() > 0 else null

	var goal_data = {
		"found": false,
		"portal_x": 0.0,
		"portal_y": 0.0,
		"distance_to_portal": 0.0,
		"relative_x": 0.0,
		"relative_y": 0.0
	}
	var portal_nodes = get_tree().get_nodes_in_group("portals")
	if portal_nodes.size() > 0 and is_instance_valid(portal_nodes[0]):
		var portal = portal_nodes[0]
		var p_pos = portal.global_position
		goal_data["found"] = true
		goal_data["portal_x"] = round(p_pos.x)
		goal_data["portal_y"] = round(p_pos.y)
		if player_data["alive"]:
			goal_data["distance_to_portal"] = round(player_pos.distance_to(p_pos) * 10.0) / 10.0
			goal_data["relative_x"] = round(p_pos.x - player_pos.x)
			goal_data["relative_y"] = round(p_pos.y - player_pos.y)

	var pd = get_node_or_null("/root/PlayerData")
	var result_data = {
		"frame": frame_count,
		"timestamp": OS.get_unix_time(),
		"session_time": round((OS.get_ticks_msec() - session_start_ticks) / 10.0) / 100.0,
		"fps": Engine.get_frames_per_second(),
		"game_state": state_str,
		"scene": scene_name,
		"stats": {
			"score": pd.score if pd else 0,
			"deaths": pd.deaths if pd else 0
		},
		"player": player_data,
		"inputs": inputs_data,
		"coins": {
			"coins_collected": pd.score / 100 if pd else 0,
			"coins_remaining": coins_data.size(),
			"nearest_coin": nearest_coin,
			"all": coins_data.slice(0, 8) if coins_data.size() > 8 else coins_data
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


func _get_player_perception(player: KinematicBody2D) -> Dictionary:
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
	var to_ground = from_pos + Vector2(0, 1200)
	var hit_ground = space_state.intersect_ray(from_pos, to_ground, [player], 1)
	if hit_ground and hit_ground.has("position"):
		res["distance_to_ground"] = round((hit_ground.position.y - from_pos.y) * 10.0) / 10.0

	var facing = 1.0
	if ("velocity" in player and player.velocity.x < -10.0) or Input.is_action_pressed("move_left"):
		facing = -1.0
	elif ("velocity" in player and player.velocity.x > 10.0) or Input.is_action_pressed("move_right"):
		facing = 1.0

	var from_wall = from_pos + Vector2(0, -30)
	var to_wall = from_wall + Vector2(facing * 400, 0)
	var hit_wall = space_state.intersect_ray(from_wall, to_wall, [player], 1)
	if hit_wall and hit_wall.has("position"):
		res["distance_to_wall_ahead"] = round(abs(hit_wall.position.x - from_pos.x) * 10.0) / 10.0

	return res


func _write_latest_state(data: Dictionary) -> void:
	var json_str = to_json(data)
	var dir = Directory.new()
	for d in output_dirs:
		var target_path = d.plus_file("latest_state.json")
		var tmp_path = d.plus_file("latest_state.json.tmp")
		var file = File.new()
		if file.open(tmp_path, File.WRITE) == OK:
			file.store_string(json_str)
			file.flush()
			file.close()
			if dir.file_exists(target_path):
				dir.remove(target_path)
			dir.rename(tmp_path, target_path)


func _append_event(event_dict: Dictionary) -> void:
	var line = to_json(event_dict)
	for d in output_dirs:
		var target_path = d.plus_file("game_events.jsonl")
		var file = File.new()
		if file.open(target_path, File.READ_WRITE) == OK:
			file.seek_end()
			file.store_line(line)
			file.flush()
			file.close()
		elif file.open(target_path, File.WRITE) == OK:
			file.store_line(line)
			file.flush()
			file.close()
