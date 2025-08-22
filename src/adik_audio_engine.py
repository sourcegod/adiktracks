# adik_audio_engine.py
"""
    File: adik_audio_engine.py
    Audio Sound Card Driver manager
    Date: Fri, 22/08/2025
    Author: Coolbrother

"""

from sounddevice_audio_driver import SoundDeviceAudioDriver

class AdikAudioEngine:
    """
    Moteur audio de l'application. Cette classe agit comme une façade,
    masquant les détails d'implémentation de l'API audio (comme sounddevice).
    Elle utilise un "pilote" pour communiquer avec le matériel audio.
    """
    def __init__(self, sample_rate=44100, block_size=1024, num_output_channels=2, num_input_channels=1):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.num_output_channels = num_output_channels
        self.num_input_channels = num_input_channels

        # L'instance du pilote audio, qui est responsable de la communication
        # avec le matériel (ici, sounddevice)
        self._audio_driver = SoundDeviceAudioDriver(
            sample_rate,
            block_size,
            num_output_channels,
            num_input_channels
        )

        # Les callbacks fournis par le player pour la lecture et l'enregistrement
        self._output_callback_function = None
        self._input_callback_function = None
        self._duplex_callback_function = None
        
        # Statut du moteur
        self._is_running_output = False
        self._is_running_input = False

        print(f"AdikAudioEngine initialisé (SR: {self.sample_rate}, Block Size: {self.block_size}, Out Channels: {self.num_output_channels})")

    #----------------------------------------
    
    def set_output_callback(self, callback_func):
        """Définit le callback pour la lecture."""
        if callable(callback_func):
            self._output_callback_function = callback_func
        else:
            raise ValueError("Le callback fourni n'est pas une fonction callable.")

    #----------------------------------------

    def set_input_callback(self, callback_func):
        """Définit le callback pour l'enregistrement."""
        if callable(callback_func):
            self._input_callback_function = callback_func
        else:
            raise ValueError("Le callback fourni n'est pas une fonction callable.")

    #----------------------------------------
    def set_duplex_callback(self, callback_func):
        """Définit le callback pour le duplex (la lecture et l'enregistrement) """
        if callable(callback_func):
            self._duplex_callback_function = callback_func
        else:
            raise ValueError("Le callback fourni n'est pas une fonction callable.")

    #----------------------------------------


    def start_output_stream(self):
        """Démarre le stream de sortie via le pilote."""
        if self._output_callback_function is None:
            print("Engine: Aucun callback de sortie défini. Impossible de démarrer le stream.")
            return

        self._audio_driver.start_output_stream(self._output_callback_function)
        self._is_running_output = True
        print("Engine: Stream de sortie démarré.")

    #----------------------------------------

    def stop_output_stream(self):
        """Arrête le stream de sortie via le pilote."""
        self._audio_driver.stop_output_stream()
        self._is_running_output = False
        print("Engine: Stream de sortie arrêté.")

    #----------------------------------------

    def start_input_stream(self):
        """Démarre le stream d'entrée via le pilote."""
        if self._input_callback_function is None:
            print("Engine: Aucun callback d'entrée défini. Impossible de démarrer le stream.")
            return

        self._audio_driver.start_input_stream(self._input_callback_function)
        self._is_running_input = True
        print("Engine: Stream d'entrée démarré.")

    #----------------------------------------

    def stop_input_stream(self):
        """Arrête le stream d'entrée via le pilote."""
        self._audio_driver.stop_input_stream()
        self._is_running_input = False
        print("Engine: Stream d'entrée arrêté.")

    #----------------------------------------

    def start_duplex_stream(self):
        """Démarre un stream duplex (entrée et sortie) via le pilote."""
        if self._duplex_callback_function is None: 
            print("Engine: Le callback (Duplex) doit être défini pour un stream duplex.")
            return
         
        # Le pilote SoundDeviceAudioDriver gère un seul stream pour le duplex
        self._audio_driver.start_duplex_stream(self._duplex_callback_function)
        self._is_running_output = True
        print("Engine: Stream duplex démarré.")
        
    #----------------------------------------
    
    def stop_duplex_stream(self):
        """Arrête le stream duplex via le pilote."""
        self._audio_driver.stop_duplex_stream()
        self._is_running_output = False
        print("Engine: Stream duplex arrêté.")

    #----------------------------------------

    def is_running(self):
        """Vérifie si un stream de sortie est actif."""
        return self._is_running_output

    #----------------------------------------
    
    def is_input_running(self):
        """Vérifie si un stream d'entrée est actif."""
        return self._is_running_input

    #----------------------------------------

    def stop_stream(self):
        """Arrête tous les streams actifs."""
        self.stop_output_stream()
        self.stop_input_stream()
        print("Engine: Tous les streams audio sont arrêtés.")

    #----------------------------------------

#========================================

if __name__ == "__main__":
    # For testing
    app = AdikAudioEngine()
    # app.init_player()

    input("It's OK...")
    
#----------------------------------------
