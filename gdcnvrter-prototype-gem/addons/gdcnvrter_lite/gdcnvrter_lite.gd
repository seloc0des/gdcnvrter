@tool
extends EditorPlugin

var dock: VBoxContainer
var pkg_input: LineEdit
var prefab_select: OptionButton
var report_box: RichTextLabel
var status_label: Label
var python_bin: String = "python3"
var converter_module: String = "gdcnvrter.cli"


func _enter_tree() -> void:
	dock = VBoxContainer.new()
	dock.name = "SELODev Converter (Lite)"

	var title := Label.new()
	title.text = "SELODev UnityPackage Converter (Lite)"
	dock.add_child(title)

	pkg_input = LineEdit.new()
	pkg_input.placeholder_text = "Path to .unitypackage"
	dock.add_child(pkg_input)

	var scan_btn := Button.new()
	scan_btn.text = "Scan Package"
	scan_btn.pressed.connect(_on_scan_pressed)
	dock.add_child(scan_btn)

	prefab_select = OptionButton.new()
	dock.add_child(prefab_select)

	var convert_btn := Button.new()
	convert_btn.text = "Convert Selected Prefab (Lite)"
	convert_btn.pressed.connect(_on_convert_pressed)
	dock.add_child(convert_btn)

	status_label = Label.new()
	status_label.text = "Ready."
	dock.add_child(status_label)

	report_box = RichTextLabel.new()
	report_box.custom_minimum_size = Vector2(0, 180)
	dock.add_child(report_box)

	add_control_to_dock(DOCK_SLOT_RIGHT_UL, dock)


func _exit_tree() -> void:
	if dock:
		remove_control_from_dock(dock)
		dock.queue_free()


func _on_scan_pressed() -> void:
	var pkg_path := pkg_input.text.strip_edges()
	if pkg_path.is_empty():
		status_label.text = "Enter a .unitypackage path first."
		return
	var output := []
	var exit_code := OS.execute(python_bin, ["-m", converter_module, "scan", pkg_path, "--json"], output, true)
	if exit_code != 0 or output.is_empty():
		status_label.text = "Scan failed. Verify python3 and gdcnvrter are installed."
		return
	var parsed = JSON.parse_string("\n".join(output))
	if typeof(parsed) != TYPE_DICTIONARY:
		status_label.text = "Could not parse scan output."
		return
	prefab_select.clear()
	for p in parsed.get("prefabs", []):
		prefab_select.add_item("%s (%s)" % [p["name"], p["status"]])
		prefab_select.set_item_metadata(prefab_select.item_count - 1, p["name"])
	status_label.text = "Scanned %d prefabs (%d full, %d partial, %d skipped)." % [
		parsed.get("total_prefabs", 0),
		parsed.get("fully_converted", 0),
		parsed.get("partially_converted", 0),
		parsed.get("skipped", 0),
	]
	report_box.text = JSON.stringify(parsed, "  ")


func _on_convert_pressed() -> void:
	var pkg_path := pkg_input.text.strip_edges()
	if pkg_path.is_empty() or prefab_select.selected < 0:
		status_label.text = "Scan a package and select one prefab first."
		return
	var prefab_name: String = str(prefab_select.get_item_metadata(prefab_select.selected))
	var out_dir := ProjectSettings.globalize_path("res://imported_unity")
	var output := []
	var exit_code := OS.execute(
		python_bin,
		["-m", converter_module, "convert", pkg_path, "--out", out_dir, "--prefab", prefab_name],
		output,
		true
	)
	if exit_code == 0:
		EditorInterface.get_resource_filesystem().scan()
		status_label.text = "Converted '%s' into res://imported_unity." % prefab_name
	else:
		status_label.text = "Conversion failed."
