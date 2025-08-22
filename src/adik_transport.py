#!/usr/bin/env python3
# adik_transport.py
"""
    File: adik_transport.py:
    Transport management for the player
    Date: Fri, 22/08/2025
    Author: Coolbrother
"""
import threading
import numpy as np
import time
from adik_sound import AdikSound
from adik_wave_handler import AdikWaveHandler
from adik_track import AdikTrack


class AdikTransport:
    """
    Gère les fonctions de transport (lecture, enregistrement, arrêt) pour le lecteur.
    """
    def __init__(self, player):
        self.player = player
        self._lock = threading.Lock()
        self._playing = False
        self._recording = False
        self.recording_buffer = np.array([], dtype=np.float32)
        self.recording_sound = None
        self.recording_mode = AdikTrack.RECORDING_MODE_REPLACE
        self.recording_start_frame = 0
        self.recording_end_frame = 0

    #----------------------------------------

    def is_playing(self):
        """
        Retourne l'état de lecture.
        """
        return self._playing

    #----------------------------------------

    def is_recording(self):
        """
        Retourne l'état d'enregistrement.
        """
        return self._recording

    #----------------------------------------

    def play(self):
        """
        Démarre la lecture.
        """
        if self._recording:
            self.stop_recording()
            return

        if self._playing:
            print("Déjà en lecture.")
            return

        print("Démarrage de la lecture...")
        with self._lock:
            self._playing = True
            self.player._start_engine()

    #----------------------------------------

    def pause(self):
        """
        Met le player en pause.
        """
        if not self._playing and not self._recording:
            print("Pas en lecture ou en enregistrement.")
            return

        print("Mise en pause.")
        with self._lock:
            self._playing = False
            if self._recording:
                self._finish_recording()

    #----------------------------------------

    def stop(self):
        """
        Arrête la lecture et l'enregistrement, et réinitialise la position.
        """
        if not self._playing and not self._recording and not self.player._is_engine_running():
            print("Déjà arrêté.")
            return

        print("Arrêt du player.")

        with self._lock:
            self._playing = False
            if self._recording:
                self._finish_recording()
            
            self.player.current_playback_frame = 0
            for track in self.player.track_list:
                track.reset_playback_position()
            
        if not self._playing and not self._recording and self.player._is_engine_running():
            self.player._stop_engine()

    #----------------------------------------

    def start_recording(self):
        """
        Démarre l'enregistrement audio.
        """
        if self._recording:
            print("Player: Déjà en enregistrement. Appuyez sur 'R' de nouveau pour arrêter.")
            return

        selected_track = self.player.get_selected_track()
        if not selected_track or not selected_track.is_armed():
            print("Player: Aucune piste armée pour l'enregistrement.")
            return

        if not self.player.audio_engine.is_input_running():
            self.player.audio_engine.start_input_stream()
            
        with self._lock:
            self._recording = True
            self.recording_buffer = np.array([], dtype=np.float32)
            self.recording_sound = None
            
            self.recording_start_frame = self.player.current_playback_frame
            self.recording_end_frame = self.player.current_playback_frame

            self._playing = True
            print(f"Player: Enregistrement démarré à la frame {self.recording_start_frame}.")

    #----------------------------------------

    def stop_recording(self):
        """
        Arrête l'enregistrement audio.
        """
        if not self._recording:
            print("Player: Pas en enregistrement.")
            return
        
        print("Player: Arrêt de l'enregistrement.")
        with self._lock:
            self._finish_recording()
        
        if self.player.audio_engine.is_input_running():
            self.player.audio_engine.stop_input_stream()

    #----------------------------------------

    def _finish_recording(self):
        """
        Finalise l'enregistrement et traite le buffer.
        """
        if not self._recording:
            print("Player: Aucune session d'enregistrement active à finaliser (interne).")
            return

        print("Player: Finalisation de l'enregistrement...")
        self._recording = False

        if self.recording_buffer.size > 0:
            self.recording_end_frame = self.player.current_playback_frame
            recorded_sound_data = self.recording_buffer
            
            selected_track = self.player.get_selected_track()

            if selected_track:
                selected_track.arrange_take(
                    new_take_audio_data=recorded_sound_data,
                    take_start_frame=self.recording_start_frame,
                    take_end_frame=self.recording_end_frame,
                    recording_mode=self.recording_mode,
                    new_take_channels=self.player.num_input_channels
                )
                print(f"Player: Enregistrement arrangé sur la piste '{selected_track.name}'.")
                selected_track.set_playback_position(self.player.current_playback_frame)
            else:
                new_track_name = f"Piste Enregistrée {len(self.player.track_list) + 1}"
                new_track = self.player.add_track(new_track_name)
                
                take_length_frames = recorded_sound_data.size // self.player.num_input_channels
                converted_data = AdikSound.convert_channels(recorded_sound_data, self.player.num_input_channels, self.player.num_output_channels, take_length_frames)

                new_sound = AdikSound(
                    name=f"adik_rec_{time.strftime('%H%M%S')}",
                    audio_data=converted_data,
                    sample_rate=self.player.sample_rate,
                    num_channels=self.player.num_output_channels
                )
                new_track.set_audio_sound(new_sound, offset_frames=self.recording_start_frame)
                print(f"Player: Enregistrement ajouté à une nouvelle piste '{new_track.name}' à la frame {self.recording_start_frame}.")
                new_track.set_playback_position(self.player.current_playback_frame)
            
            self.player._update_params()
            self.recording_buffer = np.array([], dtype=np.float32)
        else:
            print("Player: Le buffer d'enregistrement est vide. Rien à finaliser.")
        
        print("Player: Enregistrement finalisé.")

    #----------------------------------------

    def set_recording_mode(self, mode: int):
        """
        Définit le mode d'enregistrement.
        """
        if mode in [AdikTrack.RECORDING_MODE_REPLACE, AdikTrack.RECORDING_MODE_MIX]:
            self.recording_mode = mode
            mode_name = "Remplacement" if mode == AdikTrack.RECORDING_MODE_REPLACE else "Mixage"
            print(f"Player: Mode d'enregistrement changé en '{mode_name}'.")
        else:
            print(f"Erreur: Mode d'enregistrement '{mode}' invalide.")

    #----------------------------------------

    def toggle_recording_mode(self):
        """
        Bascule entre les modes d'enregistrement REPLACE et MIX.
        """
        if self.recording_mode == AdikTrack.RECORDING_MODE_REPLACE:
            self.set_recording_mode(AdikTrack.RECORDING_MODE_MIX)
        else:
            self.set_recording_mode(AdikTrack.RECORDING_MODE_REPLACE)

    #----------------------------------------

    def save_recording(self, filename=None):
        """
        Sauvegarde le dernier enregistrement finalisé dans un fichier WAV.
        """
        if self._recording:
            print("Player: L'enregistrement est toujours actif. Veuillez l'arrêter d'abord pour le sauvegarder.")
            return False

        sound_to_save = self.recording_sound
        if sound_to_save and sound_to_save.length_frames > 0:
            if filename is None:
                filename = f"/tmp/{sound_to_save.name.replace(' ', '_').replace(':', '')}.wav"

            if AdikWaveHandler.save_wav(filename, sound_to_save):
                print(f"Player: Enregistrement sauvegardé dans '{filename}'.")
                return True
            else:
                print(f"Player: Échec de la sauvegarde de l'enregistrement dans '{filename}'.")
                return False
        else:
            print("Player: Aucun enregistrement finalisé ou le buffer est vide. Rien à sauvegarder.")
            return False

    #----------------------------------------

#========================================

if __name__ == "__main__":
    # For testing
    app = AdikTransport(None)

    input("It's OK...")
    
#----------------------------------------
