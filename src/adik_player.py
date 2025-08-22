#!/usr/bin/env python3
# adik_player.py
import numpy as np
import threading
import time

from adik_track import AdikTrack
from adik_sound import AdikSound
from adik_mixer import AdikMixer
from adik_wave_handler import AdikWaveHandler # Pour charger/sauvegarder sons
from adik_audio_engine import AdikAudioEngine 
from adik_metronome import AdikMetronome
from adik_track_edit import AdikTrackEdit # Import de la nouvelle classe
from adik_loop import AdikLoop # Import de la nouvelle classe
from adik_transport import AdikTransport

def beep():
    print("\a")

#----------------------------------------

class AdikPlayer:
    def __init__(self, sample_rate=44100, block_size=1024, num_output_channels=2, num_input_channels=1):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.num_output_channels = num_output_channels # Canaux de sortie du player/mixer
        self.num_input_channels = num_input_channels # NOUVEAU: Canaux d'entrée

        # Instanciez l'Engine et définissez son callback
        self.audio_engine = AdikAudioEngine(sample_rate, block_size, num_output_channels, num_input_channels)
        self._audio_callback = self._audio_output_callback
        # self.audio_engine.set_callback(self._audio_callback) # Le callback du player devient le callback de l'engine
        self.audio_engine.set_output_callback(self._audio_output_callback)
        self.audio_engine.set_input_callback(self._audio_input_callback)

        self.mixer = AdikMixer(self.sample_rate, self.num_output_channels)

        self.track_list = [] # Liste des objets AdikTrack
        self.selected_track_idx = -1 # Index de la piste sélectionnée
        self.track_edit = AdikTrackEdit(self) # Instanciation de la classe d'édition
        self.loop_manager = AdikLoop(self)
        self.transport = AdikTransport(self)

        self.current_playback_frame = 0 # Position globale du player en frames
        """
        self._playing = False
        self._recording = False # Retirer le commentaire pour que l'enregistrement soit fonctionnel
        self.recording_buffer = np.array([], dtype=np.float32) 
        self.recording_sound = None 
        self.recording_start_frame = 0 # La frame où l'enregistrement a commencé
        self.recording_end_frame = 0 # Initialiser la fin à la même position
        self.recording_mode = AdikTrack.RECORDING_MODE_REPLACE
        """


        # total_duration_seconds et current_time_seconds seront gérés comme des propriétés (voir plus bas)
        self.current_time_seconds_cached = 0.0
        self.total_duration_seconds_cached = 0.0 # Cache pour la durée totale
        self.total_duration_frames_cached = 0
        
        self._lock = threading.Lock() # Verrou pour protéger les accès concurrents

        # --- Variables du métronome ---
        self.metronome = AdikMetronome(sample_rate=sample_rate, num_channels=num_output_channels)
        self.metronome.update_tempo()  # Initialiser le tempo au démarrage
        self._left_locator =0 # In frames
        self._right_locator =0 # In frames

        print(f"AdikPlayer initialisé (SR: {self.sample_rate}, Block Size: {self.block_size}, Out Channels: {self.num_output_channels}, In Channels: {self.num_input_channels})")
    #----------------------------------------

    # --- Gestion des Pistes ---
    # Fonctions déléguées à AdikTrackEdit
    def select_track(self, track_idx):
        return self.track_edit.select_track(track_idx)

    #----------------------------------------

    def get_selected_track(self):
        return self.track_edit.get_selected_track()

    #----------------------------------------

    def add_track(self, name=None):
        return self.track_edit.add_track(name)

    #----------------------------------------

    def delete_track(self, track_idx):
        return self.track_edit.delete_track(track_idx)
        
    #----------------------------------------

    def remove_all_tracks(self):
        self.track_edit.remove_all_tracks()

    #----------------------------------------
    
    def delete_audio_from_track(self, track_index: int, start_frame: int, end_frame: int):
        self.track_edit.delete_audio_from_track(track_index, start_frame, end_frame)

    #----------------------------------------
    
    def erase_audio_from_track(self, track_index, start_frame, end_frame):
        self.track_edit.erase_audio_from_track(track_index, start_frame, end_frame)

    #----------------------------------------
        
    def has_solo_track(self) -> bool:
        return self.track_edit.has_solo_track()

    #----------------------------------------
        
    def bounce_to_track(self, start_frame=0, end_frame=-1):
        self.track_edit.bounce_to_track(start_frame, end_frame)

    #----------------------------------------
        
    def save_track(self, start_frame=0, end_frame=-1, filename=None):
        return self.track_edit.save_track(start_frame, end_frame, filename)

    #----------------------------------------

    def _update_total_duration_cache(self):
        """
        Met à jour la durée totale du projet en se basant sur les pistes existantes.
        """
        # with self._lock:
        max_duration_frames = 0
        for track in self.track_list:
            if track.audio_sound:
                track_end_frame = track.offset_frames + track.audio_sound.length_frames
                if track_end_frame > max_duration_frames:
                    max_duration_frames = track_end_frame
        
        # Mise à jour des deux propriétés
        self.total_duration_frames_cached = max_duration_frames
        self.total_duration_seconds_cached = max_duration_frames / self.sample_rate

    #----------------------------------------

    def _update_params(self):
        """
        Met à jour les paramètres importants du player.
        La gestion de la boucle a été déplacée vers AdikLoop.
        """
        self._update_total_duration_cache()
        self.loop_manager.update_params()

    #----------------------------------------
    
    # --- Transport (Play/Pause/Stop) ---
    # Fonctions déléguées à AdikTransport
    def is_playing(self):
        return self.transport.is_playing()

    #----------------------------------------

    def is_recording(self):
        return self.transport.is_recording()

    #----------------------------------------

    def play(self):
        self.transport.play()

    #----------------------------------------

    def pause(self):
        self.transport.pause()

    #----------------------------------------

    def stop(self):
        self.transport.stop()

    #----------------------------------------

    def start_recording(self):
        self.transport.start_recording()

    #----------------------------------------

    def stop_recording(self):
        self.transport.stop_recording()

    #----------------------------------------

    def set_recording_mode(self, mode: int):
        self.transport.set_recording_mode(mode)
 
    #----------------------------------------
   
    def toggle_recording_mode(self):
        self.transport.toggle_recording_mode()

    #----------------------------------------

    def save_recording(self, filename=None):
        return self.transport.save_recording(filename)

    #----------------------------------------

    # --- Fonctions de positionnement ---
    def _get_max_frames(self):
        """
        Calcule et retourne la durée maximale en frames parmi toutes les pistes chargées.
        """
        return int(self.total_duration_seconds * self.sample_rate)

    #----------------------------------------

    def set_position(self, frames):
        """
        Définit la position de lecture globale du player et de toutes les pistes.
        La position est clamper entre 0 et la durée maximale du projet.
        """
        with self._lock:
            max_frames = self._get_max_frames()
            
            new_position = max(0, min(max_frames, frames))
            
            if new_position == self.current_playback_frame:
                return

            self.current_playback_frame = new_position
            for track in self.track_list:
                track.set_playback_position(self.current_playback_frame) # Utilise la méthode correcte
            
            # Mise à jour de current_time_seconds car set_position peut être appelée en dehors du callback
            self.current_time_seconds_cached = self.current_playback_frame / self.sample_rate 
            print(f"Position de lecture définie à: {self.current_playback_frame} frames ({self.current_time_seconds:.2f}s)")

    #----------------------------------------

    def get_position(self):
        """
        Retourne la position de lecture actuelle du player en frames.
        """
        with self._lock:
            return self.current_playback_frame

    #----------------------------------------

    def forward(self, frames_to_skip=44100): 
        """Avance la position de lecture du player."""
        self.set_position(self.get_position() + frames_to_skip)

    #----------------------------------------

    def backward(self, frames_to_skip=44100): 
        """Recule la position de lecture du player."""
        self.set_position(self.get_position() - frames_to_skip)

    #----------------------------------------

    def goto_start(self):
        """Va au début du projet."""
        self.set_position(0)

    #----------------------------------------

    def goto_end(self):
        """Va à la fin du projet (fin de la piste la plus longue)."""
        self.set_position(self._get_max_frames())

    #----------------------------------------

    # --- Gestion du stream de audio_engine ---
    def _start_engine(self):
        """Démarre l'engine audio."""
        if not self._is_engine_running():
            self.audio_engine.start_output_stream()
            # self.audio_engine.start_duplex_stream()
            print("Moteur Audio Démarré")
            beep()

    #----------------------------------------

    def _stop_engine(self):
        """Arrête l'engine audio, en entrée et en sortie """
        if self._is_engine_running():
            # Arrêter tous les streams en cours
            self.audio_engine.stop_stream()
            # self.audio_engine.stop_duplex_stream()

    #----------------------------------------

    def _is_engine_running(self):
        """Retourne si le moteur audio en lecture seule est actif"""
        return self.audio_engine.is_running()

    #----------------------------------------

    # --- gestion de la boucle ---
    # Fonctions déléguées à AdikLoop
    def is_looping(self):
        return self.loop_manager.is_looping()
        
    #----------------------------------------

    def set_loop_points(self, start_frame, end_frame):
        return self.loop_manager.set_loop_points(start_frame, end_frame)
        
    #----------------------------------------

    def toggle_loop(self):
        return self.loop_manager.toggle_loop()
        
    #----------------------------------------


    # --- Gestion du métronome ---
    # Fonctions déléguées à AdikMetronome
    def set_bpm(self, bpm):
        """Définit le tempo en BPM et met à jour les frames_per_beat."""
        with self._lock:
            if bpm > 0:
                self.metronome.tempo_bpm = bpm
                self.metronome.update_tempo()
            else:
                print("Erreur: Le BPM doit être une valeur positive.")

    #----------------------------------------

    def get_bpm(self):
        """Retourne le tempo actuel en BPM."""
        return self.metronome.tempo_bpm

    #----------------------------------------

    def increase_bpm(self, step=1):
        """
        Augmente le tempo en BPM.
        """
        # La fonction set_bpm  du metronome est déjà sous verrou
        new_bpm = self.metronome.tempo_bpm + step
        if new_bpm >= 800:
            new_bpm = 800
        self.set_bpm(new_bpm)
        print(f"BPM augmenté à {self.metronome.tempo_bpm}")

    #----------------------------------------

    def decrease_bpm(self, step=1):
        """
        Diminue le tempo en BPM. La valeur ne peut pas être inférieure à 1.
        """
        # La fonction set_bpm  du metronome est déjà sous verrou
        new_bpm = self.metronome.tempo_bpm - step
        if new_bpm < 1:
            new_bpm = 1
        self.set_bpm(new_bpm)
        print(f"BPM diminué à {self.metronome.tempo_bpm}")

    #----------------------------------------

    def toggle_click(self):
        """
        Active ou désactive le métronome.
        Initialise la position du métronome et le compteur de battements.
        """
        with self._lock:
            self.metronome.toggle_click(False)
            
    #----------------------------------------

    # --- Gestion des Locateurs ---
    def get_left_locator(self):
        """Retourne la position du locateur gauche."""
        return self._left_locator

    #----------------------------------------
    
    def set_left_locator(self, frame_position):
        """
        Définit la position du locateur gauche, en s'assurant qu'elle est valide.
        """
        # S'assurer que la position est entre 0 et la durée totale
        validated_frame = max(0, min(frame_position, self.total_duration_frames_cached))
        
        # S'assurer que le locateur gauche ne dépasse pas le droit
        self._left_locator = validated_frame # min(validated_frame, self._right_locator)

    #----------------------------------------

    def get_right_locator(self):
        """Retourne la position du locateur droit."""
        return self._right_locator

    #----------------------------------------

    def set_right_locator(self, frame_position):
        """
        Définit la position du locateur droit, en s'assurant qu'elle est valide.
        """
        # S'assurer que la position est entre 0 et la durée totale
        validated_frame = max(0, min(frame_position, self.total_duration_frames_cached))
        
        self._right_locator = validated_frame # max(validated_frame, self._left_locator)

    #----------------------------------------


    # --- Gestion du Callback ---
    def _audio_input_callback(self, indata, frames, time_info, status):
        """
        Callback audio en enregistrement.
        Cette fonction est exécutée dans un thread séparé.
        """
        if status:
            print(f"Status du callback d'entrée: {status}", flush=True)
            beep()

        with self._lock:
            if self.transport._recording and indata is not None and indata.size > 0:
                self.transport.recording_buffer = np.append(self.transport.recording_buffer, indata.astype(np.float32).flatten())

    #----------------------------------------

    def _audio_output_callback(self, outdata, num_frames, time_info, status):
        """
        Callback audio en lecture seulement.
        Le callback audio principal, avec une gestion améliorée du métronome.
        """
        if status:
            print(f"Status du callback audio: {status}", flush=True)
            beep()
            
        with self._lock:
            # 1. Remplissage du buffer de sortie avec des zéros
            output_buffer = np.zeros(num_frames * self.num_output_channels, dtype=np.float32)

            # 2. Logique de déclenchement du métronome
            if self.metronome.is_clicking():
                current_beat_index = self.metronome.playback_frame // self.metronome.frames_per_beat
                next_beat_index = (self.metronome.playback_frame + num_frames) // self.metronome.frames_per_beat

                # Si le métronome vient d'être démarré et que la position est à zéro, on clique immédiatement.
                if self.metronome.playback_frame == 0 and not self.metronome.is_click_playing():
                    beep()
                    self.metronome.beat_count =0
                    self.metronome.play_click()
                 
                # Si, on détecte le passage au battement suivant
                if current_beat_index < next_beat_index:
                    if self.metronome.playback_frame > 0:
                        self.metronome.play_click()
                        self.metronome._increment_beat_count() # Incrémenter le compteur ici
                            
                # 3. Mixage du son du métronome dans le buffer de sortie
                self.metronome.mix_click_data(output_buffer, num_frames)
               
            # 4. Traitement de la lecture si le player est en mode PLAY
            # Mettre à jour la position du métronome même si le player est en pause
            if not self.transport._playing:
                if self.metronome.is_clicking():
                    self.metronome.playback_frame += num_frames
                    pass

            else: # self._playing 
                solo_active = any(track.is_solo() for track in self.track_list)

                for track in self.track_list:
                    should_mix_track = True
                    if solo_active and not track.is_solo():
                        should_mix_track = False
                    if track.is_muted():
                        should_mix_track = False
                    if track.is_armed() and self.transport._recording and self.transport.recording_mode == track.RECORDING_MODE_REPLACE:
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
                self.current_playback_frame += num_frames
                self.metronome.playback_frame = self.current_playback_frame
                self.current_time_seconds_cached = self.current_playback_frame / self.sample_rate

                # Gérer le bouclage
                if self.loop_manager.is_looping() and self.current_playback_frame >= self.loop_manager._loop_end_frame:
                    self.current_playback_frame = self.loop_manager._loop_start_frame
                    self.metronome.playback_frame = self.current_playback_frame
                    for track in self.track_list:
                        track.playback_position = self.current_playback_frame
                    print(f"Player: Boucle terminée, repositionnement à {self.current_playback_frame} frames.")
                
                # Gérer l'arrêt en fin de lecture si le bouclage n'est pas actif
                elif not self.loop_manager.is_looping():
                    all_tracks_finished = True
                    for track in self.track_list:
                        if track.audio_sound:
                            if self.current_playback_frame < (track.offset_frames + track.audio_sound.length_frames):
                                all_tracks_finished = False
                                break
                    if all_tracks_finished and not self.transport._recording:
                        print("Player: Toutes les pistes ont fini de jouer. Arrêt automatique.")
                        self.transport._playing = False
            
            outdata[:] = output_buffer.reshape((num_frames, self.num_output_channels))

    #----------------------------------------


    '''
    def _audio_duplex_callback(self, indata, outdata, num_frames, time_info, status):
        """
        Deprecated function, for backup
        Callback audio en duplex, avec gestion de la lecture et l'enregistrement
        Le callback audio principal, avec une gestion améliorée du métronome.
        """
        if status:
            print(f"Status du callback audio: {status}", flush=True)
            beep()
            
        with self._lock:
            # 1. Traitement de l'enregistrement
            if self._recording and indata is not None and indata.size > 0:
                self.recording_buffer = np.append(self.recording_buffer, indata.astype(np.float32).flatten())

            # 2. Remplissage du buffer de sortie avec des zéros
            output_buffer = np.zeros(num_frames * self.num_output_channels, dtype=np.float32)

            # 3. Logique de déclenchement du métronome
            if self.metronome.is_clicking():
                current_beat_index = self.metronome.playback_frame // self.metronome.frames_per_beat
                next_beat_index = (self.metronome.playback_frame + num_frames) // self.metronome.frames_per_beat

                # Si le métronome vient d'être démarré et que la position est à zéro, on clique immédiatement.
                if self.metronome.playback_frame == 0 and not self.metronome.is_click_playing():
                    beep()
                    self.metronome.beat_count =0
                    self.metronome.play_click()
                 
                # Si, on détecte le passage au battement suivant
                if current_beat_index < next_beat_index:
                    if self.metronome.playback_frame > 0:
                        self.metronome.play_click()
                        self.metronome._increment_beat_count() # Incrémenter le compteur ici
                            
                # 4. Mixage du son de clic dans le buffer de sortie
                self.metronome.mix_click_data(output_buffer, num_frames)
               
            # 5. Traitement de la lecture si le player est en mode PLAY
            # Mettre à jour la position du métronome même si le player est en pause
            if not self._playing:
                if self.metronome.is_clicking():
                    self.metronome.playback_frame += num_frames
                    pass

            else: # self._playing 
                solo_active = any(track.is_solo() for track in self.track_list)

                for track in self.track_list:
                    should_mix_track = True
                    if solo_active and not track.is_solo():
                        should_mix_track = False
                    if track.is_muted():
                        should_mix_track = False
                    if track.is_armed() and self._recording and track.recording_mode == track.RECORDING_MODE_REPLACE:
                        should_mix_track = False

                    if should_mix_track:
                        if track.audio_sound and track.audio_sound.audio_data.length_frames > 0:
                            try:
                                track.mix_sound_data(output_buffer, num_frames)
                            except Exception as e:
                                print(f"Erreur lors de l'appel de mix_sound_data pour la piste {track.name}: {e}")
                        else:
                            track.get_audio_block(num_frames)
                    else: # not should_mix_track
                        track.get_audio_block(num_frames)
                
                # Mettre à jour la position du player et du métronome uniquement en mode lecture
                self.current_playback_frame += num_frames
                self.metronome.playback_frame = self.current_playback_frame
                self.current_time_seconds_cached = self.current_playback_frame / self.sample_rate

                # Gérer le bouclage
                if self.is_looping() and self.current_playback_frame >= self._loop_end_frame:
                    self.current_playback_frame = self._loop_start_frame
                    self.metronome.playback_frame = self.current_playback_frame
                    for track in self.track_list:
                        track.playback_position = self.current_playback_frame
                    print(f"Player: Boucle terminée, repositionnement à {self.current_playback_frame} frames.")
                
                # Gérer l'arrêt en fin de lecture si le bouclage n'est pas actif
                elif not self.is_looping():
                    all_tracks_finished = True
                    for track in self.track_list:
                        if track.audio_sound:
                            if self.current_playback_frame < (track.offset_frames + track.audio_sound.length_frames):
                                all_tracks_finished = False
                                break
                    if all_tracks_finished and not self._recording:
                        print("Player: Toutes les pistes ont fini de jouer. Arrêt automatique.")
                        self._playing = False
            
            outdata[:] = output_buffer.reshape((num_frames, self.num_output_channels))

    #----------------------------------------
    '''

    # --- Propriétés pour l'affichage de la position et durée ---
    @property
    def current_time_seconds(self):
        """Retourne le temps de lecture actuel en secondes."""
        return self.current_time_seconds_cached

    #----------------------------------------

    @property
    def total_duration_frames(self):
        """Retourne la durée totale du projet en frames."""
        return self.total_duration_frames_cached

    #----------------------------------------
    
    @property
    def total_duration_seconds(self):
        """Retourne la durée totale du projet en secondes."""
        return self.total_duration_seconds_cached

    #----------------------------------------

#========================================

if __name__ == "__main__":
    # For testing
    app = AdikPlayer()
    # app.init_player()

    input("It's OK...")
    
#----------------------------------------
