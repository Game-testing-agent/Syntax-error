extends Node

# MapRunner.gd — Headless & CLI dispatcher for game levels
# Parses cmdline user args (after '--') and loads the requested map.

var target_map_num: int = -1
var max_frames: int = 0
var frame_counter: int = 0
var is_debug: bool = false

const MAP_SCENES = {
	0: "res://src/Levels/Level01.tscn",
	1: "res://src/Levels/Map1_GreenHills.tscn",
	2: "res://src/Levels/Map2_UndergroundCaves.tscn",
	3: "res://src/Levels/Map3_SkyCastle.tscn",
	4: "res://src/Levels/Map4_LavaFortress.tscn"
}


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_parse_arguments()
	if target_map_num in MAP_SCENES:
		call_deferred("_load_map", target_map_num)


func _parse_arguments() -> void:
	var args = OS.get_cmdline_user_args()
	for i in range(args.size()):
		var arg = args[i]
		if arg.begins_with("--map="):
			target_map_num = int(arg.substr(6))
		elif arg == "--map" and i + 1 < args.size():
			target_map_num = int(args[i + 1])
		elif arg.begins_with("--frames="):
			max_frames = int(arg.substr(9))
		elif arg == "--frames" and i + 1 < args.size():
			max_frames = int(args[i + 1])
		elif arg == "--debug":
			is_debug = true

	if is_debug:
		print("[MapRunner] Running in DEBUG mode. Target Map: %s, Max Frames: %s" % [target_map_num, max_frames])


func _load_map(map_num: int) -> void:
	var scene_path = MAP_SCENES.get(map_num, "")
	if scene_path != "" and ResourceLoader.exists(scene_path):
		if is_debug:
			print("[MapRunner] Switching to map %d: %s" % [map_num, scene_path])
		if GameLogger:
			GameLogger.log_event("map_loaded", "scene_lifecycle", {
				"map_index": map_num,
				"scene_path": scene_path
			})
		get_tree().change_scene_to_file(scene_path)
	else:
		push_error("[MapRunner] Map scene not found for map %d: %s" % [map_num, scene_path])


func _physics_process(_delta: float) -> void:
	if max_frames > 0:
		frame_counter += 1
		if frame_counter >= max_frames:
			if is_debug:
				print("[MapRunner] Max frames (%d) reached. Quitting." % max_frames)
			get_tree().quit(0)

