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
        self.current_playback_frame = 0 # Position globale du player en frames
        self._playing = False
        self._recording = False # Retirer le commentaire pour que l'enregistrement soit fonctionnel
        self.recording_buffer = np.array([], dtype=np.float32) 
        self.recording_sound = None 
        self.recording_start_frame = 0 # La frame où l'enregistrement a commencé
        self.recording_end_frame = 0 # Initialiser la fin à la même position
        self.recording_mode = AdikTrack.RECORDING_MODE_REPLACE

        # total_duration_seconds et current_time_seconds seront gérés comme des propriétés (voir plus bas)
        self.total_duration_seconds_cached = 0.0 # Cache pour la durée totale
        self.total_duration_frames_cached = 0
        
        self._lock = threading.Lock() # Verrou pour protéger les accès concurrents

        self.is_looping = False
        self.loop_start_frame = 0
        self.loop_end_frame = 0
        self.loop_mode =0 # 0: mode normal pour boucler sur le player entier, 1: Custom: pour boucler d'un poin à un autre
        
        # --- Variables du métronome ---
        self.metronome = AdikMetronome(sample_rate=sample_rate, num_channels=num_output_channels)
        self.metronome.update_tempo()  # Initialiser le tempo au démarrage

        print(f"AdikPlayer initialisé (SR: {self.sample_rate}, Block Size: {self.block_size}, Out Channels: {self.num_output_channels}, In Channels: {self.num_input_channels})")
    #----------------------------------------

    # --- Gestion des Pistes ---
    def add_track(self, name=None):
        if name is None:
            name = f"Piste {len(self.track_list) + 1}"
        track = AdikTrack(name=name, sample_rate=self.sample_rate, num_channels=self.num_output_channels)
        self.track_list.append(track)
        self.select_track(len(self.track_list) - 1) # Sélectionne la nouvelle piste par défaut
        # self._update_total_duration_cache() # Mettre à jour la durée totale
        # Mettre à jour la durée totale et d'autres paramètres
        self._update_params()
        print(f"Piste ajoutée: {track.name}")
        return track

    #----------------------------------------

    def delete_track(self, track_idx):
        if 0 <= track_idx < len(self.track_list):
            deleted_track = self.track_list.pop(track_idx)
            print(f"Piste supprimée: {deleted_track.name}")
            if self.selected_track_idx == track_idx:
                self.selected_track_idx = max(-1, len(self.track_list) - 1) # Plus de piste sélectionnée si c'était celle-là
            elif self.selected_track_idx > track_idx:
                self.selected_track_idx -= 1 # Ajuster l'index si une piste avant a été supprimée
            # self._update_total_duration_cache() # Mettre à jour la durée totale
            self._update_params()
            return True
        print(f"Erreur: Index de piste invalide ({track_idx}) pour la suppression.")
        return False

    #----------------------------------------
    
    def remove_all_tracks(self):
        """
        Supprime toutes les pistes et nettoie les données associées.
        """
        self.stop()  # Arrêter la lecture avant de supprimer les pistes
        for track in self.track_list:
            # Nettoyer les ressources de chaque piste si nécessaire
            if hasattr(track, 'audio_data'):
                del track.audio_data
        self.track_list = []
        self.selected_track_idx = -1
        # Mettre à jour la durée totale et d'autres paramètres
        self._update_params()

    #----------------------------------------

    def delete_audio_from_track(self, track_index: int, start_frame: int, end_frame: int):
        """
        Supprime complètement les données audio d'une piste entre les positions
        start_frame et end_frame. La longueur de la piste est réduite.
        """
        if 0 <= track_index < len(self.track_list):
            track = self.track_list[track_index]
            audio_data = track.get_audio_data()
            
            if audio_data is None:
                print(f"Avertissement: La piste '{track.name}' est vide, aucune suppression n'a été effectuée.")
                return

            # Les indices de trames sont convertis en indices de samples
            start_sample = int(start_frame * track.num_channels)
            end_sample = int(end_frame * track.num_channels)
            
            # S'assurer que les trames sont dans les limites valides
            length_samples = track.audio_sound.length_samples
            start_sample = max(0, start_sample)
            end_sample = min(length_samples, end_sample)

            if start_sample < end_sample:
                # Créer une nouvelle liste de données audio
                # en ignorant la partie à supprimer
                part_before = audio_data[:start_sample]
                part_after = audio_data[end_sample:]

                # Utiliser AdikSound.concat_audio_data pour joindre les deux segments
                # au lieu de l'opérateur '+'
                new_audio_data = AdikSound.concat_audio_data(part_before, part_after)

                # Mettre à jour les données audio de la piste
                track.set_audio_data(new_audio_data)
                
                # Mettre à jour les paramètres de la piste (durée, etc.)
                # Ceci est déjà fait depuis la fonction set_audio_data
                # track._update_duration()
                self._update_params()
                
                print(f"Données audio de la piste '{track.name}' supprimées de la trame {start_frame} à {end_frame}. Nouvelle longueur: {len(new_audio_data)} samples.")
            else:
                print("Avertissement: Les trames de début et de fin sont invalides.")
        else:
            print(f"Erreur: Index de piste invalide ({track_index}).")

    #----------------------------------------

    def erase_audio_from_track(self, track_index, start_frame, end_frame):
        """
        Remplace les données audio d'une piste par du silence (valeurs zéro)
        entre les positions start_frame et end_frame.
        La longueur de la piste reste inchangée.
        """
        if 0 <= track_index < len(self.track_list):
            track = self.track_list[track_index]
            audio_data = track.get_audio_data()
            
            # Les indices de trames sont convertis en indices de samples
            start_sample = int(start_frame * track.num_channels)
            end_sample = int(end_frame * track.num_channels)
            
            # S'assurer que les trames sont dans les limites valides
            length_samples = track.audio_sound.length_samples
            start_sample = max(0, start_sample)
            end_sample = min(length_samples, end_sample)

            if start_sample < end_sample:
                # Remplir la section avec des zéros pour créer du silence
                for i in range(start_sample, end_sample):
                    audio_data[i] = 0
                
                print(f"Données audio de la piste '{track.name}' effacées (silence) de la trame {start_frame} à {end_frame}.")
            else:
                print("Avertissement: Les trames de début et de fin sont invalides.")
        else:
            print(f"Erreur: Index de piste invalide ({track_index}).")

    #----------------------------------------

    def has_solo_track(self) -> bool:
        """
        Vérifie si au moins une piste est en mode solo.
        """
        return any(track.is_solo() for track in self.track_list)

    #----------------------------------------

    def bounce_to_track(self, start_frame=0, end_frame=-1):
        # Déterminer la durée totale du mixage
        if end_frame == -1:
            end_frame = self.total_duration_frames_cached
     
        # S'assurer que les trames sont dans les limites
        start_frame = max(0, start_frame)
        end_frame = min(end_frame, self.total_duration_frames_cached)
     
        if start_frame >= end_frame:
            print(f"Avertissement: Les trames de mixage sont invalides.: start_frame: {start_frame}, end_frame: {end_frame}")
            return

        mix_length_frames = end_frame - start_frame
     
        # Créer le tampon de mixage vide
        mix_buffer = AdikSound.new_audio_data(mix_length_frames * self.num_output_channels)
     
        # Sauvegarder la position de lecture pour la restaurer plus tard
        saved_playback_position = self.current_playback_frame
     
        solo_mode = self.has_solo_track()
     
        # Pour chaque piste, la lire et mixer le son dans le tampon
        for track in self.track_list:
            # Ne mixer que les pistes non muettes ou solo
            if track.is_muted() or (solo_mode and not track.is_solo()):
                continue
             
            # Définir la position de lecture de la piste au début de la zone de mixage
            track.set_playback_position(start_frame)
             
            # Lire les données de la piste par blocs et les mixer
            num_frames_read = 0
            while num_frames_read < mix_length_frames:
                frames_to_read = min(self.block_size, mix_length_frames - num_frames_read)

                # Créer une "vue" sur la partie du tampon de mixage où le mixage aura lieu
                mix_slice = mix_buffer[num_frames_read * self.num_output_channels : (num_frames_read + frames_to_read) * self.num_output_channels]
                 
                # Mixer le bloc de la piste dans la tranche du tampon de mixage
                track.mix_sound_data(mix_slice, frames_to_read)

                num_frames_read += frames_to_read

        # Créer un nouvel objet AdikSound avec le son mixé
        bounced_sound = AdikSound(
            name="Bounced Audio",
            audio_data=mix_buffer,
            sample_rate=self.sample_rate,
            num_channels=self.num_output_channels
        )

        # Ajouter une nouvelle piste et lui assigner le son mixé
        new_track = self.add_track(name="Piste Mixée")
        new_track.set_audio_sound(bounced_sound, offset_frames=start_frame)

        # Restaurer la position de lecture du player
        self.set_position(saved_playback_position)
         
        print(f"Mixage (bounce) terminé. Le son a été ajouté à la piste '{new_track.name}'.")

    #----------------------------------------

    def select_track(self, track_idx):
        if 0 <= track_idx < len(self.track_list):
            self.selected_track_idx = track_idx
            # print(f"Piste sélectionnée: {self.track_list[self.selected_track_idx].name}")
            return True
        # print(f"Erreur: Index de piste invalide ({track_idx}) pour la sélection.")
        return False

    #----------------------------------------

    def get_selected_track(self):
        if 0 <= self.selected_track_idx < len(self.track_list):
            return self.track_list[self.selected_track_idx]
        return None
        
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
        """ mise à jour des paramètres importants du player """
        self._update_total_duration_cache()
        if self.loop_mode == 0: # mode normal
            # update loop params
            self.loop_start_frame =0
            self.loop_end_frame = self.total_duration_frames_cached

    #----------------------------------------

    # --- Transport (Play/Pause/Stop) ---
    def is_playing(self):
        return self._playing

    #----------------------------------------

    def is_recording(self):
        return self._recording

    #----------------------------------------

    def play(self):
        # Si on est en enregistrement, le bouton 'Play' agit comme 'Stop Recording'
        if self._recording:
            self.stop_recording()
            return

        if self._playing:
            print("Déjà en lecture.")
            return

        print("Démarrage de la lecture...")
        with self._lock:
            self._playing = True
            self._start_engine() # Appelle la méthode de l'engine pour démarrer le stream

    #----------------------------------------

    def pause(self):
        if not self._playing and not self._recording:
            print("Pas en lecture ou en enregistrement.")
            return
        
        print("Mise en pause.")
        with self._lock:
            self._playing = False
            if self._recording: # Si on était en enregistrement, finaliser
                self._finish_recording()
            # La gestion de l'arrêt du moteur est dans stop() ou stop_recording()

    #----------------------------------------

    def stop(self):
        if not self._playing and not self._recording and not self._is_engine_running():
            print("Déjà arrêté.")
            return

        print("Arrêt du player.")

        with self._lock:
            self._playing = False
            # Si on était en enregistrement, finaliser avant de réinitialiser
            if self._recording:
                self._finish_recording()
            
            self.current_playback_frame = 0
            for track in self.track_list:
                track.reset_playback_position() # Utilise la méthode correcte
            
        # Appelle la méthode de l'engine pour arrêter le stream
        # Seulement si rien d'autre ne tourne (pas de lecture, pas d'enregistrement)
        if not self._playing and not self._recording and self._is_engine_running():
            self._stop_engine()

    #----------------------------------------

    # --- Méthodes pour l'enregistrement ---
    def start_recording(self):
        """Démarre l'enregistrement audio à la position actuelle du player."""
        if self._recording:
            print("Player: Déjà en enregistrement. Appuyez sur 'R' de nouveau pour arrêter.")
            return

        selected_track = self.get_selected_track()
        if not selected_track or not selected_track.is_armed():
            print("Player: Aucune piste armée pour l'enregistrement.")
            return

        # Démarrer spécifiquement le stream d'entrée
        if not self.audio_engine.is_input_running():
            self.audio_engine.start_input_stream()

        """
        # S'assurer que le stream est actif (et configuré pour l'entrée)
        if not self._is_engine_running():
            self._start_engine()
        """
        
        with self._lock:
            self._recording = True
            self.recording_buffer = np.array([], dtype=np.float32) # Effacer le buffer précédent
            self.recording_sound = None # Réinitialiser l'objet AdikSound
            
            # Stocker la position de début d'enregistrement
            self.recording_start_frame = self.current_playback_frame 
            self.recording_end_frame = self.current_playback_frame # Initialiser la fin à la même position

            # Ne pas réinitialiser la position de lecture ici
            self._playing = True # Démarrer la lecture pour le monitoring pendant l'enregistrement
            print(f"Player: Enregistrement démarré à la frame {self.recording_start_frame}.")

    #----------------------------------------

    def stop_recording(self):
        """Arrête l'enregistrement audio et déclenche la finalisation."""
        if not self._recording:
            print("Player: Pas en enregistrement.")
            return
        
        print("Player: Arrêt de l'enregistrement.")
        with self._lock:
            # Cette fonction doit être appelée sans être sous un vérou (lock)
            self._finish_recording() # Appelle la nouvelle fonction de finalisation
            # Note: is_recording est mis à False dans _finish_recording
            
            """
            # Arrêter le stream seulement si plus rien n'est actif
            if not self._playing and not self._recording and self._is_engine_running():
                self._stop_engine()
            """

        # Arrêter le stream d'entrée si nécessaire
        ### Note: Cela doit se faire en dehors du vérou, pour éviter des vérous imbriqués
        if self.audio_engine.is_input_running():
            self.audio_engine.stop_input_stream()

    #----------------------------------------
    
    def _finish_recording(self):
        if not self._recording:
            print("Player: Aucune session d'enregistrement active à finaliser (interne).")
            return

        print("Player: Finalisation de l'enregistrement...")
        self._recording = False

        if self.recording_buffer.size > 0:
            self.recording_end_frame = self.current_playback_frame 
            recorded_sound_data = self.recording_buffer
            
            selected_track = self.get_selected_track()

            if selected_track:
                # IMPORTANT : on passe le nombre de canaux de la prise (canaux d'entrée)
                selected_track.arrange_take(
                    new_take_audio_data=recorded_sound_data,
                    take_start_frame=self.recording_start_frame,
                    take_end_frame=self.recording_end_frame,
                    recording_mode=self.recording_mode,
                    new_take_channels=self.num_input_channels # <<< NOUVEAU
                )
                print(f"Player: Enregistrement arrangé sur la piste '{selected_track.name}'.")
                # --- Mettre à jour la position de lecture de la piste ---
                # On ajuste la position de lecture de la piste à la position globale du player.
                # Cela permet de garantir qu'elle est bien synchronisée avec le reste des pistes.
                selected_track.set_playback_position(self.current_playback_frame)

            else:
                new_track_name = f"Piste Enregistrée {len(self.track_list) + 1}"
                new_track = self.add_track(new_track_name)
                
                take_length_frames = recorded_sound_data.size // self.num_input_channels
                converted_data = AdikSound.convert_channels(recorded_sound_data, self.num_input_channels, self.num_output_channels, take_length_frames)

                new_sound = AdikSound(
                    name=f"adik_rec_{time.strftime('%H%M%S')}",
                    audio_data=converted_data,
                    sample_rate=self.sample_rate,
                    num_channels=self.num_output_channels
                )
                new_track.set_audio_sound(new_sound, offset_frames=self.recording_start_frame)
                print(f"Player: Enregistrement ajouté à une nouvelle piste '{new_track.name}' à la frame {self.recording_start_frame}.")
                
                # --- Mettre à jour la position de lecture de la nouvelle piste ---
                new_track.set_playback_position(self.current_playback_frame)
            
            # self._update_total_duration_cache()
            self._update_params()
            self.recording_buffer = np.array([], dtype=np.float32)
        else:
            print("Player: Le buffer d'enregistrement est vide. Rien à finaliser.")
        
        print("Player: Enregistrement finalisé.")

    #----------------------------------------

    def set_recording_mode(self, mode: int):
        """Définit le mode d'enregistrement pour les futures prises."""
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
        """Sauvegarde le son de l'enregistrement actuel ou le dernier enregistré dans un fichier WAV."""
        # Note: Cette fonction ne doit PAS appeler _finish_recording,
        # elle doit être appelée APRES que l'enregistrement ait été arrêté et finalisé.
        if self._recording:
            print("Player: L'enregistrement est toujours actif. Veuillez l'arrêter d'abord pour le sauvegarder.")
            return

        sound_to_save = self.recording_sound # Tente de sauvegarder le dernier son finalisé

        if sound_to_save and sound_to_save.length_frames > 0:
            if filename is None:
                # Utilise un nom de fichier par défaut basé sur le nom du son
                filename = f"/tmp/{sound_to_save.name.replace(' ', '_').replace(':', '')}.wav"

            if AdikWaveHandler.save_wav(filename, sound_to_save):
                print(f"Player: Enregistrement sauvegardé dans '{filename}'.")
                return True
            else:
                print(f"Player: Échec de la sauvegarde de l'enregistrement dans '{filename}'.")
                return False
        else:
            print("Player: Aucun enregistrement finalisé ou le buffer est vide. Rien à sauvegarder.")
            print("Astuce: Appuyez sur 'R' pour démarrer l'enregistrement, puis 'R' ou 'Espace' ou 'V' pour le finaliser avant de sauvegarder.")
            return False
            
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
    def set_loop_points(self, start_time_seconds, end_time_seconds):
        """
        Définit les points de début et de fin de la boucle en secondes.
        La conversion en frames est gérée automatiquement.
        Les points sont automatiquement bornés entre 0 et la durée totale du projet.
        """
        with self._lock:
            self._update_total_duration_cache()
            
            
            # Utilisation directe de la valeur en frames mise en cache
            total_duration_frames = self.total_duration_frames_cached

            # Conversion des secondes en frames
            start_frame = int(start_time_seconds * self.sample_rate)
            end_frame = int(end_time_seconds * self.sample_rate)
            
            # Bornage automatique des points de bouclage
            if start_frame < 0:
                start_frame = 0
            
            if end_frame > total_duration_frames:
                end_frame = total_duration_frames

            # Validation des points de bouclage
            if end_frame <= start_frame:
                print("Erreur: Le point de fin de la boucle doit être supérieur au point de début.")
                return False

            # Mettre à jour les propriétés
            self.loop_start_frame = start_frame
            self.loop_end_frame = end_frame
            self.is_looping = True
            
            print(f"Player: Boucle activée de {self.loop_start_frame} à {self.loop_end_frame} frames.")
            return True

    #----------------------------------------

    def toggle_loop(self):
        """Active ou désactive le mode boucle."""
        with self._lock:
            if self.is_looping:
                self.is_looping = False
                print("Player: Boucle désactivée.")
            else:
                # Vérifier si les points de bouclage sont valides avant d'activer la boucle
                self._update_params()
                print(f"loop_start: {self.loop_start_frame}, loop_end: {self.loop_end_frame}")
                if self.loop_end_frame > self.loop_start_frame:
                    self.is_looping = True
                    print("Player: Boucle activée.")
                else:
                    print("Erreur: Les points de bouclage ne sont pas valides. Utilisez set_loop_points d'abord.")

    #----------------------------------------


    # --- Gestion du métronome ---
    def set_bpm(self, bpm):
        """Définit le tempo en BPM et met à jour les frames_per_beat."""
        with self._lock:
            if bpm > 0:
                self.metronome.tempo_bpm = bpm
                self.update_tempo()
            else:
                print("Erreur: Le BPM doit être une valeur positive.")

    #----------------------------------------

    def get_bpm(self):
        """Retourne le tempo actuel en BPM."""
        return self.metronome.tempo_bpm

    #----------------------------------------

    def toggle_click(self):
        """
        Active ou désactive le métronome.
        Initialise la position du métronome et le compteur de battements.
        """
        with self._lock:
            self.metronome.toggle_click(False)
            
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
            if self._recording and indata is not None and indata.size > 0:
                self.recording_buffer = np.append(self.recording_buffer, indata.astype(np.float32).flatten())

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
                    if track.is_armed() and self._recording and self.recording_mode == track.RECORDING_MODE_REPLACE:
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
                if self.is_looping and self.current_playback_frame >= self.loop_end_frame:
                    self.current_playback_frame = self.loop_start_frame
                    self.metronome.playback_frame = self.current_playback_frame
                    for track in self.track_list:
                        track.playback_position = self.current_playback_frame
                    print(f"Player: Boucle terminée, repositionnement à {self.current_playback_frame} frames.")
                
                # Gérer l'arrêt en fin de lecture si le bouclage n'est pas actif
                elif not self.is_looping:
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
                if self.is_looping and self.current_playback_frame >= self.loop_end_frame:
                    self.current_playback_frame = self.loop_start_frame
                    self.metronome.playback_frame = self.current_playback_frame
                    for track in self.track_list:
                        track.playback_position = self.current_playback_frame
                    print(f"Player: Boucle terminée, repositionnement à {self.current_playback_frame} frames.")
                
                # Gérer l'arrêt en fin de lecture si le bouclage n'est pas actif
                elif not self.is_looping:
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
