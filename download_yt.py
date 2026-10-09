import yt_dlp
import os
import re
import shutil
import tempfile
import threading
import queue
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

ctk.set_appearance_mode("light")  # Modo oscuro
ctk.set_default_color_theme("green")  # Tema azul

def es_url_valida(url):
    # Expresión regular para validar links de cualquier sitio web (no solo YouTube)
    patron = r'^https?://.+'
    return bool(re.match(patron, url))

FORMATO_1080 = 'bestvideo[ext=mp4][vcodec^=avc1][height<=1080][height>=720]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080][height>=720]'
FORMATO_720 = 'bestvideo[ext=mp4][vcodec^=avc1][height=720]+bestaudio[ext=m4a]/best[ext=mp4][height=720]'

def formatear_tamano(tamano):
    if tamano is None:
        return "No disponible"

    for unidad in ("B", "KB", "MB", "GB", "TB"):
        if tamano < 1024 or unidad == "TB":
            return f"{tamano:.1f} {unidad}"
        tamano /= 1024

def estimar_tamano(ydl, info, selector):
    formatos = list(ydl.build_format_selector(selector)({
        'formats': info.get('formats', []),
        'incomplete': False,
    }))
    if not formatos:
        return None

    formato_seleccionado = formatos[0]
    componentes = formato_seleccionado.get('requested_formats') or [formato_seleccionado]
    tamanos = [
        componente.get('filesize') or componente.get('filesize_approx')
        for componente in componentes
    ]
    if any(tamano is None for tamano in tamanos):
        return None
    return sum(tamanos)

def mover_videos_finales(carpeta_temporal, carpeta_destino):
    nombres = [
        nombre for nombre in os.listdir(carpeta_temporal)
        if nombre.lower().endswith(".mp4")
        and ".temp." not in nombre.lower()
        and os.path.isfile(os.path.join(carpeta_temporal, nombre))
    ]
    if not nombres:
        raise RuntimeError("No se encontró ningún MP4 final después de la unión.")

    rutas_finales = []
    for nombre in nombres:
        base, extension = os.path.splitext(nombre)
        destino = os.path.join(carpeta_destino, nombre)
        numero = 2
        while os.path.exists(destino):
            destino = os.path.join(carpeta_destino, f"{base} ({numero}){extension}")
            numero += 1
        rutas_finales.append(shutil.move(os.path.join(carpeta_temporal, nombre), destino))
    return rutas_finales

def analizar_url(url):
    opciones = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'sleep_interval_requests': 1,
    }
    with yt_dlp.YoutubeDL(opciones) as ydl:
        info = ydl.extract_info(url, download=False)
        es_playlist = info.get('_type') == 'playlist' or info.get('entries') is not None
        if es_playlist:
            info = next((entrada for entrada in info.get('entries', []) if entrada), None)
            if info is None:
                raise ValueError("No se encontraron videos en la playlist.")

        pesos = {
            "1080p": estimar_tamano(ydl, info, FORMATO_1080),
            "720p": estimar_tamano(ydl, info, FORMATO_720),
        }
    return pesos, es_playlist

def descarshion_videitos(url, calidad, carpeta, status_callback, progress_callback=None, cancel_event=None, descargar_playlist=False, dialog_callback=None):
    try:
        if not os.path.exists(carpeta):
            os.makedirs(carpeta)
            
        if calidad == "1":
            formato_final = FORMATO_1080
        elif calidad == "2":
            formato_final = FORMATO_720
        else:
            if status_callback:
                status_callback("Calidad no válida. Se descargará la mejor calidad disponible.")
            formato_final = FORMATO_1080

        if cancel_event and cancel_event.is_set():
            raise yt_dlp.utils.DownloadCancelled("Descarga cancelada por el usuario")

        aviso_playlist = "Esto se puede demorar unos minutos.\n" if descargar_playlist else ""
        resolucion_str = "720p" if calidad == "2" else "hasta 1080p"

        def progress_hook(d):
            if cancel_event and cancel_event.is_set():
                raise yt_dlp.utils.DownloadCancelled("Descarga cancelada por el usuario")

            if d['status'] == 'downloading':
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                if total_bytes > 0:
                    tamano_mb = total_bytes / (1024 * 1024)
                    tamano_str = f"{tamano_mb:.2f} MB"
                else:
                    tamano_str = "Calculando..."

                if progress_callback and total_bytes > 0:
                    progreso = d.get('downloaded_bytes', 0) / total_bytes
                    progress_callback(min(progreso, 0.99))
                
                if status_callback:
                    status_callback(f"{aviso_playlist}Calidad: {resolucion_str}\nPeso descargado: {tamano_str}\nDescargando...")

        def postprocessor_hook(d):
            if d.get('postprocessor') != 'Merger':
                return
            if d.get('status') == 'started' and status_callback:
                status_callback("Descargas listas. Uniendo video y audio; puede tardar por el tamaño del archivo...")
            elif d.get('status') == 'finished' and status_callback:
                status_callback("Video y audio unidos.")
        
        opciones = {
            'format': formato_final,
            'noplaylist': not descargar_playlist,
            'merge_output_format': 'mp4',
            'sleep_interval': 5,
            'max_sleep_interval': 10,
            'sleep_interval_requests': 1,
            'progress_hooks': [progress_hook],
            'postprocessor_hooks': [postprocessor_hook],
        }
        
        if status_callback:
            status_callback(f"{aviso_playlist}Descargando video en {resolucion_str}...")
        
        with tempfile.TemporaryDirectory(prefix="download_yt_") as carpeta_temporal:
            opciones['outtmpl'] = os.path.join(carpeta_temporal, "%(title)s.%(ext)s")
            with yt_dlp.YoutubeDL(opciones) as ydl:
                resultado = ydl.download([url])

            if cancel_event and cancel_event.is_set():
                if status_callback:
                    status_callback("Descarga cancelada.")
                return
            if resultado != 0:
                raise RuntimeError(f"yt-dlp terminó con el código {resultado}; la descarga o unión del video no se completó.")

            mover_videos_finales(carpeta_temporal, carpeta)

        if progress_callback:
            progress_callback(1.0)
        if status_callback:
            status_callback("Descarga completada. El video se ha guardado en: " + carpeta)
        if dialog_callback:
            dialog_callback("info", "Descarga completada", f"El video se ha guardado en: {carpeta}")

    except yt_dlp.utils.DownloadCancelled:
        if status_callback:
            status_callback("Descarga cancelada.")
        
    except Exception as e:
        if cancel_event and cancel_event.is_set():
            if status_callback:
                status_callback("Descarga cancelada.")
            return
        if status_callback:
            status_callback(f"Error al descargar el video: {e}")
        if dialog_callback:
            dialog_callback("error", "Error", f"Error al descargar el video: {e}")
        
class DescargadorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Descargador de Videos de YouTube")
        self.geometry("520x590")
        self.resizable(False, False)
        self.cancel_event = threading.Event()
        self.eventos = queue.Queue()
        self._url_analizada = None
        self._analisis_id = 0
        self._pesos_estimados = None
        self._playlist_analizada = False

        # Título
        self.titulo_label = ctk.CTkLabel(self, text="Descargador de Videos", font=ctk.CTkFont(size=20, weight="bold"))
        self.titulo_label.pack(pady=(20, 10))

        # Widgets
        self.url_label = ctk.CTkLabel(self, text="Ingrese la URL del video:", font=ctk.CTkFont(size=12, weight="bold"))
        self.url_label.pack(pady=(20, 10))

        frame_url = ctk.CTkFrame(self, fg_color="transparent")
        frame_url.pack(pady=(5, 15))

        self.url_entry = ctk.CTkEntry(frame_url, width=330, height=35, placeholder_text="https://www.youtube.com/watch?v=...")
        self.url_entry.pack(side=ctk.LEFT, padx=(0, 10))

        self.url_entry.bind("<Return>", self.analizar_resolucion_url)

        self.btn_analizar = ctk.CTkButton(frame_url, text="ANALIZAR", width=100, height=35, command=self.analizar_resolucion_url)
        self.btn_analizar.pack(side=ctk.LEFT)

        frame_progreso = ctk.CTkFrame(self, fg_color="transparent", width=440)
        frame_progreso.pack(pady=(0, 10))

        self.progress_bar = ctk.CTkProgressBar(
            frame_progreso,
            width=385,
            height=12,
            corner_radius=6,
            fg_color="#010101",
            progress_color="#018A27",
        )
        self.progress_bar.pack(side=ctk.LEFT, padx=(0, 10))

        self.progress_label = ctk.CTkLabel(
            frame_progreso,
            text="0%",
            width=40,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.progress_label.pack(side=ctk.LEFT)
        self.progress_bar.set(0)

        # Guardado
        self.carpeta_label = ctk.CTkLabel(self, text="Carpeta de guardado:", font=ctk.CTkFont(size=12, weight="bold"))
        self.carpeta_label.pack(anchor="w", padx=40)

        frame_carpeta = ctk.CTkFrame(self, fg_color="transparent")
        frame_carpeta.pack(pady=(5, 15))

        self.carpeta_entry = ctk.CTkEntry(frame_carpeta, width=335, height=35)
        self.carpeta_entry.pack(side=ctk.LEFT, padx=(0, 10))
        self.carpeta_entry.insert(0, os.path.join(os.path.expanduser("~"), "Desktop"))

        self.btn_examinar = ctk.CTkButton(frame_carpeta, text="Examinar", width=95, height=35, command=self.seleccionar_carpeta)
        self.btn_examinar.pack(side=ctk.LEFT)

        # Calidad
        self.calidad_label = ctk.CTkLabel(self, text="Calidad:", font=ctk.CTkFont(size=12, weight="bold"))
        self.calidad_label.pack(anchor="w", padx=40)

        self.calidad_var = ctk.StringVar(value="1")
        
        frame_radio = ctk.CTkFrame(self, fg_color="transparent")
        frame_radio.pack(anchor="w", padx=40, pady=5)

        self.rb1 = ctk.CTkRadioButton(
            frame_radio,
            text="Hasta 1080p",
            variable=self.calidad_var,
            value="1",
            command=self.actualizar_peso_calidad,
        )
        self.rb1.pack(side=ctk.LEFT, padx=(0, 20))

        self.rb2 = ctk.CTkRadioButton(
            frame_radio,
            text="720p",
            variable=self.calidad_var,
            value="2",
            command=self.actualizar_peso_calidad,
        )
        self.rb2.pack(side=ctk.LEFT)

        self.peso_estimado_label = ctk.CTkLabel(
            self,
            text="Peso estimado: analiza una URL",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#060606",
        )
        self.peso_estimado_label.pack(anchor="w", padx=40, pady=(0, 4))

        self.descargar_playlist_var = ctk.BooleanVar(value=False)
        self.playlist_checkbox = ctk.CTkCheckBox(
            self,
            text="Descargar playlist completa",
            variable=self.descargar_playlist_var,
        )
        self.playlist_checkbox.pack(anchor="w", padx=40, pady=(5, 0))

        # Botones de descarga y cancelación
        frame_acciones = ctk.CTkFrame(self, fg_color="transparent")
        frame_acciones.pack(pady=20)

        self.btn_descargar = ctk.CTkButton(frame_acciones, text="DESCARGAR", width=180, height=42, font=ctk.CTkFont(size=14, weight="bold"), command=self.iniciar_descarga)
        self.btn_descargar.pack(side=ctk.LEFT, padx=(0, 10))

        self.btn_cancelar = ctk.CTkButton(
            frame_acciones,
            text="CANCELAR",
            width=125,
            height=42,
            fg_color="#A63D40",
            hover_color="#873236",
            command=self.cancelar_descarga,
            state="disabled",
        )
        self.btn_cancelar.pack(side=ctk.LEFT)

        # Estado
        self.status_text = ctk.CTkTextbox(self, height=80, width=440)
        self.status_text.pack(pady=(0, 15))
        self.status_text.insert("0.0", "Listo para descargar...\n")
        self.status_text.configure(state="disabled")
        self.after(100, self.procesar_eventos)

    def seleccionar_carpeta(self):
        carpeta_seleccionada = filedialog.askdirectory()
        if carpeta_seleccionada:
            self.carpeta_entry.delete(0, ctk.END)
            self.carpeta_entry.insert(0, carpeta_seleccionada)

    def analizar_resolucion_url(self, event=None):
        url = self.url_entry.get().strip()
        if not es_url_valida(url) or url == self._url_analizada:
            return

        self._url_analizada = url
        self._pesos_estimados = None
        self._playlist_analizada = False
        self._analisis_id += 1
        analisis_id = self._analisis_id
        self.btn_analizar.configure(state="disabled")
        self.btn_descargar.configure(state="disabled")
        self.peso_estimado_label.configure(text="Calculando peso para ambas calidades...")
        self.actualizar_estado("Analizando resoluciones y pesos estimados...")

        def tarea():
            error_mensaje = None
            try:
                pesos, es_playlist = analizar_url(url)
            except Exception as error:
                pesos = None
                es_playlist = False
                error_mensaje = str(error)

            self.eventos.put(("analisis", analisis_id, url, pesos, es_playlist, error_mensaje))

        threading.Thread(target=tarea, daemon=True).start()

    def mostrar_resultado_analisis(self, analisis_id, url, pesos, es_playlist, error):
        if analisis_id != self._analisis_id:
            return

        self.btn_analizar.configure(state="normal")
        self.btn_descargar.configure(state="normal")
        if url != self.url_entry.get().strip():
            return

        if error:
            self._url_analizada = None
            self.peso_estimado_label.configure(text="No se pudo estimar el peso")
            self.actualizar_estado(f"Error al analizar la URL: {error}")
            return

        self._pesos_estimados = pesos
        self._playlist_analizada = es_playlist
        self.actualizar_peso_calidad()
        self.actualizar_estado("Análisis completado. El peso corresponde a la calidad seleccionada.")

    def actualizar_peso_calidad(self):
        if self._pesos_estimados is None:
            return

        if self.calidad_var.get() == "2":
            calidad = "720p"
            peso = self._pesos_estimados["720p"]
        else:
            calidad = "hasta 1080p"
            peso = self._pesos_estimados["1080p"]

        alcance = " por video (primer elemento de la playlist)" if self._playlist_analizada else ""
        self.peso_estimado_label.configure(
            text=f"Peso estimado para {calidad}: {formatear_tamano(peso)}{alcance}"
        )

    def cancelar_descarga(self):
        self.cancel_event.set()
        self.btn_cancelar.configure(state="disabled")
        self.actualizar_estado("Cancelando descarga...")

    def finalizar_descarga(self):
        self.btn_descargar.configure(state="normal")
        self.btn_cancelar.configure(state="disabled")
        self.btn_analizar.configure(state="normal")

    def procesar_eventos(self):
        while True:
            try:
                evento = self.eventos.get_nowait()
            except queue.Empty:
                break

            if evento[0] == "estado":
                self.actualizar_estado(evento[1])
            elif evento[0] == "progreso":
                self.actualizar_progreso(evento[1])
            elif evento[0] == "analisis":
                self.mostrar_resultado_analisis(*evento[1:])
            elif evento[0] == "dialogo":
                _, tipo, titulo, mensaje = evento
                if tipo == "info":
                    messagebox.showinfo(titulo, mensaje)
                else:
                    messagebox.showerror(titulo, mensaje)
            elif evento[0] == "fin_descarga":
                self.finalizar_descarga()

        self.after(100, self.procesar_eventos)

    def actualizar_estado(self, mensaje):
        self.status_text.configure(state="normal")
        self.status_text.delete("0.0", "end")
        self.status_text.insert("0.0", mensaje)
        self.status_text.configure(state="disabled")
        self.update_idletasks()

    def actualizar_progreso(self, progreso):
        self.progress_bar.set(progreso)
        self.progress_label.configure(text=f"{int(progreso * 100)}%")

    def iniciar_descarga(self):
        url = self.url_entry.get().strip()
        calidad = self.calidad_var.get().strip()
        carpeta = self.carpeta_entry.get().strip()

        if not es_url_valida(url):
            messagebox.showerror("Error", "La URL ingresada no es válida.")
            return

        if not calidad in ["1", "2"]:
            messagebox.showerror("Error", "La calidad ingresada no es válida.")
            return

        if not carpeta:
            messagebox.showerror("Error", "Debe seleccionar una carpeta de guardado.")
            return

        self.btn_descargar.configure(state="disabled")
        self.btn_cancelar.configure(state="normal")
        self.btn_analizar.configure(state="disabled")
        self.cancel_event.clear()
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")
        descargar_playlist = self.descargar_playlist_var.get()

        def tarea():
            try:
                descarshion_videitos(
                    url,
                    calidad,
                    carpeta,
                    lambda mensaje: self.eventos.put(("estado", mensaje)),
                    lambda progreso: self.eventos.put(("progreso", progreso)),
                    self.cancel_event,
                    descargar_playlist,
                    lambda tipo, titulo, mensaje: self.eventos.put(("dialogo", tipo, titulo, mensaje)),
                )
            finally:
                self.eventos.put(("fin_descarga",))

        threading.Thread(target=tarea).start()

if __name__ == "__main__":
    app = DescargadorApp()
    app.mainloop()