extends SceneTree

func _initialize():
    call_deferred("check")

func check():
    var placed = load("res://Placed.tscn").instantiate()
    root.add_child(placed)
    await physics_frame
    await physics_frame
    var doorway = placed.get_node("Doorway")
    var left = doorway.get_node("Left")
    var right = doorway.get_node("Right")
    var mat = left.get_node("_Mesh").get_surface_override_material(0)
    var expected = float(OS.get_environment("EXPECTED_RED"))
    var problems = []
    if mat == null or mat != right.get_node("_Mesh").get_surface_override_material(0):
        problems.append("Shared material identity")
    elif not is_equal_approx(mat.albedo_color.r, expected):
        problems.append("Reimported material color")
    if not left.position.is_equal_approx(Vector3(-1, 1, 0)) or not left.scale.is_equal_approx(Vector3(.4, 2, .5)):
        problems.append("Doorway dimensions")
    var world = doorway.get_world_3d().direct_space_state
    for x in [-1.0, 0.0, 1.0]:
        var ray = PhysicsRayQueryParameters3D.create(Vector3(x, 1, 2), Vector3(x, 1, -2))
        if world.intersect_ray(ray).is_empty() != (x == 0):
            problems.append("Door opening collision at x=%s" % x)
    if problems:
        push_error(str(problems))
        quit(1)
    else:
        print("Placed doorway passed geometry, material and physics checks")
        quit(0)
