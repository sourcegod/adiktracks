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

        self.mixer = AdikMixer(self.sample_rate, self.num_output_channels)

        self.track_list = [] # Liste des objets AdikTrack
        self.selected_track_idx = -1 # Index de la piste sélectionnée
        self.track_edit = AdikTrackEdit(self) # Instanciation de la classe d'édition
        self.loop_manager = AdikLoop(self)
        self.transport = AdikTransport(self)
        # --- Variables du métronome ---
        self.metronome = AdikMetronome(sample_rate=sample_rate, num_channels=num_output_channels)
        # Instanciez l'Engine et utiliser ses fonctions de Callback internes
        # Doit être instancié après le Transport et le Metronome car son constructeur fait appel à ces instances.
        self.audio_engine = AdikAudioEngine(self, sample_rate, block_size, num_output_channels, num_input_channels)

        self.current_playback_frame = 0 # Position globale du player en frames
        # total_duration_seconds et current_time_seconds seront gérés comme des propriétés (voir plus bas)
        self.current_time_seconds_cached = 0.0
        self.total_duration_seconds_cached = 0.0 # Cache pour la durée totale
        self.total_duration_frames_cached = 0
        
        self._lock = threading.Lock() # Verrou pour protéger les accès concurrents

        self.metronome.update_tempo()  # Initialiser le tempo au démarrage
        self._left_locator =0 # In frames
        self._right_locator =0 # In frames
        self.time_signature = (4, 4) # (nombre de battements par mesure, valeur de la note par battement)
        
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

    # --- Gestion de positionnement par mesures ---
    def frame_to_bar(self, frame):
        """
        Convertit une position de trame en mesure, battement, et tick.
        Le tick est le reste des trames.
        Retourne un tuple: (bar, beat, tick)
        """
        beats_per_bar = self.time_signature[0]
        frames_per_beat = self.metronome.frames_per_beat
        if frames_per_beat == 0:
            return 0, 0, 0
        
        frames_per_bar = beats_per_bar * frames_per_beat
        
        if frames_per_bar == 0:
            # Évite une division par zéro si frames_per_bar est 0
            return 0, 0, 0

        bar = frame // frames_per_bar
        remaining_frames_in_bar = frame % frames_per_bar
        
        beat = remaining_frames_in_bar // frames_per_beat
        tick = remaining_frames_in_bar % frames_per_beat
        
        return bar, beat, tick

    #----------------------------------------

    def bar_to_frame(self, bar):
        """
        Convertit un numéro de mesure en position de trame.
        """
        beats_per_bar = self.time_signature[0]
        frames_per_beat = self.metronome.frames_per_beat
        frames_per_bar = beats_per_bar * frames_per_beat
        return int(bar * frames_per_bar)

    #----------------------------------------

    def get_bar(self):
        """
        Retourne la mesure (bar) actuelle en fonction de la position de lecture.
        """
        beats_per_bar = self.time_signature[0]
        frames_per_beat = self.metronome.frames_per_beat
        if frames_per_beat == 0:
            return 0
        frames_per_bar = beats_per_bar * frames_per_beat
        return int(self.current_playback_frame // frames_per_bar)

    #----------------------------------------

    def set_bar(self, num_bars):
        """
        Définit la position de lecture sur une mesure spécifique.
        """
        target_frame = self.bar_to_frame(num_bars)
        self.set_position(target_frame)
        print(f"Position définie à la mesure: {num_bars}")

    #----------------------------------------

    def prev_bar(self):
        """
        Déplace la position de lecture à la mesure précédente.
        """
        current_bar = self.get_bar()
        if current_bar > 0:
            self.set_bar(current_bar - 1)
        else:
            self.goto_start()
    
    #----------------------------------------

    def next_bar(self):
        """
        Déplace la position de lecture à la mesure suivante.
        """
        current_bar = self.get_bar()
        self.set_bar(current_bar + 1)

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
