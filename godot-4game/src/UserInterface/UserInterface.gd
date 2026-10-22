extends Node

@onready var scene_tree: SceneTree = get_tree()
@onready var score_label: Label = $Score
@onready var pause_overlay: ColorRect = $PauseOverlay
@onready var title_label: Label = $PauseOverlay/Title
@onready var main_screen_button: Button = $PauseOverlay/PauseMenu/MainScreenButton

const MESSAGE_DIED: = "You died"

var paused: = false: set = set_paused


func _ready() -> void:
	PlayerData.updated.connect(update_interface)
	PlayerData.died.connect(_on_Player_died)
	PlayerData.reset.connect(_on_Player_reset)
	update_interface()


func _on_Player_died() -> void:
	self.paused = true
	title_label.text = MESSAGE_DIED

	if GameLogger:
		GameLogger.log_event("death_overlay_shown", "ui", {
			"score": PlayerData.score if PlayerData else 0,
			"deaths": PlayerData.deaths if PlayerData else 0
		})
		GameLogger.log_event("death_menu_opened", "ui", {
			"title": MESSAGE_DIED
		})


func _on_Player_reset() -> void:
	self.paused = false


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause") and title_label.text != MESSAGE_DIED:
		self.paused = not self.paused


func update_interface() -> void:
	score_label.text = "Score: %s" % (PlayerData.score if PlayerData else 0)
	if GameLogger:
		GameLogger.log_event("score_label_updated", "ui", {
			"displayed_score": PlayerData.score if PlayerData else 0
		})


func set_paused(value: bool) -> void:
	var was_paused = paused
	paused = value
	scene_tree.paused = value
	pause_overlay.visible = value

	if GameLogger and title_label.text != MESSAGE_DIED and was_paused != value:
		if value:
			GameLogger.log_event("pause_opened", "ui", {
				"score": PlayerData.score if PlayerData else 0
			})
		else:
			GameLogger.log_event("pause_closed", "ui", {
				"score": PlayerData.score if PlayerData else 0
			})
