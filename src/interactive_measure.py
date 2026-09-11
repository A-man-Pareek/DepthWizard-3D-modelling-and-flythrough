import cv2
import json
import numpy as np


# ==================================================
# FILES
# ==================================================

IMAGE_PATH = "input/test.png"
DEPTH_PATH = "input/depth.npy"
CAMERA_PATH = "camera_params.json"


# ==================================================
# LOAD CAMERA PARAMETERS
# ==================================================

with open(CAMERA_PATH, "r") as file:
    camera = json.load(file)

fx = float(camera["fx"])
fy = float(camera["fy"])
cx = float(camera["cx"])
cy = float(camera["cy"])


# ==================================================
# LOAD IMAGE
# ==================================================

image = cv2.imread(IMAGE_PATH)

if image is None:
    raise FileNotFoundError(
        f"Could not load image: {IMAGE_PATH}"
    )

original_image = image.copy()

original_height, original_width = image.shape[:2]


# ==================================================
# LOAD DEPTH
# ==================================================

depth = np.load(DEPTH_PATH).astype(np.float32)

if depth.shape != (original_height, original_width):
    depth = cv2.resize(
        depth,
        (original_width, original_height),
        interpolation=cv2.INTER_LINEAR
    )


# ==================================================
# CREATE DISPLAY IMAGE
# ==================================================

DISPLAY_WIDTH = 1200
DISPLAY_HEIGHT = 800

scale_x = DISPLAY_WIDTH / original_width
scale_y = DISPLAY_HEIGHT / original_height

scale = min(scale_x, scale_y)

display_width = int(original_width * scale)
display_height = int(original_height * scale)

display_image = cv2.resize(
    original_image,
    (display_width, display_height),
    interpolation=cv2.INTER_AREA
)


# ==================================================
# SELECTED POINTS
# ==================================================

selected_points = []


# ==================================================
# PIXEL → 3D
# ==================================================

def pixel_to_3d(u, v):

    z = float(depth[v, u])

    if not np.isfinite(z) or z <= 0:
        return None

    x = (u - cx) * z / fx
    y = (v - cy) * z / fy

    return np.array([x, y, z])


# ==================================================
# MOUSE CALLBACK
# ==================================================

WINDOW_NAME = "DepthWizard Measurement"


def mouse_callback(event, x, y, flags, param):

    if event != cv2.EVENT_LBUTTONDOWN:
        return

    if len(selected_points) >= 2:
        print("Already selected two points.")
        print("Press R to reset.")
        return

    # ----------------------------------------------
    # DISPLAY COORDINATES → ORIGINAL IMAGE
    # ----------------------------------------------

    u = int(x / scale)
    v = int(y / scale)

    # Safety check
    if not (
        0 <= u < original_width
        and 0 <= v < original_height
    ):
        return

    # ----------------------------------------------
    # GET 3D POINT
    # ----------------------------------------------

    point_3d = pixel_to_3d(u, v)

    if point_3d is None:
        print("Invalid depth at this location.")
        return

    selected_points.append(
        (u, v, point_3d)
    )

    point_number = len(selected_points)

    print("\n------------------------------")
    print(f"POINT {point_number}")
    print("------------------------------")

    print(
        f"Pixel: ({u}, {v})"
    )

    print(
        f"Depth: {point_3d[2]:.3f} m"
    )

    print(
        f"X: {point_3d[0]:.3f} m"
    )

    print(
        f"Y: {point_3d[1]:.3f} m"
    )

    print(
        f"Z: {point_3d[2]:.3f} m"
    )

    # ----------------------------------------------
    # DRAW MARKER
    # ----------------------------------------------

    cv2.circle(
        display_image,
        (x, y),
        8,
        (0, 0, 255),
        -1
    )

    cv2.putText(
        display_image,
        f"P{point_number}",
        (x + 10, y - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 255),
        2
    )

    # ----------------------------------------------
    # IF TWO POINTS → MEASURE
    # ----------------------------------------------

    if len(selected_points) == 2:

        point_a = selected_points[0][2]
        point_b = selected_points[1][2]

        distance = np.linalg.norm(
            point_a - point_b
        )

        print("\n================================")
        print("3D MEASUREMENT")
        print("================================")

        print(
            f"Distance = {distance:.3f} metres"
        )

        print("================================")

        # Draw line between points
        p1 = (
            int(selected_points[0][0] * scale),
            int(selected_points[0][1] * scale)
        )

        p2 = (
            int(selected_points[1][0] * scale),
            int(selected_points[1][1] * scale)
        )

        cv2.line(
            display_image,
            p1,
            p2,
            (0, 0, 255),
            3
        )

        # Display measurement
        midpoint = (
            (p1[0] + p2[0]) // 2,
            (p1[1] + p2[1]) // 2
        )

        cv2.putText(
            display_image,
            f"{distance:.2f} m",
            midpoint,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )

    cv2.imshow(
        WINDOW_NAME,
        display_image
    )


# ==================================================
# RESET FUNCTION
# ==================================================

def reset_measurement():

    global display_image
    global selected_points

    selected_points = []

    display_image = cv2.resize(
        original_image,
        (display_width, display_height),
        interpolation=cv2.INTER_AREA
    )

    cv2.imshow(
        WINDOW_NAME,
        display_image
    )

    print("\nMeasurement reset.")
    print("Click two new points.")


# ==================================================
# CREATE WINDOW
# ==================================================

cv2.namedWindow(
    WINDOW_NAME,
    cv2.WINDOW_AUTOSIZE
)

cv2.setMouseCallback(
    WINDOW_NAME,
    mouse_callback
)


# ==================================================
# START
# ==================================================

print("\n================================")
print("DEPTHWIZARD 3D MEASUREMENT")
print("================================")
print("Click TWO points.")
print("Press R to reset.")
print("Press Q to quit.")
print("================================")


cv2.imshow(
    WINDOW_NAME,
    display_image
)


# ==================================================
# MAIN LOOP
# ==================================================

while True:

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

    if key == ord("r"):
        reset_measurement()


cv2.destroyAllWindows()