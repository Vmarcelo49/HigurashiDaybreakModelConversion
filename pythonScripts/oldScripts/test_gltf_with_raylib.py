"""Simple GLTF viewer using raylib with animation support"""
import sys
from pyray import *
from pyray import ffi

if len(sys.argv) < 2:
    print("Usage: python test_gltf_with_raylib.py <gltf_file>")
    sys.exit(1)

# Initialize
init_window(1280, 720, b"GLTF Viewer with Animations")
set_target_fps(60)

# Setup camera
camera = Camera3D(Vector3(5, 5, 5), Vector3(0, 0, 0), Vector3(0, 1, 0), 45, CAMERA_PERSPECTIVE)

# Load model
model = None
animations = None
anim_count = 0
current_anim = 0
anim_frame_counter = 0
model_loaded = False

try:
    model = load_model(sys.argv[1].encode('utf-8'))
    print(f"✓ Loaded: {sys.argv[1]}")
    model_loaded = True
    
    # Try to load animations
    try:
        anim_count_ptr = ffi.new('int *', 0)
        animations = load_model_animations(sys.argv[1].encode('utf-8'), anim_count_ptr)
        anim_count = anim_count_ptr[0]
        if anim_count > 0:
            print(f"✓ Found {anim_count} animation(s)")
            for i in range(min(anim_count, 5)):  # Show first 5 only
                anim = animations[i]
                print(f"  [{i}] Animation {i}: {anim.frameCount} frames")
            if anim_count > 5:
                print(f"  ... and {anim_count - 5} more")
        else:
            print("ℹ No animations found in model")
    except Exception as e:
        print(f"ℹ No animations available: {e}")
        animations = None
        anim_count = 0
        
except Exception as e:
    print(f"✗ Failed: {e}")
    print("Showing test cube instead...")

# Main loop
angle = 0
paused = False
anim_speed = 1.0

while not window_should_close():
    # Camera controls
    update_camera(camera, CAMERA_ORBITAL)
    
    # Animation controls
    if anim_count > 0:
        # Change animation with arrow keys
        if is_key_pressed(KEY_RIGHT):
            current_anim = (current_anim + 1) % anim_count
            anim_frame_counter = 0
            print(f"→ Animation {current_anim}/{anim_count-1}")
        elif is_key_pressed(KEY_LEFT):
            current_anim = (current_anim - 1) % anim_count
            anim_frame_counter = 0
            print(f"← Animation {current_anim}/{anim_count-1}")
        
        # Pause/Resume animation
        if is_key_pressed(KEY_P):
            paused = not paused
            print("⏸ Paused" if paused else "▶ Playing")
        
        # Reset animation
        if is_key_pressed(KEY_R):
            anim_frame_counter = 0
            print("↻ Reset animation")
        
        # Speed controls
        if is_key_pressed(KEY_EQUAL) or is_key_pressed(KEY_KP_ADD):
            anim_speed = min(anim_speed + 0.25, 3.0)
            print(f"⏩ Speed: {anim_speed:.2f}x")
        elif is_key_pressed(KEY_MINUS) or is_key_pressed(KEY_KP_SUBTRACT):
            anim_speed = max(anim_speed - 0.25, 0.25)
            print(f"⏪ Speed: {anim_speed:.2f}x")
        
        # Update animation
        if not paused and animations:
            anim = animations[current_anim]
            anim_frame_counter += int(30 * get_frame_time() * anim_speed)  # Assume 30fps animations
            if anim_frame_counter >= anim.frameCount:
                anim_frame_counter = 0  # Loop animation
            update_model_animation(model, anim, anim_frame_counter)
    
    # Reset rotation
    if is_key_pressed(KEY_SPACE):
        angle = 0
    
    # Auto-rotate if no animations
    if anim_count == 0:
        angle += 30 * get_frame_time()
    
    # Drawing
    begin_drawing()
    clear_background(RAYWHITE)
    begin_mode_3d(camera)
    
    draw_grid(10, 1.0)
    
    if model_loaded and model:
        if anim_count > 0:
            # Draw model with animation (no rotation)
            draw_model(model, Vector3(0, 0, 0), 1.0, WHITE)
        else:
            # Draw model with rotation
            draw_model_ex(model, Vector3(0, 0, 0), Vector3(0, 1, 0), angle, Vector3(1, 1, 1), WHITE)
    else:
        # Draw a test cube if model failed
        draw_cube(Vector3(0, 1, 0), 2, 2, 2, RED)
        draw_cube_wires(Vector3(0, 1, 0), 2, 2, 2, MAROON)
    
    end_mode_3d()
    
    # UI
    y_pos = 10
    draw_fps(10, y_pos)
    y_pos += 30
    
    draw_text(b"CAMERA: Mouse Orbit | Wheel Zoom | Space Reset", 10, y_pos, 20, DARKGRAY)
    y_pos += 25
    
    if anim_count > 0:
        draw_text(b"ANIMATION CONTROLS:", 10, y_pos, 20, DARKGRAY)
        y_pos += 25
        draw_text(f"  Left/Right: Change Animation ({current_anim}/{anim_count-1})".encode(), 10, y_pos, 18, DARKGRAY)
        y_pos += 23
        draw_text(f"  P: {'Resume' if paused else 'Pause'} | R: Reset | +/-: Speed ({anim_speed:.2f}x)".encode(), 10, y_pos, 18, DARKGRAY)
        y_pos += 23
        
        anim = animations[current_anim]
        draw_text(f"  Frame: {anim_frame_counter}/{anim.frameCount}".encode(), 10, y_pos, 18, BLUE)
        
        # Animation progress bar
        bar_x = 10
        bar_y = y_pos + 25
        bar_width = 300
        bar_height = 20
        draw_rectangle(bar_x, bar_y, bar_width, bar_height, LIGHTGRAY)
        if anim.frameCount > 0:
            progress = (anim_frame_counter / anim.frameCount) * bar_width
            draw_rectangle(bar_x, bar_y, int(progress), bar_height, BLUE)
        draw_rectangle_lines(bar_x, bar_y, bar_width, bar_height, DARKGRAY)
    
    end_drawing()

# Cleanup
if animations and anim_count > 0:
    unload_model_animations(animations, anim_count)
if model:
    unload_model(model)
close_window()
