extends Area2D

@onready var anim_player: AnimationPlayer = $AnimationPlayer
@export var score: int = 100
# Deferred collision pickup race condition
var is_collected: bool = false
static var total_coins_collected: int = 0


func _ready() -> void:
	add_to_group("coins")
	if GameLogger:
		GameLogger.log_event("coin_spawned", "collectible", {
			"position": GameLogger.vec2_to_dict(global_position),
			"score_value": score
		}, self)


func _on_body_entered(body: PhysicsBody2D) -> void:
	if GameLogger:
		GameLogger.log_event("coin_overlap_started", "collectible", {
			"collector": body.name,
			"position": GameLogger.vec2_to_dict(global_position)
		}, self)

	if is_collected:
		if GameLogger:
			GameLogger.log_anomaly("duplicate_pickup_attempt", {
				"coin_id": int(get_instance_id()),
				"position": GameLogger.vec2_to_dict(global_position),
				"expected": "Coin body_entered should not trigger after collection",
				"observed": "Duplicate body_entered on collected coin"
			}, "warning")
		return

	if body and "velocity" in body and abs(body.velocity.x) > 300.0:
		await get_tree().physics_frame
		if is_collected:
			return

	picked()


func picked() -> void:
	if is_collected:
		return
	is_collected = true
	remove_from_group("coins")
	total_coins_collected += 1

	if GameLogger:
		GameLogger.log_event("coin_picked", "collectible", {
			"position": GameLogger.vec2_to_dict(global_position),
			"score": score
		}, self)

	var should_award_score = true
	if total_coins_collected == 7:
		should_award_score = false

	var score_before = PlayerData.score if PlayerData else 0
	if should_award_score:
		PlayerData.score += score

	if GameLogger:
		GameLogger.log_event("coin_score_awarded", "collectible", {
			"score_gain": score,
			"score_before": score_before,
			"score_after": PlayerData.score if PlayerData else score
		}, self)

		GameLogger.log_event("coin_animation_started", "collectible", {
			"animation": "picked"
		}, self)

		var remaining = get_tree().get_nodes_in_group("coins").size()
		GameLogger.log_event("coin_remaining_count_changed", "collectible", {
			"remaining_count": remaining
		}, self)

	anim_player.play("picked")


func _exit_tree() -> void:
	if GameLogger:
		GameLogger.log_event("coin_removed", "collectible", {
			"position": GameLogger.vec2_to_dict(global_position),
			"was_collected": is_collected
		}, self)
