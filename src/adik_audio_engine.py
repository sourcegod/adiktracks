# adik_audio_engine.py
import sounddevice as sd
import numpy as np
import threading # Si nécessaire, mais sounddevice gère déjà son thread

class AdikAudioEngine:
    def __init__(self, sample_rate=44100, block_size=1024, num_output_channels=2, num_input_channels=1):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.num_output_channels = num_output_channels
        self.num_input_channels = num_input_channels # NOUVEAU: Nombre de canaux d'entrée

        self.stream = None
        self._callback_function = None # Le callback que l'engine appellera

        try:
            sd.check_output_settings(samplerate=self.sample_rate, channels=self.num_output_channels)
            sd.check_input_settings(samplerate=self.sample_rate, channels=self.num_input_channels)
            print(f"Engine: Périphériques audio par défaut: Entrée='{sd.query_devices(kind='input')['name']}', Sortie='{sd.query_devices(kind='output')['name']}'")
        except sd.PortAudioError as e:
            print(f"Engine: Avertissement: Problème avec les périphériques audio par défaut: {e}")
            print("Veuillez vérifier vos périphériques audio et leurs paramètres.")

        # print(f"AdikAudioEngine initialisé (SR: {self.sample_rate}, Block Size: {self.block_size}, Out Channels: {self.num_output_channels})")

    #----------------------------------------

    def set_callback(self, callback_func):
        """
        Définit la fonction de rappel qui sera appelée par le stream audio.
        Cette fonction recevra (outdata, frames, time_info, status).
        """
        if callable(callback_func):
            self._callback_function = callback_func
        else:
            raise ValueError("Le callback fourni n'est pas une fonction callable.")

    #----------------------------------------

    def start_stream(self):
        """Démarre le stream audio (maintenant avec support d'entrée/sortie)."""
        if self.stream and self.stream.active:
            print("Engine: Stream audio déjà actif.")
            return

        if self._callback_function is None:
            print("Engine: Aucun callback défini. Impossible de démarrer le stream.")
            return

        try:
            # MODIFICATION ICI: Utilisation de sd.Stream pour l'entrée et la sortie
            self.stream = sd.Stream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                channels=[self.num_input_channels, self.num_output_channels], # [canaux_entrée, canaux_sortie]
                dtype='float32',
                callback=self._callback_function,
                # NOUVEAU: Paramètres pour l'entrée
                # device=None # Utilise les périphériques par défaut
            )
            self.stream.start()
            print("Engine: Stream audio démarré (lecture et enregistrement).")
        except Exception as e:
            print(f"Engine: Erreur lors du démarrage du stream audio: {e}.")
            self.stream = None

  
    #----------------------------------------

    """
    Deprecated function, for output stream only
    def start_stream(self):
        # Démarre le stream audio.
        if self.stream and self.stream.active:
            print("Engine: Stream audio déjà actif.")
            return

        if self._callback_function is None:
            print("Engine: Aucun callback défini. Impossible de démarrer le stream.")
            return

        try:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                channels=self.num_output_channels,
                dtype='float32',
                callback=self._callback_function # Utilise le callback fourni
            )
            self.stream.start()
            print("Engine: Stream audio démarré.")
        except Exception as e:
            print(f"Engine: Erreur lors du démarrage du stream audio: {e}.")
            self.stream = None
    #----------------------------------------
"""

    def stop_stream(self):
        """Arrête et ferme le stream audio."""
        if self.stream:
            self.stream.close() # close() arrête et nettoie
            self.stream = None
            print("Engine: Stream audio arrêté.")
    #----------------------------------------

    def is_running(self):
        """Retourne True si le stream audio est actif."""
        return self.stream is not None and self.stream.active

    #----------------------------------------

