extends Node3D

const DOOR = "res://SELOPackager/scenes/aed11111111111111111111111111111.tscn"
var player := CharacterBody3D.new()

func _ready():
    var instruction := Label.new()
    add_child(instruction)
    instruction.position = Vector2(16, 16)
    if not ResourceLoader.exists(DOOR):
        instruction.text = "Convert the Doorway fixture into this project, then run again."
        return
    add_child(load(DOOR).instantiate())
    instruction.text = "Arrow keys to walk. Pass between the posts or walk into one to test collision."
    var floor_body := StaticBody3D.new()
    var floor_mesh := MeshInstance3D.new()
    var floor_shape := CollisionShape3D.new()
    var box := BoxMesh.new()
    var shape := BoxShape3D.new()
    box.size = Vector3(18, 0.2, 18)
    shape.size = box.size
    floor_mesh.mesh = box
    floor_shape.shape = shape
    add_child(floor_body)
    floor_body.add_child(floor_mesh)
    floor_body.add_child(floor_shape)
    floor_body.position.y = -0.1
    add_child(player)
    player.position = Vector3(0, 0.9, 3)
    var collider := CollisionShape3D.new()
    var capsule := CapsuleShape3D.new()
    capsule.height = 1.7
    capsule.radius = 0.25
    collider.shape = capsule
    player.add_child(collider)
    var camera := Camera3D.new()
    player.add_child(camera)
    camera.position.y = 0.55
    var light := DirectionalLight3D.new()
    add_child(light)
    light.rotation_degrees = Vector3(-50, -25, 0)

func _physics_process(delta):
    if not player.is_inside_tree():
        return
    var dir := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
    player.velocity.x = dir.x * 2.5
    player.velocity.z = dir.y * 2.5
    player.velocity.y -= 12.0 * delta
    player.move_and_slide()
