extends SceneTree

## Automated Test Suite for Structured GameLogger
## Validates Schema 1.0, Event Inventory, Monotonic IDs, JSON parsing, and Anomalies

var passed_count: int = 0
var failed_count: int = 0


func _init() -> void:
	print("\n========================================================")
	print("  RUNNING AI GAME TESTER AGENT - GAMELOGGER TEST SUITE")
	print("========================================================\n")

	# Wait 1 frame for autoloads to settle
	call_deferred("_run_all_tests")


func _run_all_tests() -> void:
	var logger = root.get_node_or_null("GameLogger")
	_assert(logger != null, "GameLogger autoload is registered and available in SceneTree")

	if not logger:
		print("FATAL: GameLogger not found.")
		quit(1)
		return

	var start_event_id = logger.event_id

	# Test 1: Session metadata & Schema fields on session_start
	print("--- Test Group 1: Session & Schema Conformance ---")
	_assert(logger.session_id.begins_with("session_"), "Session ID is properly generated")
	_assert(logger.SCHEMA_VERSION == "1.0", "Schema version is 1.0")
	_assert(logger.get_log_paths().size() > 0, "Log output paths are configured")

	# Test 2: Input & Action Events
	print("\n--- Test Group 2: Input & Action Events ---")
	var rec1 = logger.log_action("move_right_pressed", {"strength": 1.0})
	_assert(rec1["category"] == "input", "Action category is input")
	_assert(rec1["event_name"] == "move_right_pressed", "Event name is move_right_pressed")
	_assert(rec1["action_context"]["recent_actions"].size() > 0, "Recent actions buffer contains entry")

	logger.log_action("jump_pressed", {"strength": 1.0})
	logger.log_action("jump_released", {})
	logger.log_action("pause_pressed", {})
	logger.log_action("retry_pressed", {"button": "RetryButton"})
	logger.log_action("main_menu_pressed", {"button": "MainScreenButton"})
	logger.log_action("quit_pressed", {"button": "QuitButton"})

	# Test 3: Player Movement & Physics Transitions
	print("\n--- Test Group 3: Player Movement & Physics ---")
	var rec_spawn = logger.log_event("player_spawned", "player_lifecycle", {
		"position": {"x": 200.0, "y": 800.0},
		"speed": {"x": 700.0, "y": 1350.0},
		"stomp_impulse": 1600.0
	})
	_assert(rec_spawn["category"] == "player_lifecycle", "player_spawned category is player_lifecycle")

	var rec_jump = logger.log_event("jump_started", "player_movement", {
		"start_position": {"x": 200.0, "y": 800.0},
		"initial_velocity": {"x": 0.0, "y": -1350.0}
	})
	_assert(rec_jump["event_name"] == "jump_started", "jump_started recorded")

	logger.log_event("jump_interrupted", "player_movement", {
		"position": {"x": 200.0, "y": 700.0},
		"velocity_before": {"x": 0.0, "y": -600.0}
	})
	logger.log_event("fall_started", "player_movement", {
		"start_position": {"x": 200.0, "y": 650.0},
		"velocity": {"x": 0.0, "y": 100.0}
	})
	logger.log_event("fall_distance_threshold_reached", "player_movement", {
		"fall_distance": 420.0,
		"threshold": 400.0
	})
	logger.log_event("player_landed", "player_movement", {
		"position": {"x": 280.0, "y": 800.0},
		"fall_distance": 150.0,
		"horizontal_displacement": 80.0,
		"was_jumping": true
	})
	logger.log_event("player_left_floor", "player_movement", {
		"position": {"x": 300.0, "y": 800.0},
		"velocity": {"x": 700.0, "y": 0.0}
	})
	logger.log_event("player_moved", "player_movement", {
		"from_position": {"x": 200.0, "y": 800.0},
		"to_position": {"x": 300.0, "y": 800.0},
		"distance": 100.0
	})

	# Test 4: Combat & Enemy Interactions
	print("\n--- Test Group 4: Combat & Stomp Events ---")
	logger.log_event("enemy_spawned", "enemy", {
		"position": {"x": 500.0, "y": 800.0},
		"score_value": 100
	})
	logger.log_event("enemy_started_moving", "enemy", {"direction_x": -1.0})
	logger.log_event("enemy_reversed_at_wall", "enemy", {"old_direction": -1, "new_direction": 1})
	logger.log_event("stomp_attempted", "enemy", {
		"player_velocity_y": 800.0
	})
	logger.log_event("enemy_stomp_area_entered", "enemy", {"stomp_area_y": 780.0})
	logger.log_event("enemy_stomped", "enemy", {
		"bounce_velocity": {"x": 0.0, "y": -600.0},
		"stomp_impulse": 600.0
	})
	logger.log_event("enemy_killed", "enemy", {
		"score_gain": 100,
		"score_before": 0,
		"score_after": 100
	})
	logger.log_event("enemy_removed", "enemy", {"was_killed": true})

	logger.log_event("enemy_contact_started", "enemy", {"contact_type": "body"})
	logger.log_event("enemy_contact_death", "enemy", {"enemy_name": "Enemy"})
	logger.log_event("player_died", "player_lifecycle", {"position": {"x": 500.0, "y": 800.0}})
	logger.log_event("death_counter_incremented", "player_lifecycle", {"deaths_before": 0, "deaths_after": 1})
	logger.log_event("player_removed", "player_lifecycle", {"position": {"x": 500.0, "y": 800.0}})

	# Test 5: Collectibles (Coins)
	print("\n--- Test Group 5: Collectibles (Coins) ---")
	logger.log_event("coin_spawned", "collectible", {"position": {"x": 400.0, "y": 600.0}, "score_value": 100})
	logger.log_event("coin_overlap_started", "collectible", {"collector": "Player"})
	logger.log_event("coin_picked", "collectible", {"score": 100})
	logger.log_event("coin_score_awarded", "collectible", {"score_gain": 100, "score_before": 100, "score_after": 200})
	logger.log_event("coin_animation_started", "collectible", {"animation": "picked"})
	logger.log_event("coin_remaining_count_changed", "collectible", {"remaining_count": 15})
	logger.log_event("coin_removed", "collectible", {"was_collected": true})

	# Test 6: Portal & Scene Lifecycle
	print("\n--- Test Group 6: Portal & Scene Lifecycle ---")
	logger.log_event("portal_entered", "portal", {"target_scene": "res://src/Levels/Level02.tscn"})
	logger.log_event("portal_transition_started", "portal", {
		"source_scene": "res://src/Levels/Level01.tscn",
		"target_scene": "res://src/Levels/Level02.tscn"
	})
	logger.log_event("portal_fade_started", "portal", {"animation": "fade_out"})
	logger.log_event("portal_fade_completed", "portal", {})
	logger.log_event("scene_change_requested", "portal", {"target_scene": "res://src/Levels/Level02.tscn"})
	logger.log_event("level_completed", "portal", {"final_score": 1000, "final_deaths": 1})
	logger.log_lifecycle("level_loaded", {"scene": "res://src/Levels/Level02.tscn"})

	# Test 7: UI & State Reset Events
	print("\n--- Test Group 7: UI & Lifecycle Events ---")
	logger.log_event("pause_opened", "ui", {"score": 200})
	logger.log_event("pause_closed", "ui", {"score": 200})
	logger.log_event("death_overlay_shown", "ui", {"score": 200, "deaths": 1})
	logger.log_event("death_menu_opened", "ui", {"title": "You died"})
	logger.log_event("score_label_updated", "ui", {"displayed_score": 200})
	logger.log_event("retry_started", "ui", {"score_before": 200, "deaths_before": 1})
	logger.log_event("global_state_reset", "ui", {"reason": "player_reset"})
	logger.log_event("return_to_main_menu", "ui", {"target_scene": "res://src/Screens/MainScreen.tscn"})

	# Test 8: State Snapshots
	print("\n--- Test Group 8: State Snapshots ---")
	var snap_rec = logger.log_state_snapshot()
	_assert(snap_rec["category"] == "state_snapshot", "Snapshot category is state_snapshot")
	_assert(snap_rec["event_name"] == "state_snapshot", "Snapshot event_name is state_snapshot")
	_assert(snap_rec["data"].has("fps"), "Snapshot data contains fps")
	_assert(snap_rec["data"].has("coins"), "Snapshot data contains coin inventory")
	_assert(snap_rec["data"].has("enemies"), "Snapshot data contains enemy telemetry")
	_assert(snap_rec["data"].has("goal"), "Snapshot data contains portal goal data")

	# Test 9: Anomaly Detection
	print("\n--- Test Group 9: Anomaly Detection ---")
	var anom1 = logger.log_anomaly("player_stuck_detected", {
		"held_input": "move_right",
		"held_frames": 60,
		"displacement": 2.1,
		"expected": "Horizontal displacement > 10px",
		"observed": "Stationary despite active input"
	}, "warning")
	_assert(anom1["category"] == "anomaly", "Anomaly category is anomaly")
	_assert(anom1["data"]["anomaly_type"] == "player_stuck_detected", "Anomaly type preserved")

	logger.log_anomaly("player_out_of_bounds", {
		"threshold_y": 1400.0,
		"position": {"x": 200.0, "y": 1450.0}
	}, "error")
	logger.log_anomaly("unexpected_score_change", {
		"old_score": 500,
		"new_score": 300,
		"delta": -200
	}, "warning")
	logger.log_anomaly("duplicate_pickup_attempt", {
		"coin_id": 1234
	}, "warning")
	logger.log_anomaly("missing_expected_object", {
		"node": "Portal2D",
		"property": "next_scene"
	}, "error")
	logger.log_anomaly("scene_transition_timeout", {
		"elapsed_ms": 5200
	}, "error")

	# Test 10: JSONL File Integrity & Monotonic Event IDs Verification
	print("\n--- Test Group 10: JSONL Output Validation on Disk ---")
	var log_paths = logger.get_log_paths()
	var verified_path = ""
	for p in log_paths:
		if FileAccess.file_exists(p):
			verified_path = p
			break

	_assert(verified_path != "", "Log file exists on disk: " + verified_path)

	if verified_path != "":
		var file = FileAccess.open(verified_path, FileAccess.READ)
		_assert(file != null, "Successfully opened log file for verification")

		var line_count = 0
		var parse_errors = 0
		var monotonic_errors = 0
		var current_expected_id = -1
		var current_session = ""

		while not file.eof_reached():
			var line = file.get_line().strip_edges()
			if line == "":
				continue
			line_count += 1

			var json_obj = JSON.parse_string(line)
			if json_obj == null or typeof(json_obj) != TYPE_DICTIONARY:
				parse_errors += 1
				continue

			# Schema checks
			if not json_obj.has("schema_version") or not json_obj.has("event_id") or not json_obj.has("event_name"):
				parse_errors += 1

			# Monotonicity check within the same session
			var item_session = json_obj.get("session_id", "")
			var item_event_id = json_obj.get("event_id", -1)

			if item_session != current_session:
				current_session = item_session
				current_expected_id = item_event_id
			else:
				if item_event_id != current_expected_id + 1:
					monotonic_errors += 1
				current_expected_id = item_event_id

		file.close()

		_assert(parse_errors == 0, "All JSON lines parse validly without syntax errors (Errors: %d)" % parse_errors)
		_assert(monotonic_errors == 0, "All event IDs are strictly monotonic (Errors: %d)" % monotonic_errors)
		_assert(line_count > 0, "Verified %d total log records written to disk" % line_count)

	print("\n========================================================")
	print("  TEST RESULTS SUMMARY:")
	print("  Passed: %d" % passed_count)
	print("  Failed: %d" % failed_count)
	print("========================================================\n")

	if failed_count == 0:
		print(">>> ALL TESTS PASSED SUCCESSFULLY! <<<\n")
		quit(0)
	else:
		print(">>> SOME TESTS FAILED! <<<\n")
		quit(1)


func _assert(condition: bool, message: String) -> void:
	if condition:
		passed_count += 1
		print("  [PASS] " + message)
	else:
		failed_count += 1
		print("  [FAIL] " + message)
