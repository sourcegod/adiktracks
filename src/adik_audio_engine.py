# adik_audio_engine.py
import sounddevice as sd
import numpy as np
import threading # Si nécessaire, mais sounddevice gère déjà son thread

class AdikAudioEngine:
    def __init__(self, sample_rate=44100, block_size=1024, num_output_channels=2):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.num_output_channels = num_output_channels
        self.stream = None
        self._callback_function = None # Le callback que l'engine appellera

        print(f"AdikAudioEngine initialisé (SR: {self.sample_rate}, Block Size: {self.block_size}, Out Channels: {self.num_output_channels})")

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
        """Démarre le stream audio."""
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

    def stop_stream(self):
        """Arrête et ferme le stream audio."""
        if self.stream:
            self.stream.close() # close() arrête et nettoie
            self.stream = None
            print("Engine: Stream audio arrêté.")
    #----------------------------------------

    def is_stream_active(self):
        """Retourne True si le stream audio est actif."""
        return self.stream is not None and self.stream.active

    #----------------------------------------

