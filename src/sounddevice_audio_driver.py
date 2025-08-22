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

        if self._stream_in and self._stream_in.active:
            print("Pilote SoundDevice: Un stream d'entrée est déjà actif. Le stream de sortie ne peut pas être démarré.")
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

        if self._stream_out and self._stream_out.active:
            print("Pilote SoundDevice: Un stream de sortie est déjà actif. Le stream d'entrée ne peut pas être démarré.")
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
    
    def start_duplex_stream(self, output_callback, input_callback):
        """Démarre un stream duplex sounddevice."""
        if (self._stream_out and self._stream_out.active) or (self._stream_in and self._stream_in.active):
            print("Pilote SoundDevice: Un stream est déjà actif. Impossible de démarrer un stream duplex.")
            return
        
        # NOTE: sounddevice.Stream est capable de gérer le duplex
        # Nous allons créer un seul stream pour l'entrée et la sortie.
        # Pour cela, il nous faut un seul callback qui gère les deux.
        # C'est la raison pour laquelle cette méthode est un peu plus complexe.
        # Pour le moment, nous allons simplement utiliser un stream de sortie
        # ou d'entrée, mais pas les deux en même temps.

        # Correction: Un stream duplex est possible si le callback est unique
        # gérant les données d'entrée ET de sortie.
        print("Pilote SoundDevice: Démarrage d'un stream duplex non pris en charge pour le moment.")
        print("Veuillez utiliser un stream de sortie ou d'entrée séparé.")

    #----------------------------------------
    
    def stop_duplex_stream(self):
        """Arrête le stream duplex (non implémenté)."""
        print("Pilote SoundDevice: Arrêt d'un stream duplex non pris en charge pour le moment.")

    #----------------------------------------

