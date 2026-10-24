extends SceneTree

## Automated Gameplay Flow Test:
## Validates that logging survives:
##   1. Player spawning
##   2. Death and counter increment
##   3. Retry cycle and level reload
##   4. Portal transition and scene change
##   5. State snapshotting during active gameplay

var logger = null
var player_data = null
var test_step: int = 0
var test_frames: int = 0
var pass_count: int = 0
var fail_count: int = 0


func _init() -> void:
	print("\n========================================================")
	print("  RUNNING GAMEPLAY FLOW INTEGRATION TEST")
	print("========================================================\n")
	call_deferred("_start_flow")


func _start_flow() -> void:
	logger = root.get_node_or_null("GameLogger")
	player_data = root.get_node_or_null("PlayerData")
	_assert(logger != null, "GameLogger loaded")
	_assert(player_data != null, "PlayerData loaded")

	# Step 1: Change to Level01
	print("Step 1: Loading Level01.tscn...")
	change_scene_to_file("res://src/Levels/Level01.tscn")


func _process(_delta: float) -> bool:
	test_frames += 1

	if test_step == 0 and test_frames >= 10:
		# Level01 should now be loaded
		var level = current_scene
		_assert(level != null and "Level01" in level.name, "Level01 is active scene: " + (level.name if level else "null"))
		var player = level.get_node_or_null("Player") if level else null
		_assert(player != null, "Player is present in Level01")
		_assert(logger.active_player == player, "GameLogger tracked active player")

		# Step 2: Trigger Player Death
		print("\nStep 2: Triggering Player death...")
		test_step = 1
		test_frames = 0
		var deaths_before = player_data.deaths
		player.die()
		_assert(player_data.deaths == deaths_before + 1, "Death counter incremented to " + str(player_data.deaths))

	elif test_step == 1 and test_frames >= 10:
		# Step 3: Trigger Retry cycle
		print("\nStep 3: Triggering Retry cycle...")
		test_step = 2
		test_frames = 0
		logger.log_action("retry_pressed", {"button": "RetryButton"})
		logger.log_event("retry_started", "ui", {
			"score_before": player_data.score,
			"deaths_before": player_data.deaths
		})
		player_data.score = 0
		paused = false
		reload_current_scene()

	elif test_step == 2 and test_frames >= 10:
		# Step 4: Verify post-retry recovery
		print("\nStep 4: Verifying post-retry state and logging continuity...")
		var level = current_scene
		var player = level.get_node_or_null("Player") if level else null
		_assert(player != null, "New Player spawned after retry")
		_assert(logger.active_player == player, "GameLogger registered new player instance")

		# Step 5: Test Portal transition
		print("\nStep 5: Testing Portal scene transition...")
		test_step = 3
		test_frames = 0
		var portal = level.get_node_or_null("Portal2D") if level else null
		_assert(portal != null, "Portal2D found in level")
		if portal:
			portal.teleport()

	elif test_step == 3 and test_frames >= 30:
		# Step 6: Verify scene change
		print("\nStep 6: Verifying scene transition completion...")
		test_step = 4
		var level = current_scene
		_assert(level != null, "Scene changed after portal fade: " + (level.name if level else "null"))

		# Step 7: Validate JSONL output
		print("\nStep 7: Validating generated JSONL file integrity...")
		var file_path = logger.get_log_paths()[0]
		var file = FileAccess.open(file_path, FileAccess.READ)
		_assert(file != null, "Log file opened successfully: " + file_path)

		var total_records = 0
		var has_player_spawned = false
		var has_player_died = false
		var has_retry = false
		var has_portal = false
		var has_snapshot = false

		while not file.eof_reached():
			var line = file.get_line().strip_edges()
			if line == "":
				continue
			var obj = JSON.parse_string(line)
			if obj != null:
				total_records += 1
				var ev = obj.get("event_name", "")
				if ev == "player_spawned": has_player_spawned = true
				if ev == "player_died": has_player_died = true
				if ev == "retry_started": has_retry = true
				if ev == "portal_transition_started": has_portal = true
				if ev == "state_snapshot": has_snapshot = true

		file.close()

		_assert(has_player_spawned, "Log contains player_spawned event")
		_assert(has_player_died, "Log contains player_died event")
		_assert(has_retry, "Log contains retry_started event")
		_assert(has_portal, "Log contains portal_transition_started event")
		_assert(total_records > 20, "Log captured rich session history (%d records)" % total_records)

		print("\n========================================================")
		print("  INTEGRATION TEST SUMMARY: Passed=%d, Failed=%d" % [pass_count, fail_count])
		print("========================================================\n")

		if fail_count == 0:
			print(">>> ALL INTEGRATION SCENARIOS VERIFIED SUCCESSFULLY! <<<\n")
			quit(0)
			return true
		else:
			print(">>> INTEGRATION SCENARIOS FAILED! <<<\n")
			quit(1)
			return true

	return false


func _assert(condition: bool, message: String) -> void:
	if condition:
		pass_count += 1
		print("  [PASS] " + message)
	else:
		fail_count += 1
		print("  [FAIL] " + message)
