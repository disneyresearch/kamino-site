import warp as wp
import newton

# Define a model builder and register solver-specific custom attributes
builder = newton.ModelBuilder(up_axis=newton.Axis.Z)
newton.solvers.SolverKamino.register_custom_attributes(builder)

# Load the model from a USD file
asset_path = newton.utils.download_asset("disneyresearch")
asset_file = str(asset_path / "dr_legs/usd/dr_legs_with_meshes_and_boxes.usda")
builder.add_usd(
    asset_file,
    force_position_velocity_actuation=True,
    enable_self_collisions=False,
    hide_collision_shapes=True,
)

# Add a global ground plane applied to all worlds
builder.add_ground_plane()

# Create the model, skipping joint validation to allow for kinematic loops
model = builder.finalize()

# Create the Kamino solver for the given model
config = newton.solvers.SolverKamino.Config.from_model(model)
solver = newton.solvers.SolverKamino(model, config=config)

# Create state, control, and contact data containers
state_0 = model.state()
state_1 = model.state()
control = model.control()
collision_pipeline = newton.CollisionPipeline(model)
contacts = collision_pipeline.contacts()

# Reset the state to a valid initial configuration above the ground plane
base_q = wp.array([wp.transformf((0.0, 0.0, 0.4), wp.quat_identity(dtype=wp.float32))], dtype=wp.transformf)
reset_config = newton.solvers.SolverKamino.ResetConfig(
    base_pose=newton.solvers.SolverKamino.ResetConfig.FromBaseQ(base_q=base_q),
)
solver.reset(state=state_0, config=reset_config)

# Run the simulation
sim_dt = 0.01
for _ in range(1000):
    state_0.clear_forces()
    collision_pipeline.collide(state_0, contacts)
    solver.step(state_0, state_1, control, contacts, sim_dt)
    state_0, state_1 = state_1, state_0
