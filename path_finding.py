import cv2
import numpy as np
import heapq
from heapq import heappush, heappop
import time

Crop_factor = 20
def dijkstra(start, end, depth_map):
    visited = np.zeros(depth_map.shape, dtype=bool)
    queue = [(0, start, [])]
    while queue:
        (cost, current, path) = heappop(queue)
        if visited[current[::-1]]:
            continue
        visited[current[::-1]] = True
        path = path + [current]
        if current == end:
            return path
        for neighbor in neighbors(current, depth_map.shape):
            if not visited[neighbor[::-1]]:
                new_cost = cost + depth_map[neighbor[::-1]]
                heappush(queue, (new_cost, neighbor, path))
    return None

def heuristic(a, b):
    return np.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def neighbors(point, img_shape):
    x, y = point
    return [(new_x, new_y) for new_x in range(x - 1, x + 2) for new_y in range(y - 1, y + 2)
            if 0 <= new_x < img_shape[1] and 0 <= new_y < img_shape[0] and (new_x != x or new_y != y)]



def create_distance_transform(depth_map, object_threshold):
    binary_map = (depth_map < object_threshold).astype(np.uint8)
    distance_transform = cv2.distanceTransform(binary_map, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    return distance_transform

def astar(start, end, depth_map, object_threshold=50, penalty_weight=1, min_distance=1000):
    distance_transform = create_distance_transform(depth_map, object_threshold)

    def cost_with_penalty(current, neighbor):
        cost = heuristic(current, neighbor)
        distance = distance_transform[neighbor[::-1]]
        brightness_penalty = depth_map[neighbor[::-1]] / 255.0
        if distance < min_distance:
            cost += (min_distance - distance) * penalty_weight * brightness_penalty
        return cost

    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, end)}

    while open_set:
        current = heapq.heappop(open_set)[1]
        if current == end:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            path.reverse()
            return path

        for neighbor in neighbors(current, depth_map.shape):
            tentative_g_score = g_score[current] + cost_with_penalty(current, neighbor)
            if tentative_g_score < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + heuristic(neighbor, end)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))

    return None


def main(depth_map, frame_num):
    t1 = time.time()

    original_depth_map = depth_map.copy()
    depth_map = downsample_image(depth_map)

    # Update the coordinates of the red dot and farthest point
    dot_x = depth_map.shape[1] // 2
    dot_y = depth_map.shape[0] - 1
    farthest_point = np.unravel_index(depth_map.argmin(), depth_map.shape)
    farthest_point = tuple(map(int, farthest_point))


    # Convert the grayscale depth map to a color image
    depth_map_color = cv2.cvtColor(depth_map, cv2.COLOR_GRAY2BGR)

    # Draw a red and green dot at respective locations
    radius_red = 10
    radius_green = 5
    color_red = (0, 0, 255)  # Red
    color_green = (0,255,0) # Green
    thickness = -1  # Fill the circle
    line_thickness = 5
    cv2.circle(depth_map_color, (dot_x, dot_y), radius_red, color_red, thickness)
    cv2.circle(depth_map_color, farthest_point[::-1], radius_green, color_green, thickness)

    # Find the path between the red and green dots with the least obstruction
    # path = dijkstra((dot_x, dot_y), farthest_point[::-1], depth_map)
    path = astar((dot_x, dot_y), farthest_point[::-1], depth_map)

    # Upscale the path coordinates
    upscale_factor = Crop_factor
    path = [(x * upscale_factor, y * upscale_factor) for x, y in path]

    # Convert the original grayscale depth map to a color image
    original_depth_map_color = cv2.cvtColor(original_depth_map, cv2.COLOR_GRAY2BGR)

    # Draw a red and green dot at respective locations
    cv2.circle(original_depth_map_color, (dot_x * upscale_factor, dot_y * upscale_factor), radius_red, color_red, thickness)
    cv2.circle(original_depth_map_color, (farthest_point[1] * upscale_factor, farthest_point[0] * upscale_factor), radius_green, color_green, thickness)

    # Draw the path with a blue line on the original depth map
    if path:
        for i in range(len(path) - 1):
            cv2.line(original_depth_map_color, path[i], path[i + 1], (255, 0, 0), line_thickness)

    # Show the original depth map with the red dot, green dot, and path
    cv2.imshow(f'Path for map {frame_num}', original_depth_map_color)
    t2 = time.time()
    print(f'Frame {frame_num} took {t2-t1} seconds')
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def downsample_image(image, factor=Crop_factor):
    new_shape = (image.shape[1] // factor, image.shape[0] // factor)
    return cv2.resize(image, new_shape, interpolation=cv2.INTER_AREA)

if __name__ == '__main__':

    # read all depth maps from Midas/outputs/depth and find the path for each
    path = './Midas/outputs/depth/'
    # number of images in the folder
    n = 60
    for i in range(1, n+1):

        depth_map = cv2.imread(path + str(i) + '.png', cv2.IMREAD_GRAYSCALE)
        if depth_map is not None:
            main(depth_map,i)
