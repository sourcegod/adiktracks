# adik_player.py
import numpy as np
import threading
import time

from adik_track import AdikTrack
from adik_sound import AdikSound
from adik_mixer import AdikMixer
from adik_wave_handler import AdikWaveHandler # Pour charger/sauvegarder sons
from adik_audio_engine import AdikAudioEngine 

class AdikPlayer:
    def __init__(self, sample_rate=44100, block_size=1024, num_channels=2):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.num_output_channels = num_channels # Canaux de sortie du player/mixer

        self.tracks = [] # Liste des objets AdikTrack
        self.selected_track_idx = -1 # Index de la piste sélectionnée
        self.current_playback_frame = 0 # Position globale du player en frames
        self.is_playing = False
        # self.is_recording = False # On retire l'enregistrement pour le moment

        self.mixer = AdikMixer(self.sample_rate, self.num_output_channels)

        # Instanciez l'Engine et définissez son callback
        self.audio_engine = AdikAudioEngine(self.sample_rate, self.block_size, self.num_output_channels)
        self.audio_engine.set_callback(self._audio_callback) # Le callback du player devient le callback de l'engine


        self._lock = threading.Lock() # Verrou pour protéger les accès concurrents
        
        # Buffers et états liés à l'enregistrement sont supprimés pour le moment
        # self.recording_buffer = np.array([], dtype=np.float32) 
        # self.recording_sound = None 

        print(f"AdikPlayer initialisé (SR: {self.sample_rate}, Block Size: {self.block_size}, Out Channels: {self.num_output_channels})")

    # --- Gestion des Pistes ---
    def add_track(self, name=None):
        track = AdikTrack(name=name, sample_rate=self.sample_rate, num_channels=self.num_output_channels)
        self.tracks.append(track)
        self.select_track(len(self.tracks) - 1) # Sélectionne la nouvelle piste par défaut
        print(f"Piste ajoutée: {track.name}")
        return track

    def delete_track(self, track_idx):
        if 0 <= track_idx < len(self.tracks):
            deleted_track = self.tracks.pop(track_idx)
            print(f"Piste supprimée: {deleted_track.name}")
            if self.selected_track_idx == track_idx:
                self.selected_track_idx = -1 # Plus de piste sélectionnée si c'était celle-là
            elif self.selected_track_idx > track_idx:
                self.selected_track_idx -= 1 # Ajuster l'index si une piste avant a été supprimée
            return True
        print(f"Erreur: Index de piste invalide ({track_idx}) pour la suppression.")
        return False

    def select_track(self, track_idx):
        if 0 <= track_idx < len(self.tracks):
            self.selected_track_idx = track_idx
            # print(f"Piste sélectionnée: {self.tracks[self.selected_track_idx].name}")
            return True
        # print(f"Erreur: Index de piste invalide ({track_idx}) pour la sélection.")
        return False

    def get_selected_track(self):
        if 0 <= self.selected_track_idx < len(self.tracks):
            return self.tracks[self.selected_track_idx]
        return None
        
    # La fonction arm_track_for_recording est retirée pour le moment
    # def arm_track_for_recording(self, track_idx):
    #     if 0 <= track_idx < len(self.tracks):
    #         for t in self.tracks: # Désarmer toutes les autres pistes
    #             t.is_armed_for_recording = False
            
    #         track = self.tracks[track_idx]
    #         track.is_armed_for_recording = not track.is_armed_for_recording # Basculer l'état
    #         print(f"Piste '{track.name}' armée pour enregistrement: {track.is_armed_for_recording}")
    #         return True
    #     return False

    # --- Transport (Play/Pause/Stop) ---
    def play(self):
        if self.is_playing:
            print("Déjà en lecture.")
            return

        print("Démarrage de la lecture...")
        with self._lock:
            self.is_playing = True
            # Appelle la méthode de l'engine pour démarrer le stream
            self._start_engine()

    def pause(self):
        if not self.is_playing:
            print("Pas en lecture.")
            return
        
        print("Mise en pause.")
        with self._lock:
            self.is_playing = False

    def stop(self):
        if not self.is_playing and not self.audio_engine.is_stream_active(): # Vérifie l'état de l'engine
            print("Déjà arrêté.")
            return

        print("Arrêt du player.")
        with self._lock:
            self.is_playing = False
            self.current_playback_frame = 0
            for track in self.tracks:
                track.reset_playback() 
                # track.is_armed_for_recording = False # Retiré car pas d'enregistrement

            # Logique d'enregistrement est retirée pour le moment
            # if self.is_recording and self.recording_sound and self.recording_buffer.size > 0:
            #     print("Finalisation de l'enregistrement...")
            #     self.recording_sound.audio_data = self.recording_buffer
            #     selected_track = self.get_selected_track()
            #     if selected_track:
            #         selected_track.set_audio_sound(self.recording_sound)
            #         save_path = f"/tmp/recorded_{selected_track.name}.wav"
            #         AdikWaveHandler.save_wav(save_path, self.recording_sound)
            #     else:
            #         new_track = self.add_track(f"Recorded Track {len(self.tracks) + 1}")
            #         new_track.set_audio_sound(self.recording_sound)
            #         save_path = f"/tmp/recorded_new_track_{new_track.id}.wav"
            #         AdikWaveHandler.save_wav(save_path, self.recording_sound)

            #     self.recording_buffer = np.array([], dtype=np.float32)
            #     self.recording_sound = None
            # self.is_recording = False # Retiré car pas d'enregistrement


            # Appelle la méthode de l'engine pour arrêter le stream
            self._stop_engine()

    """
    def stop0(self):
        # Deprecated function
        if not self.is_playing and not self.stream:
            print("Déjà arrêté.")
            return

        print("Arrêt du player.")
        with self._lock:
            self.is_playing = False
            self.current_playback_frame = 0
            for track in self.tracks:
                track.reset_playback() # Réinitialise la position de chaque piste
                # track.is_armed_for_recording = False # Retiré car pas d'enregistrement

            # Logique d'enregistrement est retirée pour le moment
            # if self.is_recording and self.recording_sound and self.recording_buffer.size > 0:
            #     print("Finalisation de l'enregistrement...")
            #     self.recording_sound.audio_data = self.recording_buffer
            #     selected_track = self.get_selected_track()
            #     if selected_track:
            #         selected_track.set_audio_sound(self.recording_sound)
            #         save_path = f"/tmp/recorded_{selected_track.name}.wav"
            #         AdikWaveHandler.save_wav(save_path, self.recording_sound)
            #     else:
            #         new_track = self.add_track(f"Recorded Track {len(self.tracks) + 1}")
            #         new_track.set_audio_sound(self.recording_sound)
            #         save_path = f"/tmp/recorded_new_track_{new_track.id}.wav"
            #         AdikWaveHandler.save_wav(save_path, self.recording_sound)

            #     self.recording_buffer = np.array([], dtype=np.float32)
            #     self.recording_sound = None
            # self.is_recording = False # Retiré car pas d'enregistrement

            self._stop_audio_stream()
    """

    # La fonction record est retirée pour le moment
    # def record(self):
    #     if self.is_recording:
    #         print("Déjà en mode enregistrement. Arrêt de l'enregistrement...")
    #         self.is_recording = False
    #         self.stop() 
    #         return

    #     armed_track = next((t for t in self.tracks if t.is_armed_for_recording), None)
    #     if not armed_track:
    #         print("Erreur: Aucune piste armée pour l'enregistrement. Utilisez 'r' + [num_piste] pour armer.")
    #         return

    #     print("Démarrage de l'enregistrement...")
    #     self.is_recording = True
    #     self.play() 

    # --- Fonctions de positionnement ---
    def _get_max_frames(self):
        """
        Calcule et retourne la durée maximale en frames parmi toutes les pistes chargées.
        """
        max_frames = 0
        for track in self.tracks:
            if track.audio_sound:
                max_frames = max(max_frames, len(track.audio_sound.audio_data) // track.audio_sound.num_channels)
        return max_frames

    def set_position(self, frames):
        """
        Définit la position de lecture globale du player et de toutes les pistes.
        La position est clamper entre 0 et la durée maximale du projet.
        """
        with self._lock:
            max_frames = self._get_max_frames() # Utilise la nouvelle fonction
            
            new_position = max(0, min(max_frames, frames))
            
            if new_position == self.current_playback_frame:
                return

            self.current_playback_frame = new_position
            for track in self.tracks:
                track.playback_position = self.current_playback_frame
            
            print(f"Position de lecture définie à: {self.current_playback_frame} frames ({self.current_time_seconds:.2f}s)")

    def get_position(self):
        """
        Retourne la position de lecture actuelle du player en frames.
        """
        with self._lock:
            return self.current_playback_frame

    def forward(self, frames_to_skip=44100): 
        """Avance la position de lecture du player."""
        self.set_position(self.get_position() + frames_to_skip) # Utilise get_position

    def backward(self, frames_to_skip=44100): 
        """Recule la position de lecture du player."""
        self.set_position(self.get_position() - frames_to_skip) # Utilise get_position

    def goto_start(self):
        """Va au début du projet."""
        self.set_position(0)

    def goto_end(self):
        """Va à la fin du projet (fin de la piste la plus longue)."""
        self.set_position(self._get_max_frames()) # Utilise la nouvelle fonction


    # Gestion du stream de audio_engine
    def _start_engine(self):
        """Démarre l'engine audio."""
        self.audio_engine.start_stream()

    def _stop_engine(self):
        """Arrête l'engine audio."""
        self.audio_engine.stop_stream()


    # Signature du callback modifiée: plus d'indata
    def _audio_callback(self, outdata, frames, time_info, status):
        """
        Le callback audio principal appelé par sounddevice.
        'outdata' doit être rempli avec les samples de sortie.
        """
        if status:
            print(f"Status du callback audio: {status}", flush=True)

        with self._lock:
            # 1. Traitement de l'enregistrement (LOGIQUE RETIRÉE)
            # if self.is_recording and indata is not None and indata.size > 0:
            #     self.recording_buffer = np.append(self.recording_buffer, indata.flatten())

            # 2. Traitement de la lecture
            if not self.is_playing:
                outdata.fill(0.0) # Remplir de zéros si le player est en pause/arrêt
                return

            # Préparer la liste des buffers des pistes à mixer
            track_buffers = []
            
            solo_active = any(track.is_solo for track in self.tracks)

            for track in self.tracks:
                if track.audio_sound and track.audio_sound.audio_data.size > 0:
                    # Gérer les états Mute/Solo
                    if track.is_muted:
                        continue # Ne pas traiter cette piste si elle est muette
                    if solo_active and not track.is_solo:
                        continue # Ne pas traiter cette piste si solo est actif ailleurs et cette piste n'est pas solo

                    # Obtenir le bloc audio de la piste
                    track_block = track.get_audio_block(frames)
                    track_buffers.append(track_block)

            # Mixer les buffers des pistes
            mixed_output = self.mixer.mix_buffers(track_buffers, frames)

            # S'assurer que la sortie est de la bonne taille et forme pour sounddevice
            # mixed_output est 1D (frames * num_channels)
            # outdata est 2D (frames, num_channels)
            expected_output_size = frames * self.num_output_channels
            if mixed_output.size == expected_output_size:
                outdata[:] = mixed_output.reshape((frames, self.num_output_channels))
            else:
                outdata.fill(0.0)
                print("Avertissement: Taille du buffer mixé inattendue.")

            # Mettre à jour la position globale du player
            self.current_playback_frame += frames

            # Optionnel: Arrêter le player si toutes les pistes ont fini de jouer
            all_tracks_finished = True
            for track in self.tracks:
                if track.audio_sound and track.playback_position < (len(track.audio_sound.audio_data) // track.audio_sound.num_channels):
                    all_tracks_finished = False
                    break
            
            if all_tracks_finished:
                print("Toutes les pistes ont fini de jouer. Arrêt automatique.")
                self.is_playing = False # Arrête le player

    # --- Propriété pour l'affichage de la position ---
    @property
    def current_time_seconds(self):
        if self.sample_rate > 0:
            return self.current_playback_frame / self.sample_rate
        return 0.0

    @property
    def total_duration_seconds(self):
        max_frames = 0
        for track in self.tracks:
            if track.audio_sound:
                max_frames = max(max_frames, len(track.audio_sound.audio_data) // track.audio_sound.num_channels)
        
        if self.sample_rate > 0:
            return max_frames / self.sample_rate
        return 0.0

