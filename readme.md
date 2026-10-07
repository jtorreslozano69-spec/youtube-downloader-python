# YouTube Downloader (customtkinter + yt-dlp)

Este es un proyecto personal que armé en Python para resolver un problema muy común: descargar videos y playlists de YouTube de forma rápida, sin anuncios molestos y con una interfaz limpia que no parezca de los años 90. 

Combina la potencia de `yt-dlp` (el motor de descargas) con un diseño visual moderno usando `customtkinter` (soporta modo oscuro de forma nativa). Además, tiene trucos lógicos para soportar listas de reproducción gigantescas (de más de 1,000 canciones) sin que YouTube bloquee tu dirección IP.

---

## Lo que hace la App

- **Elige la calidad:** Puedes bajar los videos en la mejor calidad disponible o limitarlos a 720p (HD) si quieres ahorrar espacio o internet.
- **Evita bloqueos (Anti-ban):** Agrega intervalos de espera aleatorios entre descargas. Ideal si vas a bajar playlists masivas.
- **Es portátil:** No usa rutas fijas con mi nombre de usuario. Detecta automáticamente el sistema donde se ejecuta y guarda los archivos directo en el Escritorio real de la computadora (sea Windows, Mac o Linux).
- **Limpia los enlaces:** Si pegas una URL con espacios ocultos o saltos de línea invisibles por accidente, el programa los limpia antes de validar el link para que no falle.

---

## Cómo ponerlo a correr en tu PC

### 1. Clona el proyecto
```bash
git clone https://github.com
cd TU_REPOSITORIO
```

### 2. Instala las librerías necesarias
Asegúrate de tener Python instalado y ejecuta en tu terminal:
```bash
pip install yt-dlp customtkinter
```

### 3. El ingrediente secreto: FFmpeg (Obligatorio)
Para las resoluciones altas (1080p en adelante), YouTube guarda el video por un lado y el audio por el otro. La app los junta de forma invisible al terminar, pero para hacerlo necesita **FFmpeg** en tu sistema.

- **En Windows:** Abre tu consola como Administrador y escribe este comando rápido:
  ```bash
  winget install -e --id Gyan.FFmpeg.Essentials
  ```
  *(Ojo: Cierra y vuelve a abrir tu editor o consola después de que termine para que detecte el cambio).*
- **En Mac (usando Homebrew):** `brew install ffmpeg`

Luego de eso, solo ejecutas `python download_yt.py` y listo, a descargar.

- ### 4. Visual Studio Code

Abre el archivo `python download_yt.py` con Visual Studio Code, busca este triangulo

<img width="115" height="65" alt="image" src="https://github.com/user-attachments/assets/304850c9-a005-4e19-9b62-fac16c0cae02" />

y presiona en **Ejecutar archivo de python**

<img width="353" height="73" alt="image" src="https://github.com/user-attachments/assets/fccfde24-a6b5-4427-aa20-2294d0680a47" />

---

## Tecnologías usadas

- **Python 3** como base.
- **yt-dlp** para romper las restricciones de YouTube (el motor más actualizado actualmente).
- **CustomTkinter** para la interfaz visual moderna.
- **FFmpeg** para pegar y procesar los archivos multimedia en segundo plano.

---

## Licencia

Este proyecto está bajo la licencia **GNU GPLv3**. 

¿Qué significa esto en cristiano? Significa que el código es libre y comunitario. Puedes descargarlo, usarlo, romperlo y mejorarlo como quieras. Sin embargo, si decides modificarlo y publicar tu propia versión basada en esta app, estás obligado por ley a mantener tu código abierto, gratis y bajo esta misma licencia GPLv3. El software libre se queda libre siempre
