# adik_player.py
import numpy as np
import threading
import time

from adik_track import AdikTrack
from adik_sound import AdikSound
from adik_mixer import AdikMixer
from adik_wave_handler import AdikWaveHandler # Pour charger/sauvegarder sons
from adik_audio_engine import AdikAudioEngine 

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
        # self.audio_engine = AdikAudioEngine(self.sample_rate, self.block_size, self.num_output_channels)
        self.audio_engine = AdikAudioEngine(sample_rate, block_size, num_output_channels, num_input_channels) # Passer les canaux d'entrée
        self.audio_engine.set_callback(self._audio_callback) # Le callback du player devient le callback de l'engine
        self.mixer = AdikMixer(self.sample_rate, self.num_output_channels)

        self.tracks = [] # Liste des objets AdikTrack
        self.selected_track_idx = -1 # Index de la piste sélectionnée
        self.current_playback_frame = 0 # Position globale du player en frames
        self.is_playing = False

        self.is_recording = False # On retire l'enregistrement pour le moment
        self.recording_buffer = np.array([], dtype=np.float32) 
        self.recording_sound = None 
        self.total_duration_seconds = 0.0 # Durée maximale parmi les pistes
        self.current_time_seconds = 0.0 # Temps actuel de lecture
  

        self._lock = threading.Lock() # Verrou pour protéger les accès concurrents
        
        print(f"AdikPlayer initialisé (SR: {self.sample_rate}, Block Size: {self.block_size}, Out Channels: {self.num_output_channels})")
    #----------------------------------------

    # --- Gestion des Pistes ---
    def add_track(self, name=None):
        track = AdikTrack(name=name, sample_rate=self.sample_rate, num_channels=self.num_output_channels)
        self.tracks.append(track)
        self.select_track(len(self.tracks) - 1) # Sélectionne la nouvelle piste par défaut
        print(f"Piste ajoutée: {track.name}")
        return track

    #----------------------------------------

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

    #----------------------------------------

    def select_track(self, track_idx):
        if 0 <= track_idx < len(self.tracks):
            self.selected_track_idx = track_idx
            # print(f"Piste sélectionnée: {self.tracks[self.selected_track_idx].name}")
            return True
        # print(f"Erreur: Index de piste invalide ({track_idx}) pour la sélection.")
        return False

    #----------------------------------------

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
    
#----------------------------------------

    def _update_total_duration(self):
        max_dur = 0.0
        for track in self.tracks:
            if track.audio_sound:
                max_dur = max(max_dur, track.audio_sound.get_duration_seconds())
        self.total_duration_seconds = max_dur


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

    #----------------------------------------

    def pause(self):
        if not self.is_playing:
            print("Pas en lecture.")
            return
        
        print("Mise en pause.")
        with self._lock:
            self.is_playing = False
            if self.is_recording: # Si on était en enregistrement, finaliser
                self.is_recording = False
                # self.finish_recording()
                pass

    #----------------------------------------

    def stop(self):
        if not self.is_playing and not self._is_engine_running(): # Vérifie l'état de l'engine
            print("Déjà arrêté.")
            return

        print("Arrêt du player.")

        with self._lock:
            self.is_playing = False
            # Si on était en enregistrement, finaliser avant de réinitialiser
            if self.is_recording:
                self.is_recording = False
                # self.finish_recording()
                pass

        # Appelle la méthode de l'engine pour arrêter le stream
        # Seulement si rien d'autre ne tourne (pas de lecture, pas d'enregistrement)
        if not self.is_playing and not self.is_recording and self._is_engine_running():
            self._stop_engine()
            pass

    #----------------------------------------

    # Méthodes pour l'enregistrement
    def start_recording(self):
        """Démarre l'enregistrement audio."""
        if not self._is_engine_running():
            self._start_engine() # S'assurer que le stream est actif et configuré pour l'entrée
        
        with self._lock:
            self.is_recording = True
            self.recording_buffer = np.array([], dtype=np.float32) # Effacer le buffer précédent
            print("Player: Enregistrement démarré.")
            self.recording_sound = None # Réinitialiser l'objet AdikSound

    #----------------------------------------

    def stop_recording(self):
        """Arrête l'enregistrement audio et déclenche la finalisation."""
        if not self.is_recording:
            print("Player: Pas en enregistrement.")
            return
        
        print("Player: Arrêt de l'enregistrement.")
        with self._lock:
            self.is_recording = False
            # à déplacer dans finish_recording
            self.recording_sound = AdikSound(
                    name=f"rec_{time.strftime('%H%M%S')}",
                    audio_data=self.recording_buffer,
                    sample_rate=self.sample_rate,
                    num_channels=self.num_input_channels # Les canaux de l'enregistrement sont les canaux d'entrée
                )
     
            # self.finish_recording() # Appelle la nouvelle fonction de finalisation
            # Note: is_recording est mis à False dans finish_recording
            
            # Arrêter le stream seulement si plus rien n'est actif
            if not self.is_playing and not self.is_recording and self._is_engine_running():
                self._stop_engine()

    #----------------------------------------

    def finish_recording(self):
        """
        Finalise l'enregistrement en créant un AdikSound à partir du buffer
        et l'assigne à la piste sélectionnée ou à une nouvelle piste.
        """
        if not self.is_recording:
            print("Player: Aucune session d'enregistrement active à finaliser.")
            return

        with self._lock:
            print("Player: Finalisation de l'enregistrement...")
            self.is_recording = False # Mettre fin à l'état d'enregistrement immédiatement

            if self.recording_buffer.size > 0:
                # Créer un AdikSound à partir du buffer enregistré
                self.recording_sound = AdikSound(
                    name=f"Enregistrement {time.strftime('%H%M%S')}",
                    audio_data=self.recording_buffer,
                    sample_rate=self.sample_rate,
                    num_channels=self.num_input_channels # Les canaux de l'enregistrement sont les canaux d'entrée
                )
                
                selected_track = self.get_selected_track()
                if selected_track:
                    # Assigner le son enregistré à la piste sélectionnée
                    selected_track.set_audio_sound(self.recording_sound)
                    print(f"Player: Enregistrement assigné à la piste '{selected_track.name}'.")
                else:
                    # Si aucune piste sélectionnée, créer une nouvelle piste
                    new_track_name = f"Piste Enregistrée {len(self.tracks) + 1}"
                    new_track = self.add_track(new_track_name)
                    new_track.set_audio_sound(self.recording_sound)
                    self.select_track(len(self.tracks) - 1) # Sélectionner la nouvelle piste
                    print(f"Player: Enregistrement ajouté à une nouvelle piste '{new_track.name}'.")
                
                # Mettre à jour la durée totale du projet après l'ajout de l'enregistrement
                self._update_total_duration()

                # Le buffer est vidé après avoir été utilisé pour créer recording_sound
                self.recording_buffer = np.array([], dtype=np.float32)
                # L'objet recording_sound est conservé pour la piste, mais on le réinitialise pour la prochaine session.
                # self.recording_sound = None # Décommenter si vous voulez qu'il soit None après la finalisation
            else:
                print("Player: Le buffer d'enregistrement est vide. Rien à finaliser.")

    #----------------------------------------

    def save_recording(self, filename=None):
        """Sauvegarde le son de l'enregistrement actuel ou le dernier enregistré dans un fichier WAV."""
        saved = False
        if self.is_recording:
            print("Player: L'enregistrement est toujours actif. Veuillez l'arrêter d'abord pour le sauvegarder.")
            return

        sound_to_save = self.recording_sound # Tenter de sauvegarder le dernier son finalisé

        if sound_to_save and sound_to_save.audio_data.size > 0:
            if filename is None:
                # Utilise un nom de fichier par défaut basé sur le nom du son
                filename = f"/tmp/{sound_to_save.name.replace(' ', '_').replace(':', '_')}.wav"

            if AdikWaveHandler.save_wav(filename, sound_to_save):
                saved = True
                print(f"Player: Enregistrement sauvegardé dans '{filename}'.")
            else:
                print(f"Player: Échec de la sauvegarde de l'enregistrement dans '{filename}'.")
        else:
            print("Player: Aucun enregistrement finalisé ou le buffer est vide. Rien à sauvegarder.")
            print("Astuce: Appuyez sur 'R' pour démarrer l'enregistrement, puis 'R' ou 'Espace' ou 'V' pour le finaliser avant de sauvegarder.")
        
        return saved

    #----------------------------------------

  
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

    #----------------------------------------

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
        self.set_position(self.get_position() + frames_to_skip) # Utilise get_position

    #----------------------------------------

    def backward(self, frames_to_skip=44100): 
        """Recule la position de lecture du player."""
        self.set_position(self.get_position() - frames_to_skip) # Utilise get_position

    #----------------------------------------

    def goto_start(self):
        """Va au début du projet."""
        self.set_position(0)

    #----------------------------------------

    def goto_end(self):
        """Va à la fin du projet (fin de la piste la plus longue)."""
        self.set_position(self._get_max_frames()) # Utilise la nouvelle fonction

    #----------------------------------------


    # Gestion du stream de audio_engine
    def _start_engine(self):
        """Démarre l'engine audio."""
        self.audio_engine.start_stream()

    #----------------------------------------

    def _stop_engine(self):
        """Arrête l'engine audio."""
        self.audio_engine.stop_stream()

    #----------------------------------------

    def _is_engine_running(self):
        """Retourne si le moteur audio est actif"""
        return self.audio_engine.is_stream_active()

    #----------------------------------------


    def _audio_callback(self, indata, outdata, frames, time_info, status):
        """
        Le callback audio principal appelé par sounddevice.
        'indata' contient les samples d'entrée, 'outdata' doit être rempli avec les samples de sortie.
        """
        if status:
            print(f"Status du callback audio: {status}", flush=True)
            beep()

        with self._lock:
            # 1. Traitement de l'enregistrement
            if self.is_recording and indata is not None and indata.size > 0:
                beep()
                # Ajouter le buffer d'enregistrement indata à recording_buffer
                # indata est de forme (frames, num_input_channels), on le flatten pour le buffer 1D entrelacé
                # S'assurer que indata a le type float32 avant d'append
                self.recording_buffer = np.append(self.recording_buffer, indata.astype(np.float32).flatten())

            # 2. Traitement de la lecture
            if not self.is_playing:
                outdata.fill(0.0) # Remplir de zéros si le player est en pause/arrêt
                return

            # Préparer la liste des buffers des pistes à mixer
            track_buffers = []
            
            # Tester s'il y a une piste qui est en solo
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
            self.current_time_seconds = self.current_playback_frame / self.sample_rate

            # Optionnel: Arrêter le player si toutes les pistes ont fini de jouer
            all_tracks_finished = True
            for track in self.tracks:
                if track.audio_sound and track.playback_position < (len(track.audio_sound.audio_data) // track.audio_sound.num_channels):
                    all_tracks_finished = False
                    break
                
            if all_tracks_finished and not self.is_recording: # Ne pas arrêter si on est en enregistrement
                print("Player: Toutes les pistes ont fini de jouer. Arrêt automatique.")
                self.is_playing = False # Arrête le player
                # On ne stop_stream pas ici. Géré par stop() ou stop_recording() si nécessaire.
    
    #----------------------------------------


    # Signature du callback modifiée: plus d'indata
    def _audio_callback_for_output(self, outdata, frames, time_info, status):
        """
        # Note: This function is Deprecated
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

    #----------------------------------------
    
    
    """
    # --- Propriété pour l'affichage de la position ---
    @property
    def current_time_seconds(self):
        if self.sample_rate > 0:
            return self.current_playback_frame / self.sample_rate
        return 0.0

    #----------------------------------------

    @property
    def total_duration_seconds(self):
        max_frames = 0
        for track in self.tracks:
            if track.audio_sound:
                max_frames = max(max_frames, len(track.audio_sound.audio_data) // track.audio_sound.num_channels)
        
        if self.sample_rate > 0:
            return max_frames / self.sample_rate
        return 0.0

    #----------------------------------------
"""

