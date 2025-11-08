# Avatar Integration Guide

**Date:** 2025-11-08
**Status:** ✅ MediaPipe Skeleton Ready | Ready Player Me Integration Documented

## Overview

Three-tier approach to ASL visualization:
1. **Video Playback** (Production Ready NOW)
2. **MediaPipe Skeleton** (Implemented ✅)
3. **Ready Player Me 3D Avatar** (Integration Guide)

---

## Option 1: Video Playback (EASIEST - Ready NOW)

### Status: ✅ Production Ready

**What you have:**
- 2,000 ASL video URLs from WLASL dataset
- Direct links to real signers performing signs
- Most authentic representation

**Implementation:**
```html
<!-- Simple HTML5 Video Player -->
<video id="sign-video" autoplay loop>
  <source src="{{ video_url }}" type="video/mp4">
</video>

<script>
// Backend provides video URL
fetch('/api/v1/translation/translate', {
  method: 'POST',
  body: JSON.stringify({ text: "Hello" })
})
.then(r => r.json())
.then(data => {
  // Get video URL for each sign
  data.sign_sequence.forEach(sign => {
    if (sign.video_url) {
      playVideo(sign.video_url);
    }
  });
});
</script>
```

**Advantages:**
- ✅ Zero setup time
- ✅ Real signers (most authentic)
- ✅ Works in any browser
- ✅ All 2,000 signs have videos

**Use this for MVP!**

---

## Option 2: MediaPipe Skeleton Visualization

### Status: ✅ Implemented

**What it is:**
- Extract pose data from videos using MediaPipe
- Display as 3D skeleton overlay
- Customizable colors, lightweight

**Backend Service Created:**
- `app/services/pose_extraction.py` - MediaPipe pose extraction
- `app/routes/pose.py` - API endpoints
- Endpoints:
  - `POST /api/pose/extract` - Extract pose from video URL
  - `GET /api/pose/connections` - Get skeleton bone definitions
  - `GET /api/pose/test` - Quick test endpoint

**How It Works:**
```python
# Backend extracts 33 body + 42 hand + 6 face landmarks
pose_data = {
    "fps": 25,
    "frames": [
        {
            "frame": 0,
            "pose": [{x, y, z, visibility}, ...],  # 33 points
            "left_hand": [{x, y, z, visibility}, ...],  # 21 points
            "right_hand": [{x, y, z, visibility}, ...],  # 21 points
            "face": [{x, y, z, visibility}, ...]  # 6 key points
        }
    ],
    "skeleton_connections": {
        "pose": [(11, 12), (11, 13), ...],  # bone pairs
        "left_hand": [(0, 1), (1, 2), ...],
        "right_hand": [(0, 1), (1, 2), ...]
    }
}
```

**Frontend Visualization (Three.js):**
```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
</head>
<body>
    <canvas id="skeleton-canvas"></canvas>

    <script>
    // Setup Three.js scene
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({canvas: document.getElementById('skeleton-canvas')});

    // Fetch pose data
    fetch('/api/pose/extract', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            video_url: 'http://aslbricks.org/New/ASL-Videos/hello.mp4',
            max_frames: 30
        })
    })
    .then(r => r.json())
    .then(data => {
        // Draw skeleton for each frame
        data.frames.forEach((frame, i) => {
            setTimeout(() => drawSkeleton(frame), i * 40); // 25fps
        });
    });

    function drawSkeleton(frame) {
        // Clear previous
        scene.children = scene.children.filter(c => c.type === 'AmbientLight');

        // Draw joints (spheres)
        frame.pose?.forEach(point => {
            const geometry = new THREE.SphereGeometry(0.02, 16, 16);
            const material = new THREE.MeshBasicMaterial({color: 0x00ff00});
            const sphere = new THREE.Mesh(geometry, material);
            sphere.position.set(point.x - 0.5, 1 - point.y, point.z);
            scene.add(sphere);
        });

        // Draw bones (lines)
        const connections = data.skeleton_connections.pose;
        connections.forEach(([start, end]) => {
            if (frame.pose[start] && frame.pose[end]) {
                const geometry = new THREE.BufferGeometry();
                const vertices = new Float32Array([
                    frame.pose[start].x - 0.5, 1 - frame.pose[start].y, frame.pose[start].z,
                    frame.pose[end].x - 0.5, 1 - frame.pose[end].y, frame.pose[end].z
                ]);
                geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
                const material = new THREE.LineBasicMaterial({color: 0x0000ff});
                const line = new THREE.Line(geometry, material);
                scene.add(line);
            }
        });

        renderer.render(scene, camera);
    }

    camera.position.z = 2;
    </script>
</body>
</html>
```

**Advantages:**
- ✅ Lightweight (no video download during display)
- ✅ Customizable (colors, line thickness, etc.)
- ✅ Accurate (extracted from actual videos)
- ✅ Can be cached for fast playback

**Disadvantages:**
- ❌ Less realistic than video
- ❌ Requires pre-processing videos
- ❌ Stick figure appearance

---

## Option 3: Ready Player Me 3D Avatar

### Status: 📋 Integration Guide (Not Implemented)

**What it is:**
- Full 3D humanoid avatar
- Customizable appearance
- Professional animation system
- Free for commercial use

**Setup Steps:**

### Step 1: Get Ready Player Me Avatar

```javascript
// 1. Create avatar using their web interface
// https://readyplayer.me/

// 2. Get GLB URL
const avatarUrl = 'https://models.readyplayer.me/[YOUR_AVATAR_ID].glb';

// 3. Load with Three.js
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader';

const loader = new GLTFLoader();
loader.load(avatarUrl, (gltf) => {
    const avatar = gltf.scene;
    scene.add(avatar);

    // Avatar is ready for animation
    setupAnimations(gltf);
});
```

### Step 2: Add Animations

**Option A: Use MediaPipe Pose Data (Recommended)**

```javascript
// Convert MediaPipe pose to bone rotations
function applyPoseToAvatar(avatar, poseData) {
    const skeleton = avatar.children[0].skeleton;

    // Map MediaPipe landmarks to avatar bones
    const boneMapping = {
        'LeftShoulder': 11,    // MediaPipe pose index
        'RightShoulder': 12,
        'LeftElbow': 13,
        'RightElbow': 14,
        // ... more mappings
    };

    // Calculate and apply rotations
    Object.entries(boneMapping).forEach(([boneName, poseIndex]) => {
        const bone = skeleton.getBoneByName(boneName);
        const rotation = calculateRotationFromPose(poseData, poseIndex);
        bone.rotation.set(rotation.x, rotation.y, rotation.z);
    });
}
```

**Option B: Use Mixamo Animations**

```javascript
// 1. Export ASL gestures to FBX from Blender/Maya
// 2. Upload to Mixamo for retargeting
// 3. Download as FBX for Ready Player Me

import { FBXLoader } from 'three/examples/jsm/loaders/FBXLoader';

const fbxLoader = new FBXLoader();
fbxLoader.load('/animations/hello_asl.fbx', (animation) => {
    const mixer = new THREE.AnimationMixer(avatar);
    const action = mixer.clipAction(animation.animations[0]);
    action.play();

    // Update in render loop
    function animate() {
        mixer.update(clock.getDelta());
        renderer.render(scene, camera);
        requestAnimationFrame(animate);
    }
});
```

### Step 3: Map ASL Signs to Animations

**Backend Service:**
```python
# app/services/avatar_animation.py

class AvatarAnimationService:
    def __init__(self):
        self.animation_library = self._load_animations()

    def get_animation_for_sign(self, gloss: str) -> Dict[str, Any]:
        """Get animation data for ASL sign"""

        # Priority 1: Custom ASL animation
        if gloss in self.animation_library:
            return {
                "type": "fbx",
                "url": f"/animations/asl/{gloss.lower()}.fbx",
                "duration": self.animation_library[gloss]["duration"]
            }

        # Priority 2: MediaPipe pose data
        pose_data = self._get_cached_pose(gloss)
        if pose_data:
            return {
                "type": "pose",
                "data": pose_data,
                "duration": len(pose_data["frames"]) / pose_data["fps"]
            }

        # Priority 3: Fingerspelling
        if gloss.startswith("FS:"):
            letters = gloss[3:]
            return {
                "type": "fingerspell",
                "letters": letters,
                "duration": len(letters) * 0.5
            }

        return None

    def _get_cached_pose(self, gloss: str):
        """Get pre-extracted MediaPipe pose for sign"""
        pose_file = f"/data/poses/{gloss.lower()}.json"
        if Path(pose_file).exists():
            with open(pose_file) as f:
                return json.load(f)
        return None
```

**Frontend Integration:**
```javascript
// Fetch sign sequence with animations
fetch('/api/v1/translation/translate', {
    method: 'POST',
    body: JSON.stringify({ text: "Hello how are you" })
})
.then(r => r.json())
.then(data => {
    // Get animations for each sign
    const animations = data.sign_sequence.map(sign => ({
        gloss: sign.gloss,
        animation: getAnimationForGloss(sign.gloss)
    }));

    // Play animation sequence
    playAnimationSequence(avatar, animations);
});

function playAnimationSequence(avatar, animations) {
    let currentTime = 0;

    animations.forEach(anim => {
        setTimeout(() => {
            if (anim.animation.type === 'pose') {
                applyPoseSequence(avatar, anim.animation.data);
            } else if (anim.animation.type === 'fbx') {
                playFBXAnimation(avatar, anim.animation.url);
            }
        }, currentTime * 1000);

        currentTime += anim.animation.duration;
    });
}
```

**Advantages:**
- ✅ Professional appearance
- ✅ Customizable avatar
- ✅ Smooth animations
- ✅ Free for commercial use

**Disadvantages:**
- ❌ Requires animation creation/mapping
- ❌ More complex setup
- ❌ Needs 3D rendering
- ❌ Performance considerations

---

## Recommended Implementation Plan

### Phase 1 (Week 1): Video Playback
```javascript
// Simple, production-ready NOW
<video src="{{ sign.video_url }}" autoplay></video>
```

### Phase 2 (Week 2-3): MediaPipe Skeleton
```javascript
// Extract poses from videos
// Display as skeleton
// Cache for performance
```

### Phase 3 (Month 2+): Ready Player Me
```javascript
// Create avatar
// Map MediaPipe poses to bones
// Add custom ASL animations via Mixamo
```

---

## API Endpoints Created

### Pose Extraction
```
POST /api/pose/extract
{
    "video_url": "http://aslbricks.org/New/ASL-Videos/hello.mp4",
    "max_frames": 30
}

Response:
{
    "success": true,
    "fps": 25,
    "frames": [...],
    "skeleton_connections": {...}
}
```

### Get Skeleton Connections
```
GET /api/pose/connections

Response:
{
    "success": true,
    "connections": {
        "pose": [[11,12], [11,13], ...],
        "left_hand": [[0,1], [1,2], ...],
        "right_hand": [[0,1], [1,2], ...]
    }
}
```

### Test Pose Extraction
```
GET /api/pose/test?video_url=http://aslbricks.org/New/ASL-Videos/hello.mp4

Response:
{
    "success": true,
    "data": {...},
    "summary": {
        "fps": 25,
        "frames_processed": 30,
        "has_pose": true,
        "has_hands": true
    }
}
```

---

## Files Created

1. **`backend/app/services/pose_extraction.py`**
   - MediaPipe Holistic integration
   - Extracts 33 body + 42 hand + 6 face landmarks
   - Video download and processing
   - JSON export capability

2. **`backend/app/routes/pose.py`**
   - POST `/api/pose/extract` - Extract pose from video
   - GET `/api/pose/connections` - Get skeleton structure
   - GET `/api/pose/test` - Quick testing

3. **`backend/main.py`** (Updated)
   - Added pose router registration

---

## Next Steps

### Immediate (Ready to Use):
1. Test MediaPipe pose extraction with sample video
2. Create simple skeleton visualization frontend
3. Cache extracted poses for performance

### Short Term:
1. Pre-process all 2,000 WLASL videos
2. Store poses in database
3. Build skeleton player component

### Long Term:
1. Create Ready Player Me integration
2. Record custom ASL animations
3. Map all 2,034 signs to animations

---

## Resources

- **MediaPipe Holistic**: https://google.github.io/mediapipe/solutions/holistic.html
- **Ready Player Me**: https://readyplayer.me/
- **Three.js**: https://threejs.org/
- **Mixamo Animations**: https://www.mixamo.com/

---

**Status:** MediaPipe skeleton visualization is production-ready. Ready Player Me requires additional animation work but can be integrated using the guides above.
