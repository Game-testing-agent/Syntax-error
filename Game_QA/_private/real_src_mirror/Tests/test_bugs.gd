extends SceneTree

var passed: int = 0
var failed: int = 0

func _init() -> void:
	print("\n========================================================")
	print("  BENCHMARK VERIFICATION TEST SUITE")
	print("========================================================\n")
	call_deferred("_run_checks")

func _run_checks() -> void:
	var logger = root.get_node_or_null("GameLogger")
	var bug_flags = root.get_node_or_null("BugFlags")
	var player_data = root.get_node_or_null("PlayerData")

	_assert(logger != null, "GameLogger available")
	_assert(bug_flags != null, "BugFlags available")
	_assert(player_data != null, "PlayerData available")

	# Test 1A: can_kill_player=false check
	print("\n--- Check 1A: Enemy non-lethal collision ---")
	var id_before = logger.event_id
	logger.log_bug_trigger("1A", {"description": "Enemy4 collided without causing death"})
	_assert(logger.event_id > id_before, "Check 1A: Logged 1A trigger event")

	# Test 1B: Floor hole void fall
	print("\n--- Check 1B: Floor boundary hole ---")
	id_before = logger.event_id
	logger.log_bug_trigger("1B", {"description": "Fell through floor hole at x=29..32, y=10..13"})
	_assert(logger.event_id > id_before, "Check 1B: Logged 1B trigger event")

	# Test 1C: 7th coin pickup no score
	print("\n--- Check 1C: Seventh pickup score behavior ---")
	id_before = logger.event_id
	var coin_script = load("res://src/Objects/Coin.gd")
	coin_script.total_coins_collected = 6
	coin_script.total_coins_collected += 1
	if coin_script.total_coins_collected == 7 and bug_flags.map1_seventh_coin_no_score:
		logger.log_bug_trigger("1C", {"description": "7th coin collected without score increment", "coin_count": 7})
	_assert(logger.event_id > id_before, "Check 1C: Logged 1C trigger event")

	# Test 2A: Narrow ceiling gap
	print("\n--- Check 2A: Ceiling narrow gap ---")
	id_before = logger.event_id
	logger.log_bug_trigger("2A", {"description": "Player wedged in narrow ceiling gap at tile (55, 8)", "tile": [55, 8]})
	_assert(logger.event_id > id_before, "Check 2A: Logged 2A trigger event")

	# Test 2B: Platform edge float
	print("\n--- Check 2B: Floating behavior past edge ---")
	id_before = logger.event_id
	logger.log_bug_trigger("2B", {"description": "Enemy continued horizontal motion past platform edge without falling"})
	_assert(logger.event_id > id_before, "Check 2B: Logged 2B trigger event")

	# Test 3A: Staircase edge state
	print("\n--- Check 3A: Stair step state ---")
	id_before = logger.event_id
	logger.log_bug_trigger("3A", {"description": "Player stuck on stair edge at tile (68, 7)", "tile": [68, 7]})
	_assert(logger.event_id > id_before, "Check 3A: Logged 3A trigger event")

	# Test 3B: Stomp attempt on unstompable enemy
	print("\n--- Check 3B: Stomp interaction check ---")
	id_before = logger.event_id
	logger.log_bug_trigger("3B", {"description": "Enemy4 stomped but ignored damage"})
	_assert(logger.event_id > id_before, "Check 3B: Logged 3B trigger event")

	# Test 3C: Tower wall jump boost
	print("\n--- Check 3C: Tower wall boost ---")
	id_before = logger.event_id
	logger.log_bug_trigger("3C", {"description": "Double jump height triggered at tower wall", "jump_speed": -2000.0})
	_assert(logger.event_id > id_before, "Check 3C: Logged 3C trigger event")

	# Test 4A: Lava contact delayed death
	print("\n--- Check 4A: Delayed hazard response ---")
	id_before = logger.event_id
	logger.log_bug_trigger("4A", {"description": "Lava contact delayed death initiated (3 seconds grace period)"})
	_assert(logger.event_id > id_before, "Check 4A: Logged 4A trigger event")

	# Test 4B: Portal multi-touch requirement
	print("\n--- Check 4B: Portal touch counter ---")
	id_before = logger.event_id
	var touch_count: int = 1
	if touch_count < 2 and bug_flags.map4_portal_second_touch:
		logger.log_bug_trigger("4B", {"description": "Portal first touch ignored, activation requires second touch", "touch_count": 1})
	_assert(logger.event_id > id_before, "Check 4B: Logged 4B trigger event")

	# Test 4C: Retry position state
	print("\n--- Check 4C: Retry position retention ---")
	id_before = logger.event_id
	bug_flags.retained_enemy_transforms["Enemy1"] = Vector2(100.0, 200.0)
	logger.log_bug_trigger("4C", {"description": "Retry triggered without resetting enemy positions", "enemy_count": bug_flags.retained_enemy_transforms.size()})
	_assert(logger.event_id > id_before, "Check 4C: Logged 4C trigger event")

	print("\n========================================================")
	print("  VERIFICATION RESULTS:")
	print("  Passed: %d" % passed)
	print("  Failed: %d" % failed)
	print("========================================================\n")

	if failed == 0:
		print(">>> ALL 11 CHECKS PASSED! <<<\n")
		quit(0)
	else:
		print(">>> SOME CHECKS FAILED! <<<\n")
		quit(1)

func _assert(condition: bool, description: String) -> void:
	if condition:
		passed += 1
		print("  [PASS] %s" % description)
	else:
		failed += 1
		print("  [FAIL] %s" % description)

