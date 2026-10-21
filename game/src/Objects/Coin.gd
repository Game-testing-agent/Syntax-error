extends Area2D


onready var anim_player: AnimationPlayer = $AnimationPlayer

export var score: = 100


func _ready() -> void:
	add_to_group("coins")


func _on_body_entered(body: PhysicsBody2D) -> void:
	picked()


func picked() -> void:
	remove_from_group("coins")
	if has_node("/root/GameLogger"):
		get_node("/root/GameLogger").log_coin_collected(global_position, score)
	PlayerData.score += score
	anim_player.play("picked")
