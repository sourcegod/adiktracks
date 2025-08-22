# sounddevice_audio_driver.py
import sounddevice as sd
import numpy as np

class SoundDeviceAudioDriver:
    """
    Implémentation spécifique du pilote audio pour la bibliothèque SoundDevice.
    Cette classe gère les streams audio de bas niveau.
    """
    def __init__(self, sample_rate, block_size, num_output_channels, num_input_channels):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.num_output_channels = num_output_channels
        self.num_input_channels = num_input_channels
        self._stream_out = None
        self._stream_in = None
        self._stream_duplex = None
        
        # Vérification des périphériques audio par défaut au démarrage
        try:
            sd.check_output_settings(samplerate=self.sample_rate, channels=self.num_output_channels)
            sd.check_input_settings(samplerate=self.sample_rate, channels=self.num_input_channels)
            print(f"Pilote SoundDevice: Périphériques par défaut: Entrée='{sd.query_devices(kind='input')['name']}', Sortie='{sd.query_devices(kind='output')['name']}'")
        except sd.PortAudioError as e:
            print(f"Pilote SoundDevice: Avertissement: Problème avec les périphériques audio par défaut: {e}")
            print("Veuillez vérifier vos périphériques audio et leurs paramètres.")

    #----------------------------------------
    
    def start_output_stream(self, callback_func):
        """Démarre un stream de sortie sounddevice."""
        if self._stream_out and self._stream_out.active:
            print("Pilote SoundDevice: Stream de sortie déjà actif.")
            return

        try:
            self._stream_out = sd.OutputStream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                channels=self.num_output_channels,
                dtype='float32',
                callback=callback_func
            )
            self._stream_out.start()
        except Exception as e:
            print(f"Pilote SoundDevice: Erreur lors du démarrage du stream de sortie: {e}.")
            self._stream_out = None
            
    #----------------------------------------

    def stop_output_stream(self):
        """Arrête et ferme le stream de sortie."""
        if self._stream_out:
            self._stream_out.close()
            self._stream_out = None
    
    #----------------------------------------

    def start_input_stream(self, callback_func):
        """Démarre un stream d'entrée sounddevice."""
        if self._stream_in and self._stream_in.active:
            print("Pilote SoundDevice: Stream d'entrée déjà actif.")
            return

        try:
            self._stream_in = sd.InputStream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                channels=self.num_input_channels,
                dtype='float32',
                callback=callback_func
            )
            self._stream_in.start()
        except Exception as e:
            print(f"Pilote SoundDevice: Erreur lors du démarrage du stream d'entrée: {e}.")
            self._stream_in = None
            
    #----------------------------------------

    def stop_input_stream(self):
        """Arrête et ferme le stream d'entrée."""
        if self._stream_in:
            self._stream_in.close()
            self._stream_in = None

    #----------------------------------------
    
    def start_duplex_stream(self, callback_func):
        """
        Démarre un stream duplex sounddevice.
        """
        if (self._stream_duplex and self._stream_duplex.active) or (self._stream_out and self._stream_out.active) or (self._stream_in and self._stream_in.active):
            print("Pilote SoundDevice: Un stream est déjà actif. Impossible de démarrer un stream duplex.")
            return


        try:
            self._stream_duplex = sd.Stream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                channels=[self.num_input_channels, self.num_output_channels],
                dtype='float32',
                callback=callback_func
            )
            self._stream_duplex.start()
        except Exception as e:
            print(f"Pilote SoundDevice: Erreur lors du démarrage du stream duplex: {e}.")
            self._stream_duplex = None

    #----------------------------------------

    def stop_duplex_stream(self):
        """Arrête le stream duplex."""
        if self._stream_duplex:
            self._stream_duplex.close()
            self._stream_duplex = None
            print("Pilote SoundDevice: Stream duplex arrêté.")

    #----------------------------------------

