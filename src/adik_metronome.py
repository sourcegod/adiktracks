# adik_metronome.py
import numpy as np
from adik_sound import AdikSound
import threading

class AdikMetronome:
    def __init__(self, sample_rate, num_channels):
        self.sample_rate = sample_rate
        self.num_channels = num_channels
        self.tempo_bpm = 120.0
        self.frames_per_beat = 0
        self.beat_count = 0
        self.is_clicking = False
        self.playback_frame = 0
        self.strong_beat_click_data = None
        self.weak_beat_click_data = None
        self.click_sound_position = 0
        self.is_click_playing = False
        self._lock = None  # Le verrou sera géré par AdikPlayer
        self.metronome_thread = None
        self.thread_stop_event = threading.Event()

        self._update_click_sound()
        self.update_tempo()

    #----------------------------------------

    def update_tempo(self, bpm=None):
        """Met à jour le tempo du métronome."""
        if bpm is not None:
            if bpm > 0:
                self.tempo_bpm = bpm
        
        frames_per_second = self.sample_rate
        seconds_per_beat = 60.0 / self.tempo_bpm
        self.frames_per_beat = int(seconds_per_beat * frames_per_second)
        print(f"Metronome: Tempo mis à jour à {self.tempo_bpm} BPM. ({self.frames_per_beat} frames/battement)")

    #----------------------------------------

    def _update_click_sound(self):
        """Génère les deux sons de clic du métronome."""
        click_duration_seconds = 0.050
        amplitude = 0.2
        
        self.strong_beat_click_data = AdikSound.sine_wave(
            freq=880,
            dur=click_duration_seconds,
            amp=amplitude,
            sample_rate=self.sample_rate,
            num_channels=self.num_channels
        )
        self.weak_beat_click_data = AdikSound.sine_wave(
            freq=440,
            dur=click_duration_seconds,
            amp=amplitude,
            sample_rate=self.sample_rate,
            num_channels=self.num_channels
        )

    #----------------------------------------

    def toggle_click(self, is_playing):
        """Active ou désactive le métronome."""
        self.is_clicking = not self.is_clicking
        if self.is_clicking:
            # Réinitialisation pour un départ sur un temps fort
            if is_playing:
                self.playback_frame = 0 # Sera synchronisé par AdikPlayer
            else:
                self.playback_frame = 0
            self.beat_count = 0
            print("Metronome: Activé.")
        else:
            print("Metronome: Désactivé.")

    #----------------------------------------

    def play_click(self):
        """Déclenche la lecture du son de clic."""
        self.click_sound_position = 0
        self.is_click_playing = True

    #----------------------------------------

    def mix_click_data(self, output_buffer, num_frames):
        """Mixe le son du métronome dans le buffer de sortie."""
        if not self.is_click_playing:
            return

        click_sound = self.strong_beat_click_data if self.beat_count == 0 else self.weak_beat_click_data
        
        if click_sound is None:
            return

        click_sound_length_frames = click_sound.get_length_frames()
        remaining_frames_in_click = click_sound_length_frames - self.click_sound_position
        frames_to_mix = min(num_frames, remaining_frames_in_click)

        if frames_to_mix > 0:
            start_index = self.click_sound_position * self.num_channels
            end_index = start_index + frames_to_mix * self.num_channels
            click_slice = click_sound.audio_data[start_index:end_index]
            
            if click_slice.size == frames_to_mix * self.num_channels:
                output_buffer[:click_slice.size] += click_slice

            self.click_sound_position += frames_to_mix

        if self.click_sound_position >= click_sound_length_frames:
            self.is_click_playing = False
            self.click_sound_position = 0

    #----------------------------------------

    def _increment_beat_count(self):
        """
        Incrémente le compteur de battements et gère le bouclage.
        """
        self.beat_count = (self.beat_count + 1) % 4

    #----------------------------------------

    def _metronome_runner(self):
        # deprecated function
        """
        Le thread qui exécute le métronome.
        """
        print("Metronome: Thread démarré.")
        self.beat_count = 0
        while not self.thread_stop_event.is_set():
            # Jouer le clic du métronome
            self.play_click()
            self.beat_count += 1
            print(f"Metronome: Clic! (Beat {self.beat_count})")
            
            # Attendre le temps du prochain battement
            # On utilise le thread_stop_event.wait() qui peut être interrompu.
            time_to_wait = 60.0 / self.tempo_bpm
            self.thread_stop_event.wait(time_to_wait)
        print("Metronome: Thread arrêté.")

    #----------------------------------------

    def toggle_click_with_threading(self):
        # Deprecated function
        """Démarre ou arrête le métronome indépendant du player."""
        with self._lock:
            if not self.is_clicking:
                print("Metronome: Démarrage...")
                self.is_clicking = True
                self.thread_stop_event.clear()
                self.metronome_thread = threading.Thread(target=self._metronome_runner)
                self.metronome_thread.start()
            else:
                print("Metronome: Arrêt...")
                self.is_clicking = False
                self.thread_stop_event.set()
                if self.metronome_thread and self.metronome_thread.is_alive():
                    self.metronome_thread.join()
                self.metronome_thread = None

    #----------------------------------------
