extends Control

@onready var result: Label = $Result


func _ready() -> void:
	result.text = result.text % [PlayerData.score if PlayerData else 0, PlayerData.deaths if PlayerData else 0]
	if GameLogger:
		GameLogger.log_lifecycle("end_screen_loaded", {
			"final_score": PlayerData.score if PlayerData else 0,
			"final_deaths": PlayerData.deaths if PlayerData else 0
		})
