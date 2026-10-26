"""
app/vision/camera.py
Gestionnaire de flux vidéo unique (Singleton) en français.
Résout le problème de l'ouverture multiple de CAP_DSHOW sous Windows :
un seul thread d'arrière-plan capture les images et les partage à tous les clients connectés.
Prend en charge Windows (CAP_DSHOW / default), Linux (V4L2) et intègre un repli synthétique si aucune caméra n'est branchée.
"""

import sys
import time
import threading
from typing import Optional, Generator
import cv2
import numpy as np


class ServiceCamera:
    """Service vidéo thread-safe partagé entre toutes les requêtes /video_feed ou /flux_video."""

    _instance: Optional['ServiceCamera'] = None
    _verrou = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._verrou:
            if cls._instance is None:
                cls._instance = super(ServiceCamera, cls).__new__(cls)
                cls._instance._initialise = False
            return cls._instance

    def __init__(self, index_camera: int = 0, largeur: int = 640, hauteur: int = 480, **kwargs):
        if getattr(self, '_initialise', False):
            return
        self._initialise = True
        self.index_camera = kwargs.get("camera_index", index_camera)
        self.largeur = kwargs.get("width", largeur)
        self.hauteur = kwargs.get("height", hauteur)

        self.derniere_image: Optional[np.ndarray] = None
        self.dernier_jpeg: Optional[bytes] = None
        # Génération d'une première mire par défaut pour affichage immédiat
        image_initiale = self._generer_mire_test(0)
        succes, tampon = cv2.imencode('.jpg', image_initiale, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if succes:
            self.derniere_image = image_initiale
            self.dernier_jpeg = tampon.tobytes()

        self.en_cours = False
        self.materiel_detecte = False
        self._fil_capture: Optional[threading.Thread] = None
        self._verrou_image = threading.Lock()

    # --- Propriétés de rétrocompatibilité anglaise ---

    @property
    def camera_index(self) -> int:
        return self.index_camera

    @camera_index.setter
    def camera_index(self, v: int):
        self.index_camera = v

    @property
    def width(self) -> int:
        return self.largeur

    @width.setter
    def width(self, v: int):
        self.largeur = v

    @property
    def height(self) -> int:
        return self.hauteur

    @height.setter
    def height(self, v: int):
        self.hauteur = v

    @property
    def last_frame(self) -> Optional[np.ndarray]:
        return self.derniere_image

    @last_frame.setter
    def last_frame(self, v: Optional[np.ndarray]):
        self.derniere_image = v

    @property
    def last_jpeg(self) -> Optional[bytes]:
        return self.dernier_jpeg

    @last_jpeg.setter
    def last_jpeg(self, v: Optional[bytes]):
        self.dernier_jpeg = v

    @property
    def running(self) -> bool:
        return self.en_cours

    @running.setter
    def running(self, v: bool):
        self.en_cours = v

    @property
    def has_hardware(self) -> bool:
        return self.materiel_detecte

    @has_hardware.setter
    def has_hardware(self, v: bool):
        self.materiel_detecte = v

    @property
    def _thread(self) -> Optional[threading.Thread]:
        return self._fil_capture

    @_thread.setter
    def _thread(self, v: Optional[threading.Thread]):
        self._fil_capture = v

    @property
    def _frame_lock(self) -> threading.Lock:
        return self._verrou_image

    # --- Méthodes principales ---

    def demarrer(self):
        """Démarre le thread de capture unique."""
        if self.en_cours:
            return
        self.en_cours = True
        self._fil_capture = threading.Thread(target=self._boucle_capture, daemon=True)
        self._fil_capture.start()

    start = demarrer

    def arreter(self):
        """Arrête le thread de capture."""
        self.en_cours = False
        if self._fil_capture and self._fil_capture.is_alive():
            self._fil_capture.join(timeout=1.0)

    stop = arreter

    def _ouvrir_camera(self) -> Optional[cv2.VideoCapture]:
        # Détection du backend adapté à la plateforme
        if sys.platform.startswith("win"):
            cap = cv2.VideoCapture(self.index_camera, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(self.index_camera)

        if cap and cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.largeur)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.hauteur)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            return cap
        return None

    _open_camera = _ouvrir_camera

    def _boucle_capture(self):
        cap = self._ouvrir_camera()
        self.materiel_detecte = cap is not None and cap.isOpened()
        if not self.materiel_detecte:
            print("[Camera] Aucune caméra physique détectée -> Génération de mire de test synthétique.")

        compteur_images = 0
        while self.en_cours:
            image = None
            if self.materiel_detecte and cap is not None:
                succes, image_brute = cap.read()
                if succes and image_brute is not None:
                    image = cv2.resize(image_brute, (self.largeur, self.hauteur))
                else:
                    self.materiel_detecte = False
                    if cap:
                        cap.release()
                    cap = None

            if image is None:
                # Génération d'une mire vidéo simulée
                image = self._generer_mire_test(compteur_images)
                compteur_images += 1
                time.sleep(0.04)  # ~25 fps

            # Encodage JPEG unique pour tous les clients
            succes, tampon = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if succes:
                octets_jpeg = tampon.tobytes()
                with self._verrou_image:
                    self.derniere_image = image
                    self.dernier_jpeg = octets_jpeg

            time.sleep(0.01)

        if cap:
            cap.release()

    _capture_loop = _boucle_capture

    def _generer_mire_test(self, indice_image: int) -> np.ndarray:
        """Génère une mire de calibration synthétique avec repères et horodatage."""
        img = np.zeros((self.hauteur, self.largeur, 3), dtype=np.uint8)
        img[:] = (30, 30, 30)

        # Grille de repérage
        for x in range(0, self.largeur, 40):
            cv2.line(img, (x, 0), (x, self.hauteur), (45, 45, 45), 1)
        for y in range(0, self.hauteur, 40):
            cv2.line(img, (0, y), (self.largeur, y), (45, 45, 45), 1)

        # Zone du tapis de travail (simulation)
        cv2.rectangle(img, (120, 80), (520, 400), (0, 102, 255), 2)
        cv2.putText(img, "ZONE DE TRI - DOBOT", (130, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 102, 255), 2)

        # Objets simulés
        cv2.rectangle(img, (200, 220), (250, 270), (0, 0, 220), -1)   # Cube rouge
        cv2.circle(img, (360, 240), 22, (0, 200, 0), -1)              # Cylindre vert

        # Horodatage
        horodatage = time.strftime("%H:%M:%S")
        cv2.putText(img, f"MIRE SIMULATION | {horodatage}", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        return img

    _generate_test_pattern = _generer_mire_test

    def obtenir_dernier_jpeg(self) -> Optional[bytes]:
        with self._verrou_image:
            return self.dernier_jpeg

    get_latest_jpeg = obtenir_dernier_jpeg

    def obtenir_derniere_image(self) -> Optional[np.ndarray]:
        with self._verrou_image:
            return self.derniere_image.copy() if self.derniere_image is not None else None

    get_latest_frame = obtenir_derniere_image


# Alias de compatibilité
CameraService = ServiceCamera


def generer_flux_mjpeg() -> Generator[bytes, None, None]:
    """Générateur HTTP multipart pour le streaming web."""
    service = ServiceCamera()
    service.demarrer()

    while True:
        jpeg = service.obtenir_dernier_jpeg()
        if jpeg:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n')
        time.sleep(0.04)  # ~25 FPS


generate_mjpeg_stream = generer_flux_mjpeg
