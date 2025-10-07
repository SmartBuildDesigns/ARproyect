# Realidad Aumentada con OpenCV, Pygame y OpenGL

Este proyecto es una aplicación de Realidad Aumentada (RA) basada en marcadores, desarrollada completamente en Python. Utiliza un tablero de ajedrez como marcador físico para detectar una superficie y superponer un modelo 3D en tiempo real sobre la transmisión de video de una cámara web.

![Ejemplo de la App en funcionamiento](https://i.imgur.com/AR-demo.gif) ---

## 🛠️ Tecnologías Utilizadas
* **OpenCV:** Para la captura de video, corrección de imagen, detección del marcador (tablero de ajedrez) y el cálculo de la pose de la cámara.
* **PyOpenGL:** Para todo el renderizado de la escena 3D, incluyendo el modelo, la iluminación y las texturas.
* **Pygame:** Para la creación de la ventana, el contexto de OpenGL y la gestión de eventos de teclado.
* **PyWavefront:** Para la carga de modelos 3D en el popular formato `.obj`.
* **NumPy:** Para todas las operaciones numéricas y matriciales de alto rendimiento.

---

## ✨ Características Principales
* **Tracking en Tiempo Real:** Detecta un tablero de ajedrez y sigue su posición y orientación (pose) con alta precisión.
* **Renderizado de Modelos 3D:** Carga y muestra archivos `.obj` sobre el marcador, creando la ilusión de que el objeto está en el mundo real.
* **Control Interactivo:** Permite rotar el modelo en sus tres ejes y cambiar el modo de visualización (caras sólidas, malla de alambre o puntos).
* **Control de Nivel de Detalle (LOD):** Aumenta o disminuye dinámicamente la complejidad del modelo para optimizar el rendimiento, mostrando más o menos caras.
* **Captura de Pantalla:** Guarda una imagen de la escena de RA actual con solo presionar una tecla.

---

## ⚙️ Requisitos e Instalación
Necesitas tener **Python 3** instalado. Puedes instalar todas las dependencias del proyecto ejecutando el siguiente comando en tu terminal:
```bash
pip install opencv-python numpy pygame PyOpenGL pywavefront Pillow
```

---

## 🚀 Cómo Ejecutar el Proyecto

1.  **Calibrar la Cámara:** Antes que nada, debes calibrar tu cámara. Generalmente, esto implica ejecutar un script de calibración por separado que te pide mostrarle un tablero de ajedrez desde diferentes ángulos. Este proceso genera el archivo `calibracion_camara.npz`, que es vital para la precisión de la aplicación.
2.  **Imprimir el Marcador:** Necesitarás un tablero de ajedrez físico con un patrón de **9x6 esquinas internas**. Este es el marcador que la cámara buscará.
3.  **Ejecutar la Aplicación:**
    ```bash
    python main.py
    ```
4.  **Enfocar el Marcador:** Apunta la cámara hacia el tablero de ajedrez. Una vez que lo detecte, el modelo 3D aparecerá sobre él.

---

## ⌨️ Controles
* **`w` / `p` / `f`**: Cambiar modo de vista (Wireframe / Puntos / Caras).
* **`r` / `t` / `y`**: Rotar el modelo en los ejes X, Y, Z. (Mantén `SHIFT` para rotar en sentido contrario).
* **`+` / `-`**: Aumentar/disminuir el tamaño de los puntos y el grosor de las líneas.
* **`[`**: Disminuir el detalle del modelo (renderiza menos caras).
* **`]`**: Aumentar el detalle del modelo (renderiza más caras).
* **`s`**: Tomar una captura de pantalla (se guarda en la carpeta del proyecto).
* **`q` / `ESC`**: Salir del programa.

---

## 🔬 La Importancia Crucial de la Calibración de la Cámara

Para que la Realidad Aumentada funcione, el mundo virtual 3D y el mundo real deben estar perfectamente alineados. La calibración de la cámara es el puente que hace posible esta alineación. Sin ella, la ilusión se rompe por completo.

Una cámara no es un dispositivo de medición perfecto; su lente introduce **distorsión** y sus propiedades internas (como la distancia focal) son desconocidas para el programa. La calibración resuelve estos dos problemas.


*A la izquierda, una imagen con distorsión. A la derecha, la misma imagen corregida digitalmente gracias a los parámetros de calibración.*

### Los Parámetros de Calibración

El proceso de calibración genera dos piezas clave de información:

1.  **`dist` (Coeficientes de Distorsión):** Un conjunto de valores que describen matemáticamente cómo la lente deforma la imagen. Son la "receta" para revertir esta distorsión y "enderezar" la imagen.
2.  **`mtx` (Matriz Intrínseca):** Una matriz de 3x3 que contiene el "ADN" geométrico de la cámara:
    * **`fx`, `fy` (Distancia Focal):** Definen el campo de visión y la perspectiva de la cámara.
    * **`cx`, `cy` (Punto Principal):** Las coordenadas del centro óptico exacto del sensor.

### ¿Cómo se Usan en el Código?

Estos parámetros son utilizados en tres pasos críticos:

1.  **`cv2.undistort()`:** Antes de cualquier análisis, el fotograma capturado se "limpia" usando los coeficientes `dist`. Esto asegura que todas las líneas rectas del mundo real sean rectas en la imagen procesada, permitiendo una detección precisa de las esquinas del marcador.
    ```python
    frame_undist = cv2.undistort(frame, mtx, dist, None, mtx)
    ```

2.  **`cv2.solvePnP()`:** Esta función calcula la posición y rotación 3D del marcador. Para poder traducir las coordenadas 2D de las esquinas detectadas en la imagen a una pose 3D, **necesita la matriz `mtx`**. Esta matriz le proporciona el contexto de la perspectiva de la cámara, permitiéndole resolver la pose correctamente.
    ```python
    _, rvec, tvec = cv2.solvePnP(objp, corners2, mtx, dist)
    ```

3.  **`set_projection_from_camera()`:** Finalmente, para que el objeto 3D se dibuje con la misma perspectiva que el mundo real, la "cámara virtual" de OpenGL debe imitar perfectamente a la cámara real. Esta función utiliza los valores `fx, fy, cx, cy` de la matriz `mtx` para construir la matriz de proyección de OpenGL.
    ```python
    def set_projection_from_camera(mtx):
        # ... extrae fx, fy, cx, cy de mtx para configurar glFrustum
    ```

En resumen, la calibración establece una **cadena de precisión matemática**. Sin ella, la detección sería inexacta, el cálculo de la pose 3D sería incorrecto y el renderizado virtual no coincidiría con la perspectiva real, resultando en un objeto 3D que tiembla, se desliza y no se siente anclado al mundo real.

## Entendiendo los Archivos 3D: `.obj`, `.mtl` y las Texturas

Para que un objeto 3D se vea realista, necesita más que solo una forma. Necesita color, material y detalles en su superficie. En este proyecto, esto se logra a través de una combinación de tres tipos de archivos:

1.  **El Modelo (`.obj`):** Define la **geometría** del objeto.
2.  **El Material (`.mtl`):** Describe **cómo se ve la superficie** (color, brillo, etc.).
3.  **La Textura (`.png`, `.jpg`):** Es la **imagen que "envuelve"** al modelo para darle detalle.


*A la izquierda, un modelo 3D solo con su geometría. A la derecha, el mismo modelo con materiales y texturas aplicadas.*

### 1. El Formato de Malla: `.obj` (Wavefront OBJ)

El archivo `.obj` es uno de los formatos de modelos 3D más antiguos y populares, principalmente porque es de **texto plano** y muy fácil de interpretar. Se encarga de definir la **estructura o "esqueleto"** del modelo.

Dentro de un archivo `.obj`, encontrarás principalmente estas líneas:
* `v` (Vértice): Define un punto en el espacio 3D con coordenadas X, Y, Z. Son los "ladrillos" fundamentales de la malla.
    ```
    v 1.000000 0.500000 -0.250000
    ```
* `vt` (Vértice de Textura): Define una coordenada 2D (U, V) que indica qué punto de la imagen de textura corresponde a un vértice de la malla.
    ```
    vt 0.500000 0.500000
    ```
* `vn` (Normal de Vértice): Define la orientación de la superficie en un vértice, lo cual es crucial para calcular cómo la luz rebota en el objeto.
    ```
    vn 0.000000 1.000000 0.000000
    ```
* `f` (Cara): Define una cara poligonal (generalmente un triángulo o un cuadrado) conectando varios vértices. Esta es la línea que finalmente "construye" la superficie.
    ```
    # Formato: vértice/vértice_textura/normal
    f 1/1/1 2/2/1 3/3/1
    ```

**Importante:** El archivo `.obj` no contiene información de color o material. Para eso, hace referencia a otro archivo.

### 2. La Librería de Materiales: `.mtl` (Material Template Library)

El archivo `.obj` generalmente incluye una línea al principio que enlaza a su archivo de materiales:
```
mtllib mi_modelo.mtl
```

El archivo `.mtl` es también un archivo de texto que describe las propiedades de la superficie. Dentro de él, se definen uno o más materiales. Las directivas más comunes son:

* `newmtl NombreDelMaterial`: Inicia la definición de un nuevo material.
* `Ka`, `Kd`, `Ks`: Definen los colores **Ambiente**, **Difuso** y **Especular** del material en formato RGB.
    * **Color Difuso (`Kd`):** Es el color base del objeto bajo luz blanca directa.
    * **Color Especular (`Ks`):** Es el color del reflejo brillante (el "brillo" en un objeto pulido).
* `Ns`: Define el **brillo especular** (un valor alto crea un reflejo pequeño y concentrado, como en el metal; un valor bajo crea uno amplio, como en el plástico).
* **`map_Kd`**: ¡Esta es la directiva más importante para las texturas! Le dice al motor de renderizado que **use una imagen como el color difuso** del material.

```mtl
# Ejemplo de un archivo .mtl

newmtl MaterialLucario
Ns 250.0
Ka 1.0 1.0 1.0  # Luz ambiental
Kd 0.8 0.8 0.8  # Color difuso (base)
Ks 0.5 0.5 0.5  # Color del brillo especular
map_Kd textura_lucario.png  # <--- ¡Aquí se enlaza la imagen de la textura!
```

### 3. La Textura: Archivos de Imagen (`.png`, `.jpg`, etc.)

Este es el archivo de imagen que `map_Kd` especifica. La **textura** es una imagen 2D que se "envuelve" alrededor del modelo 3D siguiendo las coordenadas `vt` definidas en el archivo `.obj`. Este proceso, llamado **UV mapping**, es lo que permite que un simple polígono parezca tener detalles complejos como piel, tela, madera o metal.



### La Relación en Conjunto

El flujo de trabajo es el siguiente:

1.  `main.py` carga el `Lucario.obj` usando `pywavefront`.
2.  `pywavefront` lee el `.obj` y ve la línea `mtllib Lucario.mtl`.
3.  Automáticamente, carga el `Lucario.mtl` para obtener las propiedades de los materiales.
4.  Al leer el material, encuentra la directiva `map_Kd Lucario_Textura.png`.
5.  Finalmente, carga la imagen `Lucario_Textura.png` y la prepara para que OpenGL la "pinte" sobre la geometría del `.obj` cuando se renderice.

Comprender esta separación entre **forma (`.obj`)**, **superficie (`.mtl`)** e **imagen (`.png`)** es clave para trabajar con cualquier tipo de gráficos 3D.

## De la Cámara a OpenGL: La Transformación Mágica

Una vez que tenemos los parámetros de calibración (`mtx`, `dist`) y la pose del marcador en el mundo real (`rvec`, `tvec` de `solvePnP`), nos enfrentamos al último gran desafío: **traducir esta información al lenguaje de OpenGL**.

Esto no es directo, ya que OpenCV y OpenGL "ven" el mundo de maneras diferentes; usan **sistemas de coordenadas distintos**.

* **OpenCV (Cámara):** Considera que **+Y** es hacia **abajo** y **+Z** es hacia **adelante** (saliendo de la pantalla hacia el espectador).
* **OpenGL (Cámara):** Considera que **+Y** es hacia **arriba** y **-Z** es hacia **adelante**.


*Comparación de los sistemas de coordenadas. Es necesario un ajuste para que ambos "mundos" coincidan.*

Para alinear el objeto 3D virtual con el mundo real, debemos configurar dos matrices principales en OpenGL: la matriz de **Vista (Model-View)** y la de **Proyección**.

---

### 1. La Matriz de Vista (Model-View): Posicionando el Mundo

La matriz de Vista le dice a OpenGL desde dónde y con qué orientación se está mirando la escena. En nuestro caso, esta matriz debe replicar la pose exacta de nuestra cámara web real.

El proceso en el código es el siguiente:

1.  **Obtener Pose:** `cv2.solvePnP` nos da un vector de rotación (`rvec`) y uno de traslación (`tvec`) que describen la pose del marcador en el sistema de coordenadas de OpenCV.

2.  **Convertir a Matriz:** La rotación `rvec` se convierte en una matriz de rotación de 3x3, `R`, usando `cv2.Rodrigues(rvec)`.

3.  **Crear Matriz de Pose:** Se combina la matriz de rotación `R` y el vector de traslación `tvec` en una sola matriz de transformación de 4x4 (`pose_matrix`).

4.  **Corregir Coordenadas:** Aquí está el paso crucial. Antes de pasarle la `pose_matrix` a OpenGL, la multiplicamos por una matriz de conversión que invierte los ejes Y y Z para adaptarlos al sistema de OpenGL.
    ```python
    # Esta matriz voltea el signo de los ejes Y y Z
    gl_convert = np.array([[1, 0, 0, 0],
                           [0,-1, 0, 0],
                           [0, 0,-1, 0],
                           [0, 0, 0, 1]])
    
    # Se establece el modo de matriz y se carga la conversión
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glMultMatrixf(gl_convert.T) # .T es para transponer la matriz
    
    # Ahora se multiplica por la pose del marcador
    glMultMatrixf(pose_matrix.T)
    ```
Al hacer esto, hemos movido y rotado toda la escena de OpenGL para que la cámara virtual quede perfectamente alineada con la cámara real respecto al marcador.

---

### 2. La Matriz de Proyección: Imitando el Lente de la Cámara

La matriz de Proyección define las propiedades del "lente" de la cámara virtual: su campo de visión, su relación de aspecto y cómo se representa la perspectiva. Para que la ilusión sea perfecta, este lente virtual debe ser un clon del lente de nuestra cámara web.

Aquí es donde la **matriz intrínseca (`mtx`)** vuelve a ser protagonista. La función `set_projection_from_camera` realiza esta tarea:

1.  **Extraer Parámetros:** La función toma la matriz `mtx` y extrae los valores de distancia focal (`fx`, `fy`) y el punto principal (`cx`, `cy`).
    $$
    mtx = \begin{pmatrix} f_x & 0 & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{pmatrix}
    $$

2.  **Construir un Frustum:** OpenGL no usa directamente estos valores, pero sí una función llamada `glFrustum`. Esta función define la pirámide de visión de la cámara. El código utiliza fórmulas matemáticas para convertir `fx, fy, cx, cy` en los parámetros (`left`, `right`, `bottom`, `top`) que `glFrustum` necesita.
    ```python
    def set_projection_from_camera(mtx):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        fx, fy = mtx[0, 0], mtx[1, 1]
        cx, cy = mtx[0, 2], mtx[1, 2]
        
        # Calcular los bordes de la pirámide de visión
        left   = -cx * z_near / fx
        right  = (width - cx) * z_near / fx
        bottom = -(height - cy) * z_near / fy
        top    = cy * z_near / fy
        
        # Establecer la proyección de OpenGL para que coincida con la cámara
        glFrustum(left, right, bottom, top, z_near, z_far)
    ```
Este paso garantiza que los objetos 3D se rendericen con la misma distorsión de perspectiva que captura la cámara real, completando así la integración entre el mundo real y el virtual.
