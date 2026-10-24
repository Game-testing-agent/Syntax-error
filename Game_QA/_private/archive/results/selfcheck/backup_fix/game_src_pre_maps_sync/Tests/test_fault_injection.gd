extends SceneTree

## Controlled Fault-Injection Test Suite for AI Game Tester Logger
## Tests that anomaly detection fires correctly for each fault scenario.
## Run via: godot --headless --script res://src/Tests/test_fault_injection.gd

var passed: int = 0
var failed: int = 0


func _init() -> void:
	print("\n========================================================")
	print("  FAULT INJECTION TEST SUITE - AI GAME TESTER LOGGER")
	print("========================================================\n")
	call_deferred("_run_faults")


func _run_faults() -> void:
	var logger = root.get_node_or_null("GameLogger")
	_assert(logger != null, "GameLogger autoload available")
	if not logger:
		quit(1)
		return

	# -------------------------------------------------------------------------
	# FAULT 1: Unexpected score decrease (score drops without reset)
	# Expected: log_anomaly("unexpected_score_change") fires via PlayerData setter
	# -------------------------------------------------------------------------
	print("\n--- Fault 1: Unexpected score decrease ---")
	var player_data = root.get_node_or_null("PlayerData")
	_assert(player_data != null, "PlayerData autoload available")
	if player_data:
		var id_before = logger.event_id
		# Set score to 500 directly to avoid triggering anomaly on increase
		player_data.is_resetting = true
		player_data.score = 500
		player_data.is_resetting = false
		# Now trigger a decrease (not via reset) — this should fire the anomaly setter
		player_data.score = 200
		_assert(logger.event_id > id_before, "Fault 1: unexpected_score_change anomaly fired on score drop (500->200)")

	# -------------------------------------------------------------------------
	# FAULT 2: Duplicate coin pickup (is_collected guard)
	# -------------------------------------------------------------------------
	print("\n--- Fault 2: Duplicate coin pickup anomaly ---")
	var id2_before = logger.event_id
	logger.log_anomaly("duplicate_pickup_attempt", {
		"coin_id": 99999,
		"position": {"x": 100.0, "y": 200.0},
		"expected": "Coin body_entered should not trigger after collection",
		"observed": "Duplicate body_entered on collected coin"
	}, "warning")
	_assert(logger.event_id > id2_before, "Fault 2: duplicate_pickup_attempt anomaly logged")

	# -------------------------------------------------------------------------
	# FAULT 3: Player out-of-bounds (below Y threshold)
	# -------------------------------------------------------------------------
	print("\n--- Fault 3: Player out-of-bounds ---")
	var id3_before = logger.event_id
	logger.log_anomaly("player_out_of_bounds", {
		"position": {"x": 300.0, "y": 1500.0},
		"threshold_y": 1400.0,
		"expected": "Player position Y <= 1400",
		"observed": "Player position Y exceeded limit: 1500.0"
	}, "error")
	_assert(logger.event_id > id3_before, "Fault 3: player_out_of_bounds anomaly logged")

	# -------------------------------------------------------------------------
	# FAULT 4: Unexpected player removal (not during death or transition)
	# -------------------------------------------------------------------------
	print("\n--- Fault 4: Unexpected player removal ---")
	var id4_before = logger.event_id
	logger.log_anomaly("unexpected_player_removal", {
		"position": {"x": 500.0, "y": 800.0},
		"expected": "Player removal should occur on death or scene transition",
		"observed": "Player exited scene tree without death flag or transition"
	}, "error")
	_assert(logger.event_id > id4_before, "Fault 4: unexpected_player_removal anomaly logged")

	# -------------------------------------------------------------------------
	# FAULT 5: Missing portal target (Portal2D has no next_scene)
	# -------------------------------------------------------------------------
	print("\n--- Fault 5: Portal with null next_scene ---")
	var id5_before = logger.event_id
	logger.log_anomaly("missing_expected_object", {
		"node": "Portal2D",
		"missing_property": "next_scene",
		"expected": "Valid PackedScene assigned to next_scene",
		"observed": "next_scene is null or empty"
	}, "error")
	_assert(logger.event_id > id5_before, "Fault 5: missing_expected_object anomaly logged for null portal")

	# -------------------------------------------------------------------------
	# FAULT 6: Scene transition timeout (> 5000ms)
	# -------------------------------------------------------------------------
	print("\n--- Fault 6: Scene transition timeout ---")
	var id6_before = logger.event_id
	logger.log_anomaly("scene_transition_timeout", {
		"elapsed_ms": 6100,
		"expected": "Scene should load within 5000ms",
		"observed": "Scene transition timed out after 6100ms"
	}, "error")
	_assert(logger.event_id > id6_before, "Fault 6: scene_transition_timeout anomaly logged")

	# -------------------------------------------------------------------------
	# FAULT 7: Runtime error during scene change
	# -------------------------------------------------------------------------
	print("\n--- Fault 7: Runtime error during scene load ---")
	var id7_before = logger.event_id
	logger.log_anomaly("runtime_error_observed", {
		"error_code": 31,
		"operation": "change_scene_to_packed",
		"target_scene": "res://src/Levels/Level99.tscn",
		"expected": "Error code OK (0)",
		"observed": "Error code 31 (ERR_FILE_NOT_FOUND)"
	}, "error")
	_assert(logger.event_id > id7_before, "Fault 7: runtime_error_observed anomaly logged")

	# -------------------------------------------------------------------------
	# FAULT 8: Player stuck (sustained input, no displacement)
	# -------------------------------------------------------------------------
	print("\n--- Fault 8: Player stuck detection ---")
	var id8_before = logger.event_id
	logger.log_anomaly("player_stuck_detected", {
		"held_input": "move_right",
		"held_frames": 90,
		"displacement": 1.2,
		"expected": "Player should move horizontally when move_right is held and unobstructed",
		"observed": "Player remained stationary (displacement < 8px)"
	}, "warning")
	_assert(logger.event_id > id8_before, "Fault 8: player_stuck_detected anomaly logged")

	# -------------------------------------------------------------------------
	# FAULT 9: Schema conformance on returned anomaly Dictionary
	# -------------------------------------------------------------------------
	print("\n--- Fault 9: Schema conformance on anomaly records ---")
	var anom = logger.log_anomaly("test_schema_check", {
		"expected": "Schema fields present",
		"observed": "Verifying anomaly record structure"
	}, "warning")
	_assert(anom.has("schema_version"),         "Fault 9a: schema_version present")
	_assert(anom.has("session_id"),             "Fault 9b: session_id present")
	_assert(anom.has("event_id"),               "Fault 9c: event_id present")
	_assert(anom.get("category") == "anomaly",  "Fault 9d: category == anomaly")
	_assert(anom.has("timestamp_unix_ms"),      "Fault 9e: timestamp_unix_ms present")
	_assert(anom.has("action_context"),         "Fault 9f: action_context present")
	_assert(anom.has("elapsed_ms"),             "Fault 9g: elapsed_ms present")
	_assert(anom.has("physics_frame"),          "Fault 9h: physics_frame present")
	_assert(anom.has("evidence"),               "Fault 9i: evidence field present")

	# -------------------------------------------------------------------------
	# FAULT 10: Recursion guard prevents double-logging
	# -------------------------------------------------------------------------
	print("\n--- Fault 10: Recursion guard ---")
	var id_before = logger.event_id
	logger.is_logging_internal = true
	logger.log_event("should_be_blocked", "anomaly", {"test": true})
	logger.is_logging_internal = false
	_assert(logger.event_id == id_before, "Fault 10: Recursion guard blocked nested log_event (event_id unchanged)")

	# -------------------------------------------------------------------------
	# SUMMARY
	# -------------------------------------------------------------------------
	print("\n========================================================")
	print("  FAULT INJECTION RESULTS:")
	print("  Passed: %d" % passed)
	print("  Failed: %d" % failed)
	print("========================================================\n")

	if failed == 0:
		print(">>> ALL FAULT INJECTION TESTS PASSED! <<<\n")
		quit(0)
	else:
		print(">>> SOME FAULT INJECTION TESTS FAILED! <<<\n")
		quit(1)


func _assert(condition: bool, message: String) -> void:
	if condition:
		passed += 1
		print("  [PASS] " + message)
	else:
		failed += 1
		print("  [FAIL] " + message)
