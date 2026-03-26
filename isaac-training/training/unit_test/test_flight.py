#!/usr/bin/env python3
"""
UAV Flight Test in CRE Scene Families
=====================================
结合 Env Primitive Generator 场景与无人机飞行控制和 LiDAR 传感器。

功能:
    - 使用 Env Primitive Spec v0 驱动的场景生成器
    - 读取 `cfg/env_cfg/scene_cfg_*.yaml` 的 family-based 场景规则
    - 无人机配备 Livox Mid-360 LiDAR 传感器
    - 实时点云可视化
    - 键盘控制飞行 + nominal / boundary-critical / shifted 场景重生成

键盘控制:
    飞行控制:
        W/S     : 前进/后退 (X轴)
        A/D     : 左移/右移 (Y轴)
        Q/E     : 上升/下降 (Z轴)
        Z/X     : 左转/右转 (Yaw)
        F       : 飞向目标点
        O       : 返回起点 (仅目标位置)
        B       : 重置无人机 (位置+速度+姿态)

    场景控制:
        1/2/3   : 切换场景族 (nominal / boundary-critical / shifted)
        R       : 重新生成当前场景
        +/-     : 增加/减少难度
        G       : 开关重力倾斜

    显示控制:
        T       : 开关点云显示
        V       : 开关重力向量显示
        I       : 打印场景统计信息
        H       : 打印危险物详情
        P       : 暂停/继续动态障碍物

运行方式 (与 train.py 相同):
    conda activate NavRL
    cd /home/mint/rl_dev/NavRL/isaac-training
    
    # 默认参数运行 (从 cfg/train.yaml 读取配置)
    python training/unit_test/test_flight.py
    
    # 带可视化
    python3 training/unit_test/test_flight.py headless=False
    
    # 自定义 LiDAR 参数
    python training/unit_test/test_flight.py headless=False sensor.lidar_range=30
    
    # 使用不同无人机模型
    python training/unit_test/test_flight.py drone.model_name=Firefly

Author: NavRL Team
"""

import gc
import os
import sys
import math
import time
import hydra
from omegaconf import DictConfig

# ============================================================================
# Path Setup (MUST be before any imports)
# ============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRAINING_ROOT = os.path.dirname(SCRIPT_DIR)
SCRIPTS_PATH = os.path.join(TRAINING_ROOT, "scripts")
ENVS_PATH = os.path.join(TRAINING_ROOT, "envs")
MODULE_PATH = os.path.join(TRAINING_ROOT, "envs", "env_gen.py")
LOGGER_MODULE_PATH = os.path.join(TRAINING_ROOT, "runtime_logging", "logger.py")
CFG_PATH = os.path.join(TRAINING_ROOT, "cfg")
LOG_DIR = os.path.join(TRAINING_ROOT, "logs")

if TRAINING_ROOT not in sys.path:
    sys.path.insert(0, TRAINING_ROOT)
if SCRIPTS_PATH not in sys.path:
    sys.path.insert(0, SCRIPTS_PATH)
if ENVS_PATH not in sys.path:
    sys.path.insert(0, ENVS_PATH)


def _load_local_module(name: str, path: str):
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _headless_explicitly_set() -> bool:
    """Return True when headless is explicitly overridden on the CLI."""
    for arg in sys.argv[1:]:
        normalized = arg.lstrip("+")
        if normalized.startswith("headless="):
            return True
    return False


def _can_try_gui() -> bool:
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _warmup_simulation_app(simulation_app, steps: int = 4, sleep_s: float = 0.05) -> None:
    """Warm up Kit/renderer before SimulationContext creation.

    Several Isaac Sim examples do one or more `simulation_app.update()` calls
    before stage initialization. This reduces crashes inside
    `SimulationContext._init_stage -> render -> app.update()` on some GUI setups.
    """
    for _ in range(max(1, steps)):
        simulation_app.update()
        if sleep_s > 0.0:
            time.sleep(sleep_s)


@hydra.main(config_path=CFG_PATH, config_name="train", version_base=None)
def main(cfg: DictConfig):
    """Main function - all imports happen here after SimulationApp

    Args:
        cfg: Hydra configuration object (from train.yaml)
    """
    effective_headless = cfg.headless if _headless_explicitly_set() else False
    if not effective_headless and not _can_try_gui():
        print("[WARN] No GUI display detected; forcing headless=True for stability.")
        effective_headless = True

    # =========================================================================
    # Step 1: Launch Isaac Sim (MUST be first before any omni/pxr imports)
    # =========================================================================
    print("=" * 70)
    print("🚁 UAV Flight Test in CRE Scene Families")
    print("=" * 70)
    print(f"[INFO] Headless mode: {effective_headless}")
    print(f"[INFO] Device: {cfg.device}")
    print(f"[INFO] LiDAR range: {cfg.sensor.lidar_range} m")
    print(f"[INFO] Vertical FOV: {cfg.sensor.lidar_vfov}")
    print(f"[INFO] Vertical beams: {cfg.sensor.lidar_vbeams}")
    print(f"[INFO] Horizontal resolution: {cfg.sensor.lidar_hres}°")
    print(f"[INFO] LiDAR mount pitch: {cfg.sensor.lidar_mount_pitch}°")
    print(f"[INFO] Drone model: {cfg.drone.model_name}")
    print("-" * 70)
    print("[INFO] Launching Isaac Sim...")

    from omni.isaac.kit import SimulationApp
    simulation_app = SimulationApp({
        "headless": effective_headless,
        "width": 1920,
        "height": 1080,
        "anti_aliasing": 1,
    })

    print("[INFO] Warming up Isaac Sim before SimulationContext init...")
    _warmup_simulation_app(
        simulation_app,
        steps=2 if effective_headless else 5,
        sleep_s=0.02 if effective_headless else 0.05,
    )

    # =========================================================================
    # Step 2: Import dependencies (AFTER SimulationApp is created)
    # =========================================================================
    print("[INFO] Importing dependencies...")

    import torch
    import numpy as np
    import carb
    import carb.input
    import omni
    import omni.appwindow
    import omni.isaac.core.utils.prims as prim_utils
    from omni.isaac.core.simulation_context import SimulationContext
    from omni.isaac.debug_draw import _debug_draw
    from omni.isaac.orbit.sensors import RayCaster, RayCasterCfg, patterns
    from omni_drones.robots.drone import MultirotorBase
    from omni_drones.controllers import LeePositionController
    from pxr import Usd, UsdGeom, Gf, UsdLux

    # Import the generator module
    generator_module = _load_local_module("env_gen", MODULE_PATH)
    logging_module = _load_local_module("runtime_logging_logger", LOGGER_MODULE_PATH)

    UniversalArenaGenerator = generator_module.UniversalArenaGenerator
    ArenaSpawner = generator_module.ArenaSpawner
    ArenaMode = generator_module.ArenaMode
    ArenaConfig = generator_module.ArenaConfig
    CREScenarioFamily = generator_module.CREScenarioFamily
    FAMILY_TO_SCENE_CFG = generator_module.FAMILY_TO_SCENE_CFG
    create_run_logger = logging_module.create_run_logger
    normalize_reward_components = logging_module.normalize_reward_components
    run_acceptance_check = logging_module.run_acceptance_check

    print("[INFO] Dependencies loaded successfully")

    # =========================================================================
    # Step 3: Create Simulation Context
    # =========================================================================
    print("[INFO] Creating simulation context...")

    sim_context = SimulationContext(
        stage_units_in_meters=1.0,
        physics_dt=0.02,
        rendering_dt=0.02,
        backend="torch",
        device=cfg.device,
    )
    stage = sim_context.stage
    device = cfg.device

    # =========================================================================
    # Step 4: Create Base Scene (Ground, Light)
    # =========================================================================
    print("[INFO] Creating base scene...")

    # Ground plane (large enough for arena)
    ground_path = "/World/GroundPlane"
    ground = UsdGeom.Mesh.Define(stage, ground_path)
    ground.CreatePointsAttr(
        [(-50, -50, 0), (50, -50, 0), (50, 50, 0), (-50, 50, 0)])
    ground.CreateFaceVertexCountsAttr([4])
    ground.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    ground.CreateDisplayColorAttr([(0.15, 0.15, 0.18)])

    # Dome Light (ambient/environment lighting)
    dome_light = UsdLux.DomeLight.Define(stage, "/World/DomeLight")
    dome_light.CreateIntensityAttr(800.0)
    dome_light.CreateColorAttr(Gf.Vec3f(0.9, 0.9, 1.0))

    # Distant Light (sun-like directional light)
    distant_light = UsdLux.DistantLight.Define(stage, "/World/DistantLight")
    distant_light.CreateIntensityAttr(3000.0)
    distant_light.CreateColorAttr(Gf.Vec3f(1.0, 0.98, 0.95))
    distant_light.CreateAngleAttr(1.0)
    xf = UsdGeom.Xformable(distant_light.GetPrim())
    xf.ClearXformOpOrder()
    xf.AddRotateXYZOp().Set(Gf.Vec3d(-45, 30, 0))

    # Sphere Light (fill light above arena)
    sphere_light = UsdLux.SphereLight.Define(stage, "/World/SphereLight")
    sphere_light.CreateIntensityAttr(5000.0)
    sphere_light.CreateColorAttr(Gf.Vec3f(1.0, 1.0, 1.0))
    sphere_light.CreateRadiusAttr(0.5)
    xf = UsdGeom.Xformable(sphere_light.GetPrim())
    xf.ClearXformOpOrder()
    xf.AddTranslateOp().Set(Gf.Vec3d(0, 0, 12))

    print("[INFO] Lighting configured")

    arena_cfg = ArenaConfig()

    # Arena boundary markers (corners)
    half_x = arena_cfg.size_x / 2.0
    half_y = arena_cfg.size_y / 2.0
    for i, (cx, cy) in enumerate([(-half_x, -half_y), (half_x, -half_y), (half_x, half_y), (-half_x, half_y)]):
        marker = UsdGeom.Cylinder.Define(stage, f"/World/BoundaryMarker_{i}")
        xform = UsdGeom.Xformable(marker.GetPrim())
        xform.ClearXformOpOrder()
        xform.AddTranslateOp().Set(Gf.Vec3d(cx, cy, 0.1))
        xform.AddScaleOp().Set(Gf.Vec3d(0.15, 0.15, 0.15))
        marker.CreateDisplayColorAttr([(0.8, 0.8, 0.2)])

    # =========================================================================
    # Step 5: Create Start/Goal Markers
    # =========================================================================
    # Start marker (green sphere)
    start_marker = UsdGeom.Sphere.Define(stage, "/World/StartMarker")
    xf = UsdGeom.Xformable(start_marker.GetPrim())
    xf.ClearXformOpOrder()
    xf.AddTranslateOp().Set(Gf.Vec3d(*arena_cfg.start_pos))
    xf.AddScaleOp().Set(Gf.Vec3d(0.25, 0.25, 0.25))
    start_marker.CreateDisplayColorAttr([(0.2, 0.9, 0.2)])

    # Goal marker (red sphere)
    goal_marker = UsdGeom.Sphere.Define(stage, "/World/GoalMarker")
    xf = UsdGeom.Xformable(goal_marker.GetPrim())
    xf.ClearXformOpOrder()
    xf.AddTranslateOp().Set(Gf.Vec3d(*arena_cfg.goal_pos))
    xf.AddScaleOp().Set(Gf.Vec3d(0.25, 0.25, 0.25))
    goal_marker.CreateDisplayColorAttr([(0.9, 0.2, 0.2)])

    # =========================================================================
    # Step 6: Create UAV
    # =========================================================================
    print("[INFO] Creating UAV...")

    # Create environment prim for drone
    if not prim_utils.is_prim_path_valid("/World/envs/env_0"):
        prim_utils.define_prim("/World/envs/env_0")

    # Use drone model from config
    model_name = cfg.drone.model_name
    if model_name not in MultirotorBase.REGISTRY:
        print(
            f"[WARNING] Model '{model_name}' not found in registry, using 'Hummingbird'")
        model_name = "Hummingbird"

    drone_model = MultirotorBase.REGISTRY[model_name]
    drone_cfg = drone_model.cfg_cls(force_sensor=False)
    drone = drone_model(cfg=drone_cfg)

    # Spawn drone at start position
    init_pos = arena_cfg.start_pos
    drone.spawn(translations=[(init_pos[0], init_pos[1], init_pos[2])])

    print(f"[INFO] UAV '{model_name}' created at {init_pos}")

    # =========================================================================
    # Step 7: Initialize Simulation and Drone
    # =========================================================================
    print("[INFO] Initializing physics...")
    sim_context.reset()
    drone.initialize()

    # =========================================================================
    # Step 8: Initialize Arena Generator and Spawner
    # =========================================================================
    print("[INFO] Initializing arena generator...")

    generator = UniversalArenaGenerator(arena_cfg, seed=42)
    spawner = ArenaSpawner(stage, base_path="/World/Arena")

    # =========================================================================
    # Step 9: Prepare LiDAR parameters (sensor will be built after arena spawn)
    # =========================================================================
    print("[INFO] Preparing Livox Mid-360 LiDAR...")

    # LiDAR parameters from config
    lidar_range = cfg.sensor.lidar_range
    lidar_vfov = cfg.sensor.lidar_vfov
    lidar_vbeams = cfg.sensor.lidar_vbeams
    lidar_hres = cfg.sensor.lidar_hres

    vertical_angles = torch.linspace(
        lidar_vfov[0], lidar_vfov[1], lidar_vbeams
    ).tolist()

    # Get drone base_link path
    drone_base_link = f"/World/envs/env_0/{model_name}_0/base_link"

    lidar = None
    lidar_initialized = False
    lidar_scan_mesh_path = "/World/LidarScanMesh"
    dynamic_lidar_refresh_interval = 10

    print(f"[INFO] LiDAR parameters ready (will initialize after arena spawn)")

    # =========================================================================
    # Step 10: Create Position Controller
    # =========================================================================
    print("[INFO] Creating flight controller...")

    controller = LeePositionController(
        g=9.81, uav_params=drone.params
    ).to(device)

    # =========================================================================
    # Step 11: Initialize Debug Draw
    # =========================================================================
    debug_draw = _debug_draw.acquire_debug_draw_interface()

    # =========================================================================
    # Step 12: State Variables
    # =========================================================================
    family_names = {
        CREScenarioFamily.NOMINAL: "Nominal",
        CREScenarioFamily.BOUNDARY_CRITICAL: "Boundary Critical",
        CREScenarioFamily.SHIFTED: "Shifted",
    }

    # Arena state
    current_family = CREScenarioFamily.NOMINAL
    current_difficulty = 0.5
    current_result = None
    apply_gravity_tilt = False  # Start with no tilt for easier flight
    paused = False
    current_seed = 42
    regeneration_index = 0
    episode_index = 0
    test_flight_cfg = cfg.get("test_flight", {})
    auto_exit_steps = int(test_flight_cfg.get("auto_exit_steps", 0) or 0)
    auto_goal_on_start = bool(test_flight_cfg.get("auto_goal_on_start", False))
    auto_acceptance_on_exit = bool(test_flight_cfg.get("auto_acceptance_on_exit", True))
    episode_logger = create_run_logger(
        source="test_flight",
        run_name="test_flight",
        base_dir=LOG_DIR,
        near_violation_distance=0.5,
    )

    # Flight state
    target_pos = torch.tensor(
        [init_pos[0], init_pos[1], init_pos[2]],
        device=device, dtype=torch.float32
    )
    target_yaw = torch.tensor([0.0], device=device)
    move_speed = 0.05
    yaw_speed = 0.02

    # Visualization state
    show_pointcloud = True
    show_gravity_vector = True
    point_size = 4.0

    # Simulation state
    sim_time = 0.0
    dt = sim_context.get_physics_dt()

    # =========================================================================
    # Step 13: Keyboard Input Setup
    # =========================================================================
    appwindow = omni.appwindow.get_default_app_window()
    input_interface = carb.input.acquire_input_interface()
    keyboard = appwindow.get_keyboard()
    key_pressed = {}

    def on_keyboard_event(event):
        if event.type == carb.input.KeyboardEventType.KEY_PRESS:
            key_pressed[event.input] = True
        elif event.type == carb.input.KeyboardEventType.KEY_RELEASE:
            key_pressed[event.input] = False
        return True

    keyboard_sub = input_interface.subscribe_to_keyboard_events(
        keyboard, on_keyboard_event)

    # =========================================================================
    # Step 14: Helper Functions
    # =========================================================================
    def get_scene_tags():
        if current_result is None or current_result.cre_metadata is None:
            return {}
        return dict(current_result.cre_metadata.scene_tags)

    def get_scene_id():
        return str(get_scene_tags().get("scene_id", ""))

    def get_scenario_type():
        if current_result is None or current_result.cre_metadata is None:
            return ""
        return str(current_result.cre_metadata.family)

    def get_scene_cfg_name():
        scene_cfg_name = get_scene_tags().get("scene_cfg_name")
        if scene_cfg_name:
            return str(scene_cfg_name)
        preferred = FAMILY_TO_SCENE_CFG.get(current_family, "scene_cfg_base.yaml")
        cfg_path = os.path.join(CFG_PATH, "env_cfg", preferred)
        return preferred if os.path.exists(cfg_path) else f"{preferred} (fallback to scene_cfg_base.yaml)"

    def get_drone_state_vector():
        raw_state = drone.get_state()
        if raw_state.dim() == 3:
            return raw_state[0, 0, :13]
        if raw_state.dim() == 2:
            return raw_state[0, :13]
        return raw_state[:13]

    def compute_goal_distance(position):
        if current_result is None:
            return None
        if current_result.labels.local_goal:
            goal = current_result.labels.local_goal
        else:
            goal = arena_cfg.goal_pos
        return math.sqrt(
            (float(position[0]) - goal[0]) ** 2 +
            (float(position[1]) - goal[1]) ** 2 +
            (float(position[2]) - goal[2]) ** 2
        )

    def compute_proximity_metrics(ray_hits, lidar_pos):
        if ray_hits is None or lidar_pos is None:
            return 0, None

        distances = (ray_hits - lidar_pos.unsqueeze(1)).norm(dim=-1)
        valid_mask = distances < lidar_range
        num_hits = valid_mask.sum().item()
        if num_hits > 0:
            min_dist = float(distances[valid_mask].min().item())
        else:
            min_dist = None
        return num_hits, min_dist

    def export_episode_log(reason: str):
        nonlocal episode_index

        if not episode_logger.has_steps():
            return

        episode_summary = episode_logger.finalize_episode(done_type=reason)
        print(
            f"[INFO] Episode log exported: {episode_logger.run_dir} | "
            f"done_type={episode_summary.get('done_type')}"
        )
        episode_index += 1

    def update_endpoint_markers(result):
        """Update start/goal markers based on arena result."""
        if result.labels.local_start:
            start_pos = result.labels.local_start
        else:
            start_pos = arena_cfg.start_pos

        if result.labels.local_goal:
            goal_pos = result.labels.local_goal
        else:
            goal_pos = arena_cfg.goal_pos

        # Update start marker
        start_prim = stage.GetPrimAtPath("/World/StartMarker")
        if start_prim:
            xf = UsdGeom.Xformable(start_prim)
            xf.ClearXformOpOrder()
            xf.AddTranslateOp().Set(Gf.Vec3d(*start_pos))
            xf.AddScaleOp().Set(Gf.Vec3d(0.25, 0.25, 0.25))

        # Update goal marker
        goal_prim = stage.GetPrimAtPath("/World/GoalMarker")
        if goal_prim:
            xf = UsdGeom.Xformable(goal_prim)
            xf.ClearXformOpOrder()
            xf.AddTranslateOp().Set(Gf.Vec3d(*goal_pos))
            xf.AddScaleOp().Set(Gf.Vec3d(0.25, 0.25, 0.25))

        return start_pos, goal_pos

    def _append_triangles(points_out, counts_out, indices_out, verts, tri_faces):
        base = len(points_out)
        points_out.extend(verts)
        for a, b, c in tri_faces:
            counts_out.append(3)
            indices_out.extend([base + a, base + b, base + c])

    def _transform_vertices(world_mat, verts):
        out = []
        for vx, vy, vz in verts:
            p = world_mat.Transform(Gf.Vec3d(float(vx), float(vy), float(vz)))
            out.append((float(p[0]), float(p[1]), float(p[2])))
        return out

    def _cube_mesh_local():
        verts = [
            (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
            (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
        ]
        tris = [
            (0, 1, 2), (0, 2, 3),
            (4, 6, 5), (4, 7, 6),
            (0, 4, 5), (0, 5, 1),
            (1, 5, 6), (1, 6, 2),
            (2, 6, 7), (2, 7, 3),
            (3, 7, 4), (3, 4, 0),
        ]
        return verts, tris

    def _cylinder_mesh_local(segments: int = 16):
        verts = [(0.0, 0.0, 1.0), (0.0, 0.0, -1.0)]
        tris = []
        for i in range(segments):
            a = 2.0 * math.pi * i / segments
            x = math.cos(a)
            y = math.sin(a)
            verts.append((x, y, 1.0))
            verts.append((x, y, -1.0))

        for i in range(segments):
            i2 = (i + 1) % segments
            top_i = 2 + 2 * i
            bot_i = top_i + 1
            top_n = 2 + 2 * i2
            bot_n = top_n + 1

            tris.append((top_i, bot_i, bot_n))
            tris.append((top_i, bot_n, top_n))
            tris.append((0, top_n, top_i))
            tris.append((1, bot_i, bot_n))
        return verts, tris

    def _sphere_mesh_local(lat: int = 8, lon: int = 16):
        verts = []
        tris = []
        for i in range(lat + 1):
            phi = math.pi * i / lat
            z = math.cos(phi)
            r = math.sin(phi)
            for j in range(lon):
                th = 2.0 * math.pi * j / lon
                x = r * math.cos(th)
                y = r * math.sin(th)
                verts.append((x, y, z))

        def vid(i, j):
            return i * lon + (j % lon)

        for i in range(lat):
            for j in range(lon):
                a = vid(i, j)
                b = vid(i + 1, j)
                c = vid(i + 1, j + 1)
                d = vid(i, j + 1)
                if i > 0:
                    tris.append((a, b, d))
                if i < lat - 1:
                    tris.append((b, c, d))
        return verts, tris

    def _build_lidar_scan_mesh():
        nonlocal lidar_scan_mesh_path

        if stage.GetPrimAtPath(lidar_scan_mesh_path).IsValid():
            stage.RemovePrim(lidar_scan_mesh_path)

        mesh = UsdGeom.Mesh.Define(stage, lidar_scan_mesh_path)
        points = []
        counts = []
        indices = []

        # Include ground mesh triangles
        ground_prim = stage.GetPrimAtPath(ground_path)
        if ground_prim.IsValid() and ground_prim.GetTypeName() == "Mesh":
            gmesh = UsdGeom.Mesh(ground_prim)
            g_points = gmesh.GetPointsAttr().Get() or []
            g_counts = gmesh.GetFaceVertexCountsAttr().Get() or []
            g_indices = gmesh.GetFaceVertexIndicesAttr().Get() or []
            base = len(points)
            points.extend([(float(p[0]), float(p[1]), float(p[2])) for p in g_points])
            cursor = 0
            for fc in g_counts:
                face = [base + int(i) for i in g_indices[cursor: cursor + fc]]
                cursor += fc
                if len(face) < 3:
                    continue
                for k in range(1, len(face) - 1):
                    counts.append(3)
                    indices.extend([face[0], face[k], face[k + 1]])

        # Include all arena obstacles as triangulated proxy geometry
        xform_cache = UsdGeom.XformCache(Usd.TimeCode.Default())
        for prim_path in spawner.spawned_prims:
            prim = stage.GetPrimAtPath(prim_path)
            if not prim.IsValid():
                continue

            prim_type = prim.GetTypeName()
            if prim_type == "Cube":
                verts, tris = _cube_mesh_local()
            elif prim_type == "Cylinder":
                verts, tris = _cylinder_mesh_local(segments=16)
            elif prim_type == "Sphere":
                verts, tris = _sphere_mesh_local(lat=8, lon=16)
            else:
                continue

            world_mat = xform_cache.GetLocalToWorldTransform(prim)
            verts_world = _transform_vertices(world_mat, verts)
            _append_triangles(points, counts, indices, verts_world, tris)

        mesh.CreatePointsAttr(points)
        mesh.CreateFaceVertexCountsAttr(counts)
        mesh.CreateFaceVertexIndicesAttr(indices)

        return lidar_scan_mesh_path, len(counts)

    def _rebuild_lidar_sensor():
        nonlocal lidar, lidar_initialized

        mesh_path, tri_count = _build_lidar_scan_mesh()

        # RayCaster caches warp mesh by path; clear cache to reload updated mesh geometry.
        if mesh_path in RayCaster.meshes:
            RayCaster.meshes.pop(mesh_path, None)

        ray_caster_cfg = RayCasterCfg(
            prim_path=drone_base_link,
            offset=RayCasterCfg.OffsetCfg(pos=(0.0, 0.0, 0.0)),
            attach_yaw_only=False,
            pattern_cfg=patterns.BpearlPatternCfg(
                horizontal_fov=360.0,
                horizontal_res=lidar_hres,
                vertical_ray_angles=vertical_angles,
            ),
            max_distance=lidar_range,
            mesh_prim_paths=[mesh_path],
            debug_vis=False,
        )

        lidar = RayCaster(ray_caster_cfg)
        lidar._initialize_impl()
        lidar_initialized = True
        print(
            f"[INFO] LiDAR rebuilt on merged scene mesh: {mesh_path} | "
            f"triangles={tri_count} | obstacles={len(spawner.spawned_prims)}"
        )

    def regenerate_arena():
        nonlocal current_result, sim_time, target_pos, current_seed, regeneration_index

        print(f"\n{'='*60}")
        print(f"Generating: {family_names[current_family]}")
        print(f"Scene config: {get_scene_cfg_name()}")
        print(f"Difficulty: {current_difficulty:.2f}")
        print(f"Gravity Tilt: {'ON' if apply_gravity_tilt else 'OFF'}")
        print(f"{'='*60}")

        export_episode_log("regen")

        current_seed = 42 + regeneration_index
        regeneration_index += 1

        generator.cfg = arena_cfg
        current_result = generator.generate_from_scene_family(
            scene_family=current_family,
            seed=current_seed,
            difficulty=current_difficulty,
            gravity_tilt_enabled=apply_gravity_tilt,
        )

        # Spawn obstacles
        spawner.spawn(current_result)

        # Update markers and get positions
        start_pos, goal_pos = update_endpoint_markers(current_result)

        # Move drone to start position
        target_pos[0] = start_pos[0]
        target_pos[1] = start_pos[1]
        target_pos[2] = start_pos[2]

        # Print stats
        result = current_result
        summary = generator.summarize_result(result)
        print(f"Seed: {current_seed}")
        print(f"Scene family: {current_result.cre_metadata.family}")
        print(f"Resolved mode: {summary['mode']} / {summary['sub_mode'] or 'N/A'}")
        print(f"Obstacles: {summary['obstacle_count']}")
        print(f"Dynamic obstacles: {summary['dynamic_obstacle_count']}")
        print(f"Solvable: {result.solvable}")
        print(f"Complexity: {result.complexity:.3f}")
        print(f"Estimated min gap: {summary['estimated_min_gap']}")
        print(
            f"Tilt: roll={result.gravity_tilt_euler[0]:.1f}°, pitch={result.gravity_tilt_euler[1]:.1f}°")
        print(f"Start: {start_pos}, Goal: {goal_pos}")

        _rebuild_lidar_sensor()

        episode_logger.reset(
            episode_index=episode_index,
            seed=current_seed,
            scene_id=get_scene_id(),
            scenario_type=get_scenario_type(),
            scene_cfg_name=get_scene_cfg_name(),
            scene_tags=get_scene_tags(),
        )
        if auto_goal_on_start and current_result and current_result.labels.local_goal:
            goal = current_result.labels.local_goal
            target_pos[0] = goal[0]
            target_pos[1] = goal[1]
            target_pos[2] = goal[2]
        sim_time = 0.0

    def draw_gravity_vector():
        """Draw gravity vector visualization."""
        if not show_gravity_vector or current_result is None:
            return

        q = current_result.gravity_tilt_quat
        w, x, y, z = q

        # Standard gravity rotated by quaternion
        gx = -2 * (x * z - w * y)
        gy = -2 * (y * z + w * x)
        gz = -(1 - 2 * (x * x + y * y))

        # Normalize
        mag = math.sqrt(gx * gx + gy * gy + gz * gz)
        if mag > 0:
            gx, gy, gz = gx / mag, gy / mag, gz / mag

        # Draw from above arena
        origin = (0, 0, 5.0)
        endpoint = (origin[0] + gx * 2, origin[1] + gy * 2, origin[2] + gz * 2)

        debug_draw.draw_lines([origin], [endpoint],
                              [(1.0, 0.7, 0.0, 1.0)], [5])

    def draw_pointcloud(ray_hits, lidar_pos):
        """Draw LiDAR point cloud with distance-based coloring."""
        if not show_pointcloud:
            return

        if ray_hits is None or lidar_pos is None:
            return

        distances = (ray_hits - lidar_pos.unsqueeze(1)).norm(dim=-1)
        valid_mask = distances[0] < lidar_range
        valid_points = ray_hits[0][valid_mask]
        valid_distances = distances[0][valid_mask]

        if len(valid_points) == 0:
            return

        points_np = valid_points.cpu().numpy()
        dists_np = valid_distances.cpu().numpy()
        norm_dists = dists_np / lidar_range

        colors = []
        for d in norm_dists:
            if d < 0.25:
                colors.append((1.0, 0.2, 0.2, 1.0))  # Red (close)
            elif d < 0.5:
                colors.append((1.0, 0.6, 0.2, 1.0))  # Orange
            elif d < 0.75:
                colors.append((1.0, 1.0, 0.2, 1.0))  # Yellow
            else:
                colors.append((0.2, 1.0, 0.2, 1.0))  # Green (far)

        point_list = [tuple(p) for p in points_np]
        debug_draw.draw_points(point_list, colors, [
                               point_size] * len(point_list))

    def print_stats():
        """Print arena statistics."""
        if current_result is None:
            print("No arena generated")
            return

        r = current_result
        metadata = r.cre_metadata
        print("\n" + "="*60)
        print("ARENA & FLIGHT STATISTICS")
        print("="*60)
        if metadata is not None:
            print(f"Family: {metadata.family}")
            print(f"Seed: {metadata.seed}")
        print(f"Mode: {r.mode.value}")
        print(f"Sub-mode: {r.sub_mode or 'N/A'}")
        print(f"Difficulty: {r.difficulty:.2f}")
        print(f"Solvable: {r.solvable}")
        print(f"Complexity: {r.complexity:.3f}")
        print(f"Obstacles: {len(r.obstacles)}")
        print(f"  - Static: {sum(1 for o in r.obstacles if not o.is_dynamic)}")
        print(f"  - Dynamic: {sum(1 for o in r.obstacles if o.is_dynamic)}")
        print(f"  - Hazards: {sum(1 for o in r.obstacles if o.is_hazard)}")
        if metadata is not None:
            print(f"Estimated Min Gap: {metadata.estimated_min_gap}")
            print(f"Scene Tags: {metadata.scene_tags}")
        print(
            f"Gravity Tilt: roll={r.gravity_tilt_euler[0]:.2f}°, pitch={r.gravity_tilt_euler[1]:.2f}°")

        if r.labels.local_start:
            print(
                f"Local Start: {tuple(f'{v:.2f}' for v in r.labels.local_start)}")
        if r.labels.local_goal:
            print(
                f"Local Goal: {tuple(f'{v:.2f}' for v in r.labels.local_goal)}")

        # Current drone position
        raw_state = drone.get_state()
        if raw_state.dim() == 3:
            drone_pos = raw_state[0, 0, :3]
        elif raw_state.dim() == 2:
            drone_pos = raw_state[0, :3]
        else:
            drone_pos = raw_state[:3]
        print(
            f"Drone Position: ({drone_pos[0]:.2f}, {drone_pos[1]:.2f}, {drone_pos[2]:.2f})")
        print(
            f"Target Position: ({target_pos[0]:.2f}, {target_pos[1]:.2f}, {target_pos[2]:.2f})")
        print("="*60 + "\n")

    def print_hazard_details():
        """Print hazard details for the current arena."""
        if current_result is None:
            print("No arena generated")
            return

        hazards = [o for o in current_result.obstacles if o.is_hazard]
        if not hazards:
            print("\n[INFO] No hazards in the current arena.")
            return

        print("\n" + "="*60)
        print(f"HAZARD DETAILS ({family_names[current_family]})")
        print("="*60)

        thin_wires = [h for h in hazards if h.scale[0] <= 0.015]
        thick_cables = [h for h in hazards if h.scale[0] > 0.015]

        print(f"Total hazards: {len(hazards)}")
        print(f"  - Thin wires: {len(thin_wires)}")
        print(f"  - Thick cables: {len(thick_cables)}")

        if thin_wires:
            s = thin_wires[0]
            print(f"Sample wire: pos={tuple(f'{v:.2f}' for v in s.position)}, "
                  f"r={s.scale[0]:.4f}m, color={tuple(f'{v:.2f}' for v in s.color)}")
        print("="*60 + "\n")

    # =========================================================================
    # Step 15: Initial Arena Generation
    # =========================================================================
    regenerate_arena()

    # =========================================================================
    # Step 16: Main Loop
    # =========================================================================
    print("\n" + "="*70)
    print("🎮 FLIGHT TEST RUNNING")
    print("="*70)
    print("Flight Controls:")
    print("  W/S     : Forward/Backward (X)")
    print("  A/D     : Left/Right (Y)")
    print("  Q/E     : Up/Down (Z)")
    print("  Z/X     : Yaw Left/Right")
    print("  F       : Fly to Goal")
    print("  O       : Return to Start (target only)")
    print("  B       : Reset Drone (position + velocity)")
    print("")
    print("Arena Controls:")
    print("  1/2/3   : Switch Family (1=Nominal, 2=Boundary Critical, 3=Shifted)")
    print("  R       : Regenerate current scene")
    print("  +/-     : Difficulty")
    print("  G       : Toggle Gravity Tilt")
    print("")
    print("Display:")
    print("  T       : Toggle Point Cloud")
    print("  V       : Toggle Gravity Vector")
    print("  I       : Print Stats")
    print("  H       : Hazard Details")
    print("  P       : Pause Dynamic Obstacles")
    print("  Ctrl+C  : Exit")
    print("="*70 + "\n")

    step = 0
    print_interval = 250

    try:
        while simulation_app.is_running():
            sim_time += dt

            # =================================================================
            # Handle Flight Controls
            # =================================================================
            # Movement
            if key_pressed.get(carb.input.KeyboardInput.W, False):
                target_pos[0] += move_speed
            if key_pressed.get(carb.input.KeyboardInput.S, False):
                target_pos[0] -= move_speed
            if key_pressed.get(carb.input.KeyboardInput.A, False):
                target_pos[1] += move_speed
            if key_pressed.get(carb.input.KeyboardInput.D, False):
                target_pos[1] -= move_speed
            if key_pressed.get(carb.input.KeyboardInput.Q, False):
                target_pos[2] += move_speed
            if key_pressed.get(carb.input.KeyboardInput.E, False):
                target_pos[2] -= move_speed

            # Yaw
            if key_pressed.get(carb.input.KeyboardInput.Z, False):
                target_yaw[0] += yaw_speed
            if key_pressed.get(carb.input.KeyboardInput.X, False):
                target_yaw[0] -= yaw_speed

            # Fly to goal
            if key_pressed.get(carb.input.KeyboardInput.F, False):
                if current_result and current_result.labels.local_goal:
                    goal = current_result.labels.local_goal
                    target_pos[0] = goal[0]
                    target_pos[1] = goal[1]
                    target_pos[2] = goal[2]
                    print(f"Flying to goal: {goal}")
                key_pressed[carb.input.KeyboardInput.F] = False

            # Return to start
            if key_pressed.get(carb.input.KeyboardInput.O, False):
                if current_result and current_result.labels.local_start:
                    start = current_result.labels.local_start
                    target_pos[0] = start[0]
                    target_pos[1] = start[1]
                    target_pos[2] = start[2]
                    print(f"Returning to start: {start}")
                key_pressed[carb.input.KeyboardInput.O] = False

            # Reset drone (B key - "Back to origin")
            if key_pressed.get(carb.input.KeyboardInput.B, False):
                if current_result and current_result.labels.local_start:
                    start = current_result.labels.local_start
                    # Reset target position
                    target_pos[0] = start[0]
                    target_pos[1] = start[1]
                    target_pos[2] = start[2]
                    # Reset yaw
                    target_yaw[0] = 0.0
                    # Reset drone physics state
                    drone.set_world_poses(
                        positions=torch.tensor(
                            [[start[0], start[1], start[2]]], device=device),
                        orientations=torch.tensor(
                            # Identity quaternion
                            [[1.0, 0.0, 0.0, 0.0]], device=device)
                    )
                    # Reset velocities to zero
                    drone.set_velocities(
                        # linear + angular velocities
                        velocities=torch.zeros((1, 6), device=device)
                    )
                    print(f"[RESET] Drone reset to start position: {start}")
                key_pressed[carb.input.KeyboardInput.B] = False

            # Clamp height
            target_pos[2] = torch.clamp(
                target_pos[2], 0.3, arena_cfg.size_z - 0.3)

            # =================================================================
            # Handle Arena Controls
            # =================================================================
            arena_changed = False

            # Family switch (1/2/3)
            if key_pressed.get(carb.input.KeyboardInput.KEY_1, False):
                current_family = CREScenarioFamily.NOMINAL
                arena_changed = True
                key_pressed[carb.input.KeyboardInput.KEY_1] = False
            if key_pressed.get(carb.input.KeyboardInput.KEY_2, False):
                current_family = CREScenarioFamily.BOUNDARY_CRITICAL
                arena_changed = True
                key_pressed[carb.input.KeyboardInput.KEY_2] = False
            if key_pressed.get(carb.input.KeyboardInput.KEY_3, False):
                current_family = CREScenarioFamily.SHIFTED
                arena_changed = True
                key_pressed[carb.input.KeyboardInput.KEY_3] = False

            # Regenerate (R)
            if key_pressed.get(carb.input.KeyboardInput.R, False):
                arena_changed = True
                key_pressed[carb.input.KeyboardInput.R] = False

            # Difficulty (+/-)
            if key_pressed.get(carb.input.KeyboardInput.EQUAL, False):
                current_difficulty = min(1.0, current_difficulty + 0.1)
                arena_changed = True
                key_pressed[carb.input.KeyboardInput.EQUAL] = False
            if key_pressed.get(carb.input.KeyboardInput.MINUS, False):
                current_difficulty = max(0.0, current_difficulty - 0.1)
                arena_changed = True
                key_pressed[carb.input.KeyboardInput.MINUS] = False

            # Gravity tilt (G)
            if key_pressed.get(carb.input.KeyboardInput.G, False):
                apply_gravity_tilt = not apply_gravity_tilt
                print(f"Gravity tilt: {'ON' if apply_gravity_tilt else 'OFF'}")
                arena_changed = True
                key_pressed[carb.input.KeyboardInput.G] = False

            # =================================================================
            # Handle Display Controls
            # =================================================================
            # Toggle point cloud (T)
            if key_pressed.get(carb.input.KeyboardInput.T, False):
                show_pointcloud = not show_pointcloud
                print(f"Point cloud: {'ON' if show_pointcloud else 'OFF'}")
                key_pressed[carb.input.KeyboardInput.T] = False

            # Toggle gravity vector (V)
            if key_pressed.get(carb.input.KeyboardInput.V, False):
                show_gravity_vector = not show_gravity_vector
                print(
                    f"Gravity vector: {'ON' if show_gravity_vector else 'OFF'}")
                key_pressed[carb.input.KeyboardInput.V] = False

            # Print stats (I)
            if key_pressed.get(carb.input.KeyboardInput.I, False):
                print_stats()
                key_pressed[carb.input.KeyboardInput.I] = False

            # Hazard details (H)
            if key_pressed.get(carb.input.KeyboardInput.H, False):
                print_hazard_details()
                key_pressed[carb.input.KeyboardInput.H] = False

            # Pause (P)
            if key_pressed.get(carb.input.KeyboardInput.P, False):
                paused = not paused
                print(
                    f"Dynamic obstacles: {'PAUSED' if paused else 'RUNNING'}")
                key_pressed[carb.input.KeyboardInput.P] = False

            # =================================================================
            # Regenerate Arena if Changed
            # =================================================================
            if arena_changed:
                regenerate_arena()

            # =================================================================
            # Update Dynamic Obstacles
            # =================================================================
            has_dynamic_obstacles = (
                current_result is not None and
                any(obs.is_dynamic for obs in current_result.obstacles)
            )
            if not paused and has_dynamic_obstacles:
                new_positions = generator.update_dynamic_obstacles(dt)
                if new_positions:
                    spawner.update_positions(new_positions)
                    if step % dynamic_lidar_refresh_interval == 0:
                        _rebuild_lidar_sensor()

            # =================================================================
            # Flight Control
            # =================================================================
            # Get drone state
            drone_state = get_drone_state_vector()

            # Compute control action
            action = controller(
                drone_state,
                target_pos=target_pos,
                target_yaw=target_yaw
            )

            # Apply action
            drone.apply_action(action)

            # =================================================================
            # Physics Step
            # =================================================================
            sim_context.step()

            # =================================================================
            # Update LiDAR
            # =================================================================
            if lidar_initialized and lidar is not None:
                lidar.update(dt)

            # Refresh state after physics for logging/printing
            drone_state = get_drone_state_vector()

            # =================================================================
            # Visualization
            # =================================================================
            debug_draw.clear_points()
            debug_draw.clear_lines()

            # Draw point cloud
            ray_hits = lidar.data.ray_hits_w if (lidar_initialized and lidar is not None) else None
            lidar_pos = lidar.data.pos_w if (lidar_initialized and lidar is not None) else None
            draw_pointcloud(ray_hits, lidar_pos)

            # Draw gravity vector
            draw_gravity_vector()

            # =================================================================
            # Periodic Status Print
            # =================================================================
            pos = drone_state[:3]
            vel = drone_state[7:10]
            yaw_rate = float(drone_state[12]) if drone_state.numel() >= 13 else 0.0
            num_hits, min_dist = compute_proximity_metrics(ray_hits, lidar_pos)
            goal_distance = compute_goal_distance(pos)
            reached_goal = bool(goal_distance is not None and goal_distance < 0.5)
            collision_proxy = bool(
                min_dist is not None and min_dist < max(0.15, arena_cfg.drone_radius)
            )
            out_of_bounds_flag = bool(
                abs(float(pos[0])) > arena_cfg.size_x / 2.0 or
                abs(float(pos[1])) > arena_cfg.size_y / 2.0 or
                float(pos[2]) < 0.0 or
                float(pos[2]) > arena_cfg.size_z
            )
            if collision_proxy:
                step_done_type = "collision"
            elif out_of_bounds_flag:
                step_done_type = "out_of_bounds"
            elif reached_goal:
                step_done_type = "success"
            else:
                step_done_type = "running"

            episode_logger.log_step(
                step_idx=step,
                sim_time=sim_time,
                scene_id=get_scene_id(),
                scenario_type=get_scenario_type(),
                position=(float(pos[0]), float(pos[1]), float(pos[2])),
                velocity=(float(vel[0]), float(vel[1]), float(vel[2])),
                yaw_rate=yaw_rate,
                target_position=(float(target_pos[0]), float(target_pos[1]), float(target_pos[2])),
                goal_distance=goal_distance,
                reward_total=0.0,
                reward_components=normalize_reward_components({"manual_control": 0.0}),
                collision_flag=collision_proxy,
                min_obstacle_distance=min_dist,
                out_of_bounds_flag=out_of_bounds_flag,
                done_type=step_done_type,
                scene_cfg_name=get_scene_cfg_name(),
                reached_goal=reached_goal,
                scene_tags=get_scene_tags(),
            )

            if step % print_interval == 0:
                min_dist_display = min_dist if min_dist is not None else float('inf')
                goal_dist_display = goal_distance if goal_distance is not None else float('inf')
                print(f"[{family_names[current_family]}] "
                      f"Pos: ({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}) | "
                      f"Target: ({target_pos[0]:.1f}, {target_pos[1]:.1f}, {target_pos[2]:.1f}) | "
                      f"Goal={goal_dist_display:.1f}m | "
                      f"LiDAR: {num_hits} pts, min={min_dist_display:.1f}m")

            step += 1

            if auto_exit_steps > 0 and step >= auto_exit_steps:
                print(
                    f"[INFO] Auto exit triggered after {step} steps "
                    f"(test_flight.auto_exit_steps={auto_exit_steps})"
                )
                break

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user (Ctrl+C)")

    if step == 0 and not simulation_app.is_running():
        print(
            "[WARN] Main loop exited before any simulation step. "
            "Isaac Sim may have started shutting down immediately "
            "(for example due to window/display issues)."
        )

    # =========================================================================
    # Cleanup
    # =========================================================================
    export_episode_log("final")

    if auto_acceptance_on_exit and episode_logger.run_dir.exists():
        acceptance = run_acceptance_check(episode_logger.run_dir, write_report=True)
        print(
            f"[CRE] test_flight run acceptance: "
            f"{'PASS' if acceptance['passed'] else 'FAIL'} | run_dir={episode_logger.run_dir}"
        )
        if acceptance["errors"]:
            print("[CRE] test_flight acceptance errors:")
            for error in acceptance["errors"]:
                print(f"  - {error}")

    try:
        input_interface.unsubscribe_to_keyboard_events(keyboard, keyboard_sub)
    except Exception as exc:
        print(f"[WARN] Failed to unsubscribe keyboard events cleanly: {exc}")

    try:
        if lidar is not None:
            lidar = None
        RayCaster.meshes.pop(lidar_scan_mesh_path, None)
    except Exception as exc:
        print(f"[WARN] Failed to release LiDAR cleanly: {exc}")

    try:
        debug_draw.clear_points()
        debug_draw.clear_lines()
    except Exception as exc:
        print(f"[WARN] Failed to clear debug draw cleanly: {exc}")

    try:
        spawner.clear()
    except Exception as exc:
        print(f"[WARN] Failed to clear spawned obstacles cleanly: {exc}")

    gc.collect()

    try:
        if simulation_app.app.is_running() and not simulation_app.is_exiting():
            simulation_app.close(wait_for_replicator=False)
        else:
            print("[INFO] Simulation app is already shutting down; skipping explicit close().")
    except Exception as exc:
        print(f"[WARN] simulation_app.close() raised during shutdown: {exc}")

    print("\n" + "="*70)
    print("✅ Flight test finished!")
    print("="*70)


if __name__ == "__main__":
    main()
