# adik_player.py
import numpy as np
import threading
import time

from adik_track import AdikTrack
from adik_sound import AdikSound
from adik_mixer import AdikMixer
from adik_wave_handler import AdikWaveHandler # Pour charger/sauvegarder sons
import sounddevice as sd # Pour des infos de device

class AdikPlayer:
    def __init__(self, sample_rate=44100, block_size=1024, num_channels=2):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.num_output_channels = num_channels # Canaux de sortie du player/mixer

        self.tracks = [] # Liste des objets AdikTrack
        self.selected_track_idx = -1 # Index de la piste sélectionnée
        self.current_playback_frame = 0 # Position globale du player en frames
        self.is_playing = False
        self.is_recording = False # État global d'enregistrement

        self.mixer = AdikMixer(self.sample_rate, self.num_output_channels)
        self.stream = None # Le stream sounddevice sera géré ici

        self._lock = threading.Lock() # Verrou pour protéger les accès concurrents
        
        # Pour l'enregistrement, un buffer temporaire pour les données d'entrée
        self.recording_buffer = np.array([], dtype=np.float32) 
        self.recording_sound = None # Le AdikSound en cours d'enregistrement

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
            print(f"Piste sélectionnée: {self.tracks[self.selected_track_idx].name}")
            return True
        print(f"Erreur: Index de piste invalide ({track_idx}) pour la sélection.")
        return False

    def get_selected_track(self):
        if 0 <= self.selected_track_idx < len(self.tracks):
            return self.tracks[self.selected_track_idx]
        return None
        
    def arm_track_for_recording(self, track_idx):
        if 0 <= track_idx < len(self.tracks):
            for t in self.tracks: # Désarmer toutes les autres pistes
                t.is_armed_for_recording = False
            
            track = self.tracks[track_idx]
            track.is_armed_for_recording = not track.is_armed_for_recording # Basculer l'état
            print(f"Piste '{track.name}' armée pour enregistrement: {track.is_armed_for_recording}")
            return True
        return False

    # --- Transport (Play/Pause/Stop) ---
    def play(self):
        if self.is_playing:
            print("Déjà en lecture.")
            return

        print("Démarrage de la lecture...")
        with self._lock:
            # Si nous enregistrons, préparons le buffer d'enregistrement
            if self.is_recording:
                selected_track = self.get_selected_track()
                if selected_track and selected_track.is_armed_for_recording:
                    # Créer un nouveau AdikSound vide pour l'enregistrement
                    self.recording_sound = AdikSound(name=f"Rec {selected_track.name}", 
                                                     sample_rate=self.sample_rate, 
                                                     num_channels=self.num_output_channels) # Enregistrer en stéréo pour l'instant
                    self.recording_buffer = np.array([], dtype=np.float32)
                    print(f"Prêt à enregistrer sur la piste '{selected_track.name}'.")
                else:
                    print("Aucune piste armée pour l'enregistrement. L'enregistrement ne démarrera pas.")
                    self.is_recording = False # Désactiver l'état d'enregistrement global

            self.is_playing = True
            self._start_audio_stream()

    def pause(self):
        if not self.is_playing:
            print("Pas en lecture.")
            return
        
        print("Mise en pause.")
        with self._lock:
            self.is_playing = False
            # Optionnel: arrêter le stream si on veut libérer les ressources, ou laisser actif
            # pour une reprise instantanée. Pour le prototype, on laisse actif.

    def stop(self):
        if not self.is_playing and not self.stream:
            print("Déjà arrêté.")
            return

        print("Arrêt du player.")
        with self._lock:
            self.is_playing = False
            self.current_playback_frame = 0
            for track in self.tracks:
                track.reset_playback() # Réinitialise la position de chaque piste
                track.is_armed_for_recording = False # Désarme toutes les pistes à l'arrêt

            if self.is_recording and self.recording_sound and self.recording_buffer.size > 0:
                print("Finalisation de l'enregistrement...")
                self.recording_sound.audio_data = self.recording_buffer
                # Assigner le son enregistré à la piste sélectionnée (ou une nouvelle piste)
                selected_track = self.get_selected_track()
                if selected_track:
                    selected_track.set_audio_sound(self.recording_sound)
                    save_path = f"/tmp/recorded_{selected_track.name}.wav"
                    AdikWaveHandler.save_wav(save_path, self.recording_sound)
                else:
                    # Si aucune piste sélectionnée, on pourrait créer une nouvelle piste
                    new_track = self.add_track(f"Recorded Track {len(self.tracks) + 1}")
                    new_track.set_audio_sound(self.recording_sound)
                    save_path = f"/tmp/recorded_new_track_{new_track.id}.wav"
                    AdikWaveHandler.save_wav(save_path, self.recording_sound)

                self.recording_buffer = np.array([], dtype=np.float32)
                self.recording_sound = None
            self.is_recording = False # Arrêt de l'enregistrement global

            self._stop_audio_stream()

    def record(self):
        if self.is_recording:
            print("Déjà en mode enregistrement. Arrêt de l'enregistrement...")
            self.is_recording = False
            self.stop() # Arrête le player et finalise l'enregistrement
            return

        # Vérifier si une piste est armée
        armed_track = next((t for t in self.tracks if t.is_armed_for_recording), None)
        if not armed_track:
            print("Erreur: Aucune piste armée pour l'enregistrement. Utilisez 'r' + [num_piste] pour armer.")
            return

        print("Démarrage de l'enregistrement...")
        self.is_recording = True
        self.play() # Lance la lecture (qui va gérer la préparation du buffer d'enregistrement)


    def forward(self, frames_to_skip=44100): # Par défaut, 1 seconde d'avance
        with self._lock:
            max_frames = 0
            for track in self.tracks:
                if track.audio_sound:
                    max_frames = max(max_frames, len(track.audio_sound.audio_data) // track.audio_sound.num_channels)
            
            self.current_playback_frame = min(max_frames, self.current_playback_frame + frames_to_skip)
            for track in self.tracks:
                track.playback_position = self.current_playback_frame
            print(f"Avance rapide à la position: {self.current_playback_frame} frames")

    def backward(self, frames_to_skip=44100): # Par défaut, 1 seconde de recul
        with self._lock:
            self.current_playback_frame = max(0, self.current_playback_frame - frames_to_skip)
            for track in self.tracks:
                track.playback_position = self.current_playback_frame
            print(f"Retour rapide à la position: {self.current_playback_frame} frames")

    def goto_start(self):
        with self._lock:
            self.current_playback_frame = 0
            for track in self.tracks:
                track.reset_playback()
            print("Retour au début.")

    def goto_end(self):
        with self._lock:
            max_frames = 0
            for track in self.tracks:
                if track.audio_sound:
                    max_frames = max(max_frames, len(track.audio_sound.audio_data) // track.audio_sound.num_channels)
            
            self.current_playback_frame = max_frames # Aller à la fin de la piste la plus longue
            for track in self.tracks:
                track.playback_position = self.current_playback_frame
            print("Aller à la fin.")

    # --- Gestion du Stream Audio (Interne au Player) ---
    def _start_audio_stream(self):
        if self.stream and self.stream.active:
            print("Stream audio déjà actif.")
            return

        try:
            # Détection automatique des périphériques pour l'entrée/sortie
            # Pour l'enregistrement, nous avons besoin d'un flux d'entrée.
            # sounddevice peut créer un stream bidirectionnel ou deux streams séparés.
            # Pour simplifier, créons un stream bidirectionnel si l'enregistrement est actif.
            input_device_info = None
            if self.is_recording:
                try:
                    default_input_device_idx = sd.default.device[0] # Index du périphérique d'entrée par défaut
                    input_device_info = sd.query_devices(default_input_device_idx)
                    print(f"Périphérique d'entrée par défaut: {input_device_info['name']}")
                except Exception as e:
                    print(f"Avertissement: Impossible de trouver le périphérique d'entrée par défaut. Enregistrement désactivé: {e}")
                    self.is_recording = False # Impossible d'enregistrer sans périphérique d'entrée

            if self.is_recording and input_device_info:
                # Stream bidirectionnel (inout_buffer pour l'entrée, outdata pour la sortie)
                self.stream = sd.Stream(
                    samplerate=self.sample_rate,
                    blocksize=self.block_size,
                    channels=self.num_output_channels, # Canaux de sortie
                    dtype='float32',
                    callback=self._audio_callback,
                    # Pour l'entrée:
                    device=(input_device_info['index'], sd.default.device[1]), # Input, Output device indices
                    # channels peut être un tuple (input_channels, output_channels)
                    channels=(input_device_info['max_input_channels'], self.num_output_channels)
                )
            else:
                # Stream en sortie seule
                self.stream = sd.OutputStream(
                    samplerate=self.sample_rate,
                    blocksize=self.block_size,
                    channels=self.num_output_channels,
                    dtype='float32',
                    callback=self._audio_callback
                )

            self.stream.start()
            print("Stream audio démarré.")
        except Exception as e:
            print(f"Erreur lors du démarrage du stream audio: {e}. Assurez-vous que les périphériques sont disponibles.")
            self.stream = None
            self.is_playing = False
            self.is_recording = False

    def _stop_audio_stream(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            print("Stream audio arrêté.")

    def _audio_callback(self, outdata, frames, time_info, status):
        """
        Le callback audio principal appelé par sounddevice.
        'indata' contient les samples d'entrée (pour l'enregistrement).
        'outdata' doit être rempli avec les samples de sortie.
        """
        if status:
            print(f"Status du callback audio: {status}", flush=True)

        with self._lock:
            # 1. Traitement de l'enregistrement (si actif et si indata est présent)
            if self.is_recording and indata is not None and indata.size > 0:
                # indata est (frames, input_channels), flatten pour stocker
                self.recording_buffer = np.append(self.recording_buffer, indata.flatten())

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
                    # Note: get_audio_block doit retourner un buffer de la taille (frames * track.num_channels)
                    # et devrait gérer sa propre position de lecture.
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
                # Ne pas appeler stop() directement ici car cela peut causer un deadlock
                # ou des problèmes de thread. Il faut laisser le thread principal gérer l'arrêt.
                # On peut signaler l'arrêt pour le thread principal.
                # Pour l'instant, juste is_playing = False fera que le prochain callback remplira de 0.

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

