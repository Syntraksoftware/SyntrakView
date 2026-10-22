# System Introduction for Patent Application

## Title

**A Wearable IMU-Based Motion Capture System with Multi-Format BVH Retargeting and Real-Time 3D Avatar Visualization for Alpine Skiing**

---

## 1. Technical Field

The present invention relates to the field of human motion capture and biomechanical data visualization, and more particularly to a wearable inertial measurement unit (IMU)-based motion capture system that captures full-body skiing postures via Bluetooth Low Energy (BLE), retargets motion data from heterogeneous BVH (Biovision Hierarchy) formats onto a unified 3D avatar skeleton, and renders real-time skeletal animations on a desktop upper-computer application.

---

## 2. Background

Existing skiing motion analysis systems typically fall into three categories:

1. **Optical motion capture systems** (e.g., Vicon, OptiTrack): Provide high accuracy but require costly multi-camera infrastructure, controlled indoor environments, and extensive calibration setup, making them unsuitable for on-snow field use.
2. **Inertial suit systems** (e.g., Xsens): Offer portability but are expensive, require per-joint sensor-to-bone alignment calibration, and produce proprietary output formats that are difficult to integrate with third-party animation pipelines.
3. **Single-sensor or limited-sensor consumer products**: Lack full-body coverage and cannot capture joint-level articulation necessary for technique analysis.

Furthermore, when playing back recorded motion data (BVH files) produced by third-party inertial systems (e.g., Virdyn), existing playback tools suffer from:

- **Skeleton hierarchy mismatch**: Third-party BVH files may contain 60+ joints with different naming conventions, joint orderings, and parent-child relationships compared to the target avatar's reduced 17-node skeleton.
- **Coordinate system misalignment**: Different BVH exporters use different world-axis conventions (e.g., character facing +Z vs. −Z, Y-up vs. Z-up), leading to mirrored or rotated avatars.
- **T-pose reference ambiguity**: The default T-pose cannot disambiguate the anterior-posterior orientation of IMU sensors worn on the body, resulting in left-right inversion when the avatar faces the viewer.
- **Manual per-file retargeting overhead**: Engineers must manually adjust bone mappings for each new BVH file format, which is error-prone and non-scalable.

---

## 3. System Overview

The present invention provides a complete wearable motion capture and visualization system comprising:

### 3.1 Hardware Subsystem
A distributed IMU sensor network consisting of **13 wearable IMU nodes** mounted on the human body at anatomically defined positions:

| Sensor ID | Body Joint |
|-----------|-----------|
| 1 | Waist (Hips) |
| 2, 3 | Left/Right Hip |
| 4, 5 | Left/Right Thigh |
| 6, 7 | Left/Right Calf (Shin) |
| 8, 9 | Left/Right Shoulder |
| 10, 11 | Left/Right Upper Arm |
| 12, 13 | Left/Right Forearm |

Each node performs on-board sensor fusion (accelerometer + gyroscope + magnetometer) to output a 3-DOF Euler angle (yaw, pitch, roll) relative to a T-pose calibration reference. All nodes transmit data via **Bluetooth Low Energy (BLE)** at 60 Hz to a host upper-computer.

### 3.2 Upper-Computer Software Subsystem
A desktop application (Python / PyQt6 / Qt3D) that provides:

- **Real-time BLE data reception and 3D skeletal rendering** at 60 fps
- **Local BVH file playback** with play/pause/seek/speed controls
- **Multi-format BVH compatibility** (proprietary 13-joint format + Virdyn 61-joint format)
- **3D avatar selection** (20+ procedurally generated avatar meshes)
- **Ski equipment rendering** (skis, ski poles) that follows hand and foot joint positions

---

## 4. Key Technical Innovations

### 4.1 Unified 17-Node Avatar Skeleton with Decoupled Pelvis and Spine

The target avatar uses a **17-node skeletal hierarchy** that decouples the pelvis (controlled by hip sensors 2/3) from the spine (controlled by shoulder sensors 8/9), both hanging from a fixed root Hips node:

```
Hips (root, fixed)
├── Pelvis (sensor 2/3 average)
│   ├── Thigh_L → Shin_L → Foot_L
│   └── Thigh_R → Shin_R → Foot_R
└── Spine (sensor 8/9 average)
    ├── Neck → Head
    ├── UpperArm_L → ForeArm_L → Hand_L
    └── UpperArm_R → ForeArm_R → Hand_R
```

This decoupling ensures that lower-body movements (pelvis rotation) do not corrupt upper-body orientation and vice versa, which is critical for skiing where the torso and legs move independently.

### 4.2 World-Space Retargeting Algorithm for Heterogeneous BVH

For third-party BVH files with arbitrary joint counts and naming conventions (e.g., Virdyn's 61-joint format), the system performs:

1. **Iterative world-rotation accumulation**: Starting from the BVH root node, the algorithm traverses the joint hierarchy iteratively (not recursively, to prevent stack overflow) and accumulates local rotations into world-space quaternions for every joint.

2. **Keyword-based joint extraction**: Using configurable keyword lists (e.g., `['upperarm_left', 'leftupperarm', 'leftarm']`), the system locates the source BVH joints corresponding to each target avatar joint, regardless of naming convention.

3. **Inverse kinematic decomposition**: The relative rotation for each target bone is computed as:
   ```
   R_rel = R_parent_world⁻¹ × R_target_world
   ```
   This decomposes the source BVH's world rotations back into local rotations that fit the target avatar's parent-child hierarchy.

4. **T-pose reference alignment**: Because the target avatar's default bone orientation (e.g., upper arm pointing downward in Y−) differs from the source BVH's T-pose orientation (e.g., upper arm extending sideways in X), a per-bone T-pose correction quaternion is applied:
   ```
   R_rel_target = R_tpose⁻¹ × R_parent_world⁻¹ × R_target_world × R_tpose
   ```

### 4.3 Automatic Left-Right Mirror Correction

The system addresses a fundamental ambiguity in viewer-facing avatar visualization: when the avatar faces the viewer, the viewer's left corresponds to the avatar's right. The invention applies **context-aware left-right mapping** that varies by data source:

- **Real-time BLE mode**: Incoming sensor data has left-right swapped at the data ingress point (`update_angles`), so that the user's left IMU drives the viewer's right-side bone.
- **Proprietary BVH playback**: The bone-to-sensor mapping table internally swaps left and right entries.
- **Third-party BVH (remapped mode)**: The source coordinate system undergoes a 180° Y-axis rotation to flip the character's facing direction, after which direct mapping is correct.

This three-tier approach ensures left-right consistency across all input sources without requiring manual per-file configuration.

### 4.4 T-Pose Calibration with Anterior-Posterior Disambiguation

The system uses a two-step calibration procedure:

1. **T-pose calibration**: The user stands with arms extended horizontally; the system records each IMU's absolute orientation as a zero-reference. This establishes the vertical (gravity) axis and left-right symmetry axis.

2. **Forward-reach calibration**: The user extends both arms forward (parallel to the ground, facing forward). The rotational difference between T-pose and forward-reach defines the anterior-posterior axis, resolving the inherent ambiguity of T-pose alone (which cannot distinguish sensor twist around the bone's long axis).

### 4.5 Procedural Avatar Mesh Generation

The system includes a parametric STL mesh generator that procedurally constructs avatar components (head, torso, limbs, hands, feet, skis, poles) from primitives (cylinders, spheres, boxes, cones). Each component is exported as a separate STL file positioned relative to its joint origin, enabling:

- Automatic avatar length adaptation (model offset aligns mesh top to joint position)
- Color-coded body part materials
- Ski equipment (skis, poles) that inherit hand/foot joint transforms
- Multiple avatar themes (20+ styles) without manual 3D modeling

### 4.6 Crash-Resilient BVH Parser

The BVH parser includes production-hardened robustness:

- **End-site state tracking**: Properly tracks `{}` and `}` braces inside End Site blocks to prevent stack underflow from popping real joints when encountering End Site closing braces.
- **Identity quaternion initialization**: World-rotation accumulation starts from the unit quaternion (1,0,0,0) rather than the zero quaternion (0,0,0,0).
- **None-safe joint lookups**: Joint lookups that return `None` are handled with explicit `is not None` checks rather than truthiness tests (which reject valid zero quaternions).

---

## 5. System Architecture Data Flow

```
[13 IMU Sensors]
       │
       ▼  BLE, 60 Hz
[BLE Manager] ──────────────────────────────┐
       │                                    │
       ▼                                    ▼
[update_angles()]                    [BVH Player]
  (left-right swap                     ├─ Proprietary BVH (direct map)
   in realtime mode)                   └─ Third-party BVH (world-space retarget)
       │                                    │
       └──────────────┬─────────────────────┘
                      ▼
            [17-Node Skeleton]
                      │
                      ▼
            [Qt3D Renderer]
              ├─ Avatar meshes (STL)
              ├─ Ski equipment
              └─ 60 fps animation loop
```

---

## 6. Technical Advantages

| Feature | Optical Systems | Inertial Suits | Present Invention |
|---------|----------------|----------------|-------------------|
| On-snow portability | No | Yes | Yes |
| Full-body articulation (13 joints) | Yes | Yes | Yes |
| Third-party BVH playback | No | Limited | Yes (61-joint → 17-node retarget) |
| Auto left-right correction | N/A | No | Yes (3-tier, context-aware) |
| T-pose + forward-reach calibration | N/A | T-pose only | T-pose + AP disambiguation |
| Parametric avatar generation | No | Limited | Yes (20+ procedural avatars) |
| Ski equipment rendering | No | No | Yes (skis + poles) |
| BLE wireless (no tether) | N/A | Yes | Yes |
| Low-cost (consumer IMUs) | No | No | Yes |

---

## 7. Application Fields

- **Alpine skiing technique analysis and coaching**
- **Rehabilitation and physical therapy motion monitoring**
- **Sports biomechanics research**
- **Real-time avatar animation for virtual training**
- **BVH motion data review and quality assurance**
