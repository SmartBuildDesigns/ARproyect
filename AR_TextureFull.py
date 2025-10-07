import cv2
import numpy as np
import pywavefront
from pywavefront import visualization, mesh
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from PIL import Image
import time

# ---------- Configuración ----------
calibration_file = 'calibracion_camara.npz'
obj_file = 'Lucario.obj'
pattern_size = (9, 6)
square_size = 3.25
display = (800, 600)
width, height = display
z_near = 0.1
z_far = 1000.0

# ---------- Cargar calibración ----------
try:
    with np.load(calibration_file) as X:
        mtx, dist = X['mtx'], X['dist']
except FileNotFoundError:
    print(f"Error: El archivo de calibración '{calibration_file}' no fue encontrado.")
    exit()

# ---------- Inicializar cámara ----------
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise RuntimeError("No se pudo abrir la cámara")
cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

# ---------- Inicializar Pygame + OpenGL ----------
pygame.init()
pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
pygame.display.set_caption("Realidad Aumentada - Control de Detalle")

# ---------- Configuración inicial de OpenGL ----------
def init_gl():
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glLightfv(GL_LIGHT0, GL_POSITION, (5, 5, 5, 1))
    glClearColor(0.0, 0.0, 0.0, 1.0)

init_gl()

# ---------- Cargar modelo 3D ----------
try:
    # Se carga a 'original_scene' para mantenerlo intacto.
    original_scene = pywavefront.Wavefront(obj_file, collect_faces=True, parse=True)
except Exception as e:
    print(f"Error cargando el modelo 3D '{obj_file}': {e}")
    exit()

# ---------- Preparar puntos 3D del tablero ----------
objp = np.zeros((np.prod(pattern_size), 3), np.float32)
objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
objp *= square_size

# ---------- Funciones de Ayuda ----------
def create_subsampled_scene(source_scene, level):
    """Crea una nueva escena omitiendo caras para reducir el detalle."""
    if level <= 1:
        return source_scene

    new_scene = pywavefront.Wavefront(source_scene.name, strict=False)
    
    # Se añade la copia del diccionario de materiales.
    new_scene.materials = source_scene.materials
    new_scene.vertices = source_scene.vertices
    new_scene.normals = source_scene.normals
    new_scene.tex_coords = source_scene.tex_coords

    for original_mesh in source_scene.mesh_list:
        new_mesh = mesh.Mesh(original_mesh.name)
        for material in original_mesh.materials:
            subsampled_faces = material.faces[::level]
            new_mesh.add_material(material.name, material.gl_floats, len(subsampled_faces), subsampled_faces)
        new_scene.mesh_list.append(new_mesh)
    
    return new_scene


def set_projection_from_camera(mtx):
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    fx, fy = mtx[0, 0], mtx[1, 1]
    cx, cy = mtx[0, 2], mtx[1, 2]
    left, right = -cx * z_near / fx, (width - cx) * z_near / fx
    bottom, top = -(height - cy) * z_near / fy, cy * z_near / fy
    glFrustum(left, right, bottom, top, z_near, z_far)

## La función ahora recibe la escena a dibujar.
def draw_model(scene_to_draw):
    glPushMatrix()
    # El cálculo de tamaño y posición SIEMPRE se hace sobre el modelo original.
    all_vertices = np.array(original_scene.vertices)
    if all_vertices.size == 0:
        glPopMatrix()
        return

    model_min_y = all_vertices[:, 1].min()
    model_center_xz = all_vertices[:, [0, 2]].mean(axis=0)
    glTranslatef(-model_center_xz[0], -model_min_y, -model_center_xz[1])

    board_width = (pattern_size[0] - 1) * square_size
    verts_size = all_vertices.max(axis=0) - all_vertices.min(axis=0)
    model_max_dim = max(verts_size[0], verts_size[2])
    if model_max_dim > 1e-6:
        scale_factor = board_width / model_max_dim * 0.8
        glScalef(scale_factor, scale_factor, scale_factor)

    glRotatef(angles[0], 1, 0, 0)
    glRotatef(angles[1], 0, 1, 0)
    glRotatef(angles[2], 0, 0, 1)

    # Dibuja la escena que se le pasó (que puede ser la original o una simplificada).
    visualization.draw(scene_to_draw)
    glPopMatrix()

def draw_camera_bg(frame):
    h, w = frame.shape[:2]
    frame = cv2.flip(frame, 0)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix(); glLoadIdentity(); glOrtho(0, w, 0, h, -1, 1);
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix(); glLoadIdentity();
    glDisable(GL_DEPTH_TEST); glEnable(GL_TEXTURE_2D);
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, frame_rgb)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(0, 0); glTexCoord2f(1, 0); glVertex2f(w, 0);
    glTexCoord2f(1, 1); glVertex2f(w, h); glTexCoord2f(0, 1); glVertex2f(0, h);
    glEnd()
    glDeleteTextures([tex_id])
    glEnable(GL_DEPTH_TEST)
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)

# ---------- Estado inicial y controles ----------
angles = np.array([-90.0, 0.0, 0.0])
mode = 'faces'
point_size = 3.0
line_width = 1.0

## Variables para controlar el nivel de detalle.
subsample_level = 1  # 1 = detalle completo
current_scene = original_scene # Al inicio, la escena a dibujar es la original.

print("="*40)
print("Controles del Programa de RA")
print("="*40)
print("  w/p/f -> Cambiar modo (Wireframe/Puntos/Caras)")
print("  r/t/y -> Rotar en ejes X/Y/Z")
print("  (Mantener SHIFT para rotar en sentido contrario)")
print("  +/-   -> Aumentar/Disminuir tamaño de puntos/líneas")
print("  [     -> Disminuir cantidad de caras (menos detalle)")
print("  ]     -> Aumentar cantidad de caras (más detalle)")
print("  s     -> Tomar Screenshot")
print("  q/ESC -> Salir del programa")
print("="*40)

# Bucle principal
running = True
while running:
    ret, frame = cap.read()
    if not ret: break
    
    frame_undist = cv2.undistort(frame, mtx, dist, None, mtx)
    gray = cv2.cvtColor(frame_undist, cv2.COLOR_BGR2GRAY)
    found, corners = cv2.findChessboardCorners(gray, pattern_size, cv2.CALIB_CB_FAST_CHECK)
    
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    draw_camera_bg(frame_undist)

    if found:
        # ... (código de solvePnP y matrices sin cambios) ...
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        _, rvec, tvec = cv2.solvePnP(objp, corners2, mtx, dist)
        set_projection_from_camera(mtx)
        glMatrixMode(GL_MODELVIEW); glLoadIdentity()
        gl_convert = np.array([[1,0,0,0], [0,-1,0,0], [0,0,-1,0], [0,0,0,1]], dtype=np.float32)
        glMultMatrixf(gl_convert.T)
        R, _ = cv2.Rodrigues(rvec)
        pose_matrix = np.eye(4, dtype=np.float32)
        pose_matrix[:3, :3] = R
        pose_matrix[:3, 3] = tvec.flatten()
        glMultMatrixf(pose_matrix.T)
        
        glPointSize(point_size)
        glLineWidth(line_width)
        
        if mode == 'wireframe': glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        elif mode == 'points': glPolygonMode(GL_FRONT_AND_BACK, GL_POINT)
        else: glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            
        draw_model(current_scene) # Dibuja la escena actual
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    pygame.display.flip()
    
    for event in pygame.event.get():
        if event.type == QUIT or (event.type == KEYDOWN and event.key in (K_ESCAPE, K_q)):
            running = False
        if event.type == KEYDOWN:
            keys = pygame.key.get_pressed()
            step = -15 if keys[K_LSHIFT] or keys[K_RSHIFT] else 15

            if event.key == K_w: mode = 'wireframe'; print("Modo: Wireframe")
            elif event.key == K_p: mode = 'points'; print("Modo: Puntos")
            elif event.key == K_f: mode = 'faces'; print("Modo: Caras")
            elif event.key == K_r: angles[0] = (angles[0] + step) % 360; print(f"Rotación X: {angles[0]:.0f}°")
            elif event.key == K_t: angles[1] = (angles[1] + step) % 360; print(f"Rotación Y: {angles[1]:.0f}°")
            elif event.key == K_y: angles[2] = (angles[2] + step) % 360; print(f"Rotación Z: {angles[2]:.0f}°")
            elif event.key in (K_PLUS, K_KP_PLUS):
                point_size += 1.0; line_width += 1.0; print(f"Tamaño puntos/líneas: {point_size:.1f}")
            elif event.key in (K_MINUS, K_KP_MINUS):
                point_size = max(1.0, point_size - 1.0); line_width = max(1.0, line_width - 1.0)
                print(f"Tamaño puntos/líneas: {point_size:.1f}")

            ## Lógica para las teclas '[' y ']'.
            elif event.key == K_LEFTBRACKET: # Tecla '[' para disminuir detalle
                subsample_level += 1
                current_scene = create_subsampled_scene(original_scene, subsample_level)
                print(f"Nivel de detalle disminuido. Mostrando 1 de cada {subsample_level} caras.")
            elif event.key == K_RIGHTBRACKET: # Tecla ']' para aumentar detalle
                subsample_level = max(1, subsample_level - 1)
                current_scene = create_subsampled_scene(original_scene, subsample_level)
                if subsample_level == 1:
                    print("Nivel de detalle restaurado al máximo.")
                else:
                    print(f"Nivel de detalle aumentado. Mostrando 1 de cada {subsample_level} caras.")

            elif event.key == K_s:
                pixels = glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE)
                image = Image.frombytes("RGB", (width, height), pixels)
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
                filename = f"screenshot_{int(time.time())}.png"
                image.save(filename)
                print(f"¡Screenshot guardado como {filename}!")

# Limpieza
cap.release()
pygame.quit()