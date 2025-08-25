# adik_audio_engine.py
"""
    File: adik_audio_engine.py
    Audio Sound Card Driver manager
    Date: Fri, 22/08/2025
    Author: Coolbrother

"""
import numpy as np
import threading

from sounddevice_audio_driver import SoundDeviceAudioDriver
def beep():
    print("\a")

#----------------------------------------


class AdikAudioEngine:
    """
    Moteur audio de l'application. Cette classe agit comme une façade,
    masquant les détails d'implémentation de l'API audio (comme sounddevice).
    Elle utilise un "pilote" pour communiquer avec le matériel audio.
    """
    def __init__(self, player_instance, sample_rate=44100, block_size=1024, num_output_channels=2, num_input_channels=1):
        """
        Initialise le moteur audio avec les paramètres de stream.
        Une référence à l'instance de la classe Player est nécessaire
        pour que les callbacks puissent accéder à ses données.
        """
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.num_output_channels = num_output_channels
        self.num_input_channels = num_input_channels

        if player_instance is not None:
            self._player = player_instance
            self._metronome = self._player.metronome
            self._transport = self._player.transport
            self._loop = self._player.loop_manager
        else:
            self._player = None
            self._metronome = None
            self._transport = None
            self._loop = None
        self._lock = threading.Lock()

        # L'instance du pilote audio, qui est responsable de la communication
        # avec le matériel (ici, sounddevice)
        self._audio_driver = SoundDeviceAudioDriver(
            sample_rate,
            block_size,
            num_output_channels,
            num_input_channels
        )

       
        # Statut du moteur
        self._is_running_output = False
        self._is_running_input = False
        self._is_running_duplex = False

        print(f"AdikAudioEngine initialisé (SR: {self.sample_rate}, Block Size: {self.block_size}, Out Channels: {self.num_output_channels})")

    #----------------------------------------
    
    def start_output_stream(self):
        """Démarre le stream de sortie via le pilote."""
        
        """
        if self._output_callback_function is None:
            print("Engine: Aucun callback de sortie défini. Impossible de démarrer le stream.")
            return
        self._audio_driver.start_output_stream(self._output_callback_function)
        """

        self._audio_driver.start_output_stream(self._audio_output_callback)
        self._is_running_output = True
        self._is_running_input = False  # S'assurer que les autres streams sont à False
        self._is_running_duplex = False

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
        
        """
        if self._input_callback_function is None:
            print("Engine: Aucun callback d'entrée défini. Impossible de démarrer le stream.")
            return
        self._audio_driver.start_input_stream(self._input_callback_function)
        """

        self._audio_driver.start_input_stream(self._audio_input_callback)
        self._is_running_input = True
        # On arrête pas le Stream Output car on peut démarrer un stream Input avec un Stream Output
        # S'assurer que le stream duplex est à False
        self._is_running_duplex = False

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
        
        """
        if self._duplex_callback_function is None: 
            print("Engine: Le callback (Duplex) doit être défini pour un stream duplex.")
            return
         
        self._audio_driver.start_duplex_stream(self._duplex_callback_function)
        """

        # Le pilote SoundDeviceAudioDriver gère un seul stream pour le duplex
        self._audio_driver.start_duplex_stream(self._audio_duplex_callback)
        self._is_running_duplex = True
        # S'assurer que les streams duplex sont à False
        self._is_running_output = False
        self._is_running_input = False
        print("Engine: Stream duplex démarré.")
        
    #----------------------------------------
    
    def stop_duplex_stream(self):
        """Arrête le stream duplex via le pilote."""
        self._audio_driver.stop_duplex_stream()
        self._is_running_duplex = False
        print("Engine: Stream duplex arrêté.")

    #----------------------------------------

    def is_running(self):
        """Vérifie si un stream de sortie est actif (sortie ou duplex)."""
        return self._is_running_output or self._is_running_duplex

    #----------------------------------------
    
    def is_input_running(self):
        """Vérifie si un stream d'entrée est actif (entrée ou duplex)."""
        return self._is_running_input or self._is_running_duplex

    #----------------------------------------

    def stop_stream(self):
        """Arrête tous les streams actifs."""
        self.stop_output_stream()
        self.stop_input_stream()
        self.stop_duplex_stream()

        print("Engine: Tous les streams audio sont arrêtés.")

    #----------------------------------------

    #----------------------------------------
    # Les fonctions de callback audio déplacées depuis AdikPlayer
    #----------------------------------------

    # --- Gestion des fonctions Callbacks ---
    def _audio_input_callback(self, indata, frames, time_info, status):
        """
        Callback audio pour l'enregistrement (stream d'entrée).
        Cette fonction est exécutée dans un thread séparé.
        """
        # Note: Cette fonction sera utilisée pour un stream d'entrée pur.
        # Pour le duplex, on utilise _audio_duplex_callback.
        if status:
            print(f"Status du callback d'entrée: {status}", flush=True)
            beep()
            
        with self._lock:
            # On vérifie si le player est en train d'enregistrer.
            if self._transport._recording and indata is not None and indata.size > 0:
                # Ajoute les données d'entrée au buffer d'enregistrement du transport.
                self._transport.recording_buffer = np.append(
                    self._transport.recording_buffer, 
                    indata.astype(np.float32).flatten()
                )

    #----------------------------------------
    
    def _audio_output_callback(self, outdata, num_frames, time_info, status):
        """
        Callback audio pour la lecture (stream de sortie).
        Le callback audio principal, avec une gestion améliorée du métronome.
        """
        # Note: Cette fonction sera utilisée pour un stream de sortie pur.
        # Pour le duplex, on utilise _audio_duplex_callback.
        if status:
            print(f"Status du callback audio: {status}", flush=True)
            beep()
            
        with self._lock:
            # 1. Remplissage du buffer de sortie avec des zéros
            output_buffer = np.zeros(num_frames * self.num_output_channels, dtype=np.float32)

            # 2. Logique de déclenchement du métronome
            if self._metronome.is_clicking():
                current_beat_index = self._metronome.playback_frame // self._metronome.frames_per_beat
                next_beat_index = (self._metronome.playback_frame + num_frames) // self._metronome.frames_per_beat

                # Si le métronome vient d'être démarré et que la position est à zéro, on clique immédiatement.
                if self._metronome.playback_frame == 0 and not self._metronome.is_click_playing():
                    beep()
                    self._metronome.beat_count = 0
                    self._metronome.play_click()
                
                # Si, on détecte le passage au battement suivant
                if current_beat_index < next_beat_index:
                    if self._metronome.playback_frame > 0:
                        self._metronome.play_click()
                        self._metronome._increment_beat_count() # Incrémenter le compteur ici
                        
                # 3. Mixage du son du métronome dans le buffer de sortie
                self._metronome.mix_click_data(output_buffer, num_frames)
                
            # 4. Traitement de la lecture si le player est en mode PLAY
            # Mettre à jour la position du métronome même si le player est en pause
            if not self._transport._playing:
                if self._metronome.is_clicking():
                    self._metronome.playback_frame += num_frames
                    pass
            else: # self._playing
                solo_active = any(track.is_solo() for track in self._player.track_list)

                for track in self._player.track_list:
                    should_mix_track = True
                    if solo_active and not track.is_solo():
                        should_mix_track = False
                    if track.is_muted():
                        should_mix_track = False
                    if track.is_armed() and self._transport._recording and self._transport.recording_mode == track.RECORDING_MODE_REPLACE:
                        should_mix_track = False

                    if should_mix_track:
                        if track.audio_sound and track.audio_sound.length_frames > 0:
                            try:
                                track.mix_sound_data(output_buffer, num_frames)
                            except Exception as e:
                                print(f"Erreur lors de l'appel de mix_sound_data pour la piste {track.name}: {e}")
                        else:
                            track.get_audio_block(num_frames)
                    else: # not should_mix_track
                        track.get_audio_block(num_frames)
                
                # Mettre à jour la position du player et du métronome uniquement en mode lecture
                self._player.current_playback_frame += num_frames
                self._metronome.playback_frame = self._player.current_playback_frame
                self._player.current_time_seconds_cached = self._player.current_playback_frame / self.sample_rate

                # Gérer le bouclage
                if self._loop.is_looping() and self._player.current_playback_frame >= self._loop._loop_end_frame:
                    self._player.current_playback_frame = self._loop._loop_start_frame
                    self._metronome.playback_frame = self._player.current_playback_frame
                    for track in self._player.track_list:
                        track.playback_position = self._player.current_playback_frame
                    print(f"Player: Boucle terminée, repositionnement à {self._player.current_playback_frame} frames.")
                
                # Gérer l'arrêt en fin de lecture si le bouclage n'est pas actif
                elif not self._loop.is_looping():
                    all_tracks_finished = True
                    for track in self._player.track_list:
                        if track.audio_sound:
                            if self._player.current_playback_frame < (track.offset_frames + track.audio_sound.length_frames):
                                all_tracks_finished = False
                                break
                    if all_tracks_finished and not self._transport._recording:
                        print("Player: Toutes les pistes ont fini de jouer. Arrêt automatique.")
                        self._transport._playing = False
            
            # Copie le buffer de sortie vers le buffer sounddevice
            outdata[:] = output_buffer.reshape((num_frames, self.num_output_channels))

    #----------------------------------------

    def _audio_duplex_callback(self, indata, outdata, num_frames, time_info, status):
        """
        Callback audio unique pour le stream duplex.
        Combine la logique des callbacks d'entrée et de sortie.
        """
        if status:
            print(f"Status du callback duplex: {status}", flush=True)
            beep()

        # Logique d'entrée (recording)
        # Identique à _audio_input_callback
        with self._lock:
            # 1. Remplissage du buffer de d'entrée
            if self._transport._recording and indata is not None and indata.size > 0:
                self._transport.recording_buffer = np.append(
                    self._transport.recording_buffer, 
                    indata.astype(np.float32).flatten()
                )

            # Logique de sortie (playback + metronome)
            # Identique à _audio_output_callback
            # 2. Remplissage du buffer de sortie avec des zéros
            output_buffer = np.zeros(num_frames * self.num_output_channels, dtype=np.float32)

            # 3. Logique de déclenchement du métronome
            if self._metronome.is_clicking():
                current_beat_index = self._metronome.playback_frame // self._metronome.frames_per_beat
                next_beat_index = (self._metronome.playback_frame + num_frames) // self._metronome.frames_per_beat

                # Si le métronome vient d'être démarré et que la position est à zéro, on clique immédiatement.
                if self._metronome.playback_frame == 0 and not self._metronome.is_click_playing():
                    beep()
                    self._metronome.beat_count = 0
                    self._metronome.play_click()
                
                # Si, on détecte le passage au battement suivant
                if current_beat_index < next_beat_index:
                    if self._metronome.playback_frame > 0:
                        self._metronome.play_click()
                        self._metronome._increment_beat_count()
                        
                # 4. Mixage du son du métronome dans le buffer de sortie
                self._metronome.mix_click_data(output_buffer, num_frames)
            
            # 5. Traitement de la lecture si le player est en mode PLAY
            if not self._transport._playing:
                if self._metronome.is_clicking():
                    self._metronome.playback_frame += num_frames
                    pass
            else: # self._playing
                solo_active = any(track.is_solo() for track in self._player.track_list)

                for track in self._player.track_list:
                    should_mix_track = True
                    if solo_active and not track.is_solo():
                        should_mix_track = False
                    if track.is_muted():
                        should_mix_track = False
                    if track.is_armed() and self._transport._recording and self._transport.recording_mode == track.RECORDING_MODE_REPLACE:
                        should_mix_track = False

                    if should_mix_track:
                        if track.audio_sound and track.audio_sound.length_frames > 0:
                            try:
                                track.mix_sound_data(output_buffer, num_frames)
                            except Exception as e:
                                print(f"Erreur lors de l'appel de mix_sound_data pour la piste {track.name}: {e}")
                        else:
                            track.get_audio_block(num_frames)
                    else:
                        track.get_audio_block(num_frames)
                
                self._player.current_playback_frame += num_frames
                self._metronome.playback_frame = self._player.current_playback_frame
                self._player.current_time_seconds_cached = self._player.current_playback_frame / self.sample_rate

                if self._loop.is_looping() and self._player.current_playback_frame >= self._loop._loop_end_frame:
                    self._player.current_playback_frame = self._loop._loop_start_frame
                    self._metronome.playback_frame = self._metronome._loop_start_frame
                    for track in self._player.track_list:
                        track.playback_position = self._player.current_playback_frame
                    print(f"Player: Boucle terminée, repositionnement à {self._player.current_playback_frame} frames.")
                
                elif not self._loop.is_looping():
                    all_tracks_finished = True
                    for track in self._player.track_list:
                        if track.audio_sound:
                            if self._player.current_playback_frame < (track.offset_frames + track.audio_sound.length_frames):
                                all_tracks_finished = False
                                break
                    if all_tracks_finished and not self._transport._recording:
                        print("Player: Toutes les pistes ont fini de jouer. Arrêt automatique.")
                        self._transport._playing = False
            
            outdata[:] = output_buffer.reshape((num_frames, self.num_output_channels))

    #----------------------------------------

#========================================

if __name__ == "__main__":
    # For testing
    # app = AdikAudioEngine()
    app = AdikAudioEngine(None)

    input("It's OK...")
    
#----------------------------------------
