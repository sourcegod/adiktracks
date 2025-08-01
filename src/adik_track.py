# adik_track.py
import numpy as np
from adik_sound import AdikSound # Pour associer un son à la piste

class AdikTrack:
    _next_id = 0 # Pour générer des IDs uniques de piste

    # Définition des modes d'enregistrement
    RECORDING_MODE_REPLACE = 0
    RECORDING_MODE_MIX = 1

    def __init__(self, name=None, sample_rate=44100, num_channels=2):
        self.id = AdikTrack._next_id
        AdikTrack._next_id += 1
         
        self.name = name if name is not None else f"Track {self.id + 1}"
        self.sample_rate = sample_rate
        self.num_channels = num_channels # Les canaux de sortie de la piste (typiquement 2 pour stéréo)

        self.audio_sound = None # Un objet AdikSound chargé dans cette piste
        self.playback_position = 0 # Position de lecture actuelle en FRAMES (non en samples)
        self.offset_frames = 0 # Offset en frames pour le début du son sur la piste

        self.volume = 1.0 # Gain linéaire (0.0 à 1.0)
        self.pan = 0.0     # Panoramique (-1.0 pour gauche, 0.0 pour centre, 1.0 pour droite)

        self.is_muted = False
        self.is_solo = False
        self.is_armed = False # True si la piste est prête à enregistrer

        print(f"AdikTrack '{self.name}' (ID: {self.id}) créé.")

    #----------------------------------------

    def set_audio_sound(self, sound: AdikSound, offset_frames=0):
        """Associe un AdikSound à cette piste."""
        if not isinstance(sound, AdikSound):
            print(f"Erreur: '{sound}' n'est pas un objet AdikSound valide.")
            return False
        self.audio_sound = sound
        self.offset_frames = offset_frames # Stocke l'offset
        # La position de lecture ne doit PAS être réinitialisée ici, elle est gérée par le Player
        # self.playback_position = self.offset_frames
        print(f"Piste '{self.name}': Son '{sound.name}' chargé avec offset de {offset_frames} frames.")

        # Ajuster les canaux de la piste si le son est différent (ex: charger un mono sur piste stéréo)
        # Pour l'instant, nous supposerons que la piste gère la conversion si nécessaire lors de get_audio_block.
        # Mais le num_channels de la piste représente sa sortie finale avant mixage.
        return True

    #----------------------------------------

    def get_audio_block(self, num_frames_to_generate):
        """
        Génère un bloc audio pour la lecture de cette piste, en tenant compte de l'offset.
        Retourne un tableau NumPy de float32 (frames * num_channels).
        Met à jour la position de lecture de la piste.
        """
        output_block = AdikSound.new_audio_data(num_frames_to_generate * self.num_channels)

        if self.is_muted or self.audio_sound is None or self.audio_sound.audio_data.size == 0:
            # Avancer la position globale même si la piste est muette ou vide
            self.playback_position += num_frames_to_generate
            return output_block 

        # Calculer la position de lecture RELATIVE au début du son sur la timeline
        current_frame_sound = self.playback_position 
        
        # Position réelle dans les données brutes du son, en tenant compte de son offset
        start_frame_sound = current_frame_sound - self.offset_frames

        # Si le début de ce bloc est avant l'offset du son sur la piste (silence avant le son)
        if start_frame_sound < 0:
            frames_silence = abs(start_frame_sound)
            
            # Si tout le bloc est avant le son (pur silence)
            if frames_silence >= num_frames_to_generate:
                self.playback_position += num_frames_to_generate
                return output_block

            # Une partie est silence, une partie est son
            silence_samples = AdikSound.new_audio_data(frames_silence * self.num_channels)
            
            # Le reste du bloc doit être lu à partir du début du son (frame 0 du son)
            frames_to_read = num_frames_to_generate - frames_silence
            
            sound_part_raw = self.audio_sound.audio_data[0 : int(frames_to_read * self.audio_sound.num_channels)].copy()
            
            processed_sound_part = self._convert_channels(sound_part_raw, self.audio_sound.num_channels, self.num_channels, frames_to_read)

            # Compléter la partie son si elle est trop courte (fin du son atteinte)
            if processed_sound_part.size < frames_to_read * self.num_channels:
                padding_size = frames_to_read * self.num_channels - processed_sound_part.size
                processed_sound_part = np.pad(processed_sound_part, (0, padding_size), 'constant')

            # Concaténer le silence et le son
            block_content = AdikSound.concat_audio_data(silence_samples, processed_sound_part)
            
            output_block[:] = block_content[:output_block.size]

        else: # Nous sommes dans la section du son ou au-delà de sa fin
            # Calculer les index de samples dans le buffer 1D de AdikSound
            start_sample_idx = int(start_frame_sound * self.audio_sound.num_channels)
            end_sample_idx = int((start_frame_sound + num_frames_to_generate) * self.audio_sound.num_channels)
            
            data_raw = self.audio_sound.audio_data[start_sample_idx : end_sample_idx].copy()

            processed_data = self._convert_channels(data_raw, self.audio_sound.num_channels, self.num_channels, num_frames_to_generate)

            # Compléter avec des zéros si la fin du son est atteinte
            if processed_data.size < num_frames_to_generate * self.num_channels:
                padding_size = num_frames_to_generate * self.num_channels - processed_data.size
                processed_data = np.pad(processed_data, (0, padding_size), 'constant')
            
            output_block[:] = processed_data

        # Appliquer volume et panoramique
        if self.volume != 1.0 or self.pan != 0.0:
            if self.num_channels == 2:
                reshaped_data = output_block.reshape(-1, 2)
                gain_left = (1.0 - self.pan)
                gain_right = (1.0 + self.pan)
                reshaped_data[:, 0] *= (self.volume * gain_left)
                reshaped_data[:, 1] *= (self.volume * gain_right)
                output_block[:] = reshaped_data.flatten()
            else:
                output_block *= self.volume

        self.playback_position += num_frames_to_generate
        
        return output_block

    #----------------------------------------

    '''
    def get_audio_block_old(self, num_frames_to_generate):
        """
        Génère un bloc audio pour la lecture de cette piste, en tenant compte de l'offset.
        Retourne un tableau NumPy de float32 (frames * num_channels).
        Met à jour la position de lecture de la piste.
        """
        output_block = np.zeros(num_frames_to_generate * self.num_channels, dtype=np.float32)

        if self.is_muted or self.audio_sound is None or self.audio_sound.audio_data.size == 0:
            # Avancer la position globale même si la piste est muette ou vide, pour ne pas bloquer le player
            self.playback_position += num_frames_to_generate
            return output_block 

        # Calculer la position de lecture RELATIVE au début du son sur la timeline.
        # Cette position est `global_player_position - track_offset`.
        current_frame_in_sound_timeline = self.playback_position 
        
        # Position réelle dans les données brutes du son, en tenant compte de son offset
        start_frame_in_sound_data = current_frame_in_sound_timeline - self.offset_frames

        # Si le début de ce bloc est avant l'offset du son sur la piste (silence avant le son)
        if start_frame_in_sound_data < 0:
            frames_of_silence_needed = abs(start_frame_in_sound_data)
            
            # Si tout le bloc est avant le son (pur silence)
            if frames_of_silence_needed >= num_frames_to_generate:
                self.playback_position += num_frames_to_generate
                return output_block # Reste silencieux

            # Une partie est silence, une partie est son
            silence_samples = np.zeros(frames_of_silence_needed * self.num_channels, dtype=np.float32)
            
            # Le reste du bloc doit être lu à partir du début du son (frame 0 du son)
            frames_to_read_from_sound = num_frames_to_generate - frames_of_silence_needed
            
            sound_data_part = self.audio_sound.audio_data[0 : int(frames_to_read_from_sound * self.audio_sound.num_channels)].copy()
            
            # Gérer la conversion de canaux pour la partie du son
            processed_sound_part = self._convert_channels(sound_data_part, self.audio_sound.num_channels, self.num_channels, frames_to_read_from_sound)

            # Compléter la partie son si elle est trop courte (fin du son atteinte)
            if processed_sound_part.size < frames_to_read_from_sound * self.num_channels:
                processed_sound_part = np.pad(processed_sound_part, (0, frames_to_read_from_sound * self.num_channels - processed_sound_part.size), 'constant')

            # Concaténer le silence et le son
            block_content = np.concatenate((silence_samples, processed_sound_part))
            
            # Assurez-vous que la taille correspondante est correcte (truncature si excès dû aux calculs)
            output_block[:] = block_content[:output_block.size]

        else: # Nous sommes dans la section du son ou au-delà de sa fin
            # Calculer les index de samples dans le buffer 1D de AdikSound
            start_sample_idx = int(start_frame_in_sound_data * self.audio_sound.num_channels)
            end_sample_idx = int((start_frame_in_sound_data + num_frames_to_generate) * self.audio_sound.num_channels)
            
            # Prendre les données audio disponibles
            data_raw = self.audio_sound.audio_data[start_sample_idx : end_sample_idx].copy()

            # Gérer la conversion de canaux
            processed_data = self._convert_channels(data_raw, self.audio_sound.num_channels, self.num_channels, num_frames_to_generate)

            # Compléter avec des zéros si la fin du son est atteinte
            if processed_data.size < num_frames_to_generate * self.num_channels:
                padding_size = num_frames_to_generate * self.num_channels - processed_data.size
                processed_data = np.pad(processed_data, (0, padding_size), 'constant')
            
            output_block[:] = processed_data

        # Appliquer volume et panoramique
        if self.volume != 1.0 or self.pan != 0.0:
            if self.num_channels == 2: # Seulement si la piste est stéréo
                reshaped_data = output_block.reshape(-1, 2) # (frames, 2)
                
                # Gains pour panoramique
                gain_left = (1.0 - self.pan) 
                gain_right = (1.0 + self.pan) 
                
                reshaped_data[:, 0] *= (self.volume * gain_left) 
                reshaped_data[:, 1] *= (self.volume * gain_right) 
                 
                output_block[:] = reshaped_data.flatten() # Revenir à 1D
            else: # Mono channel (pas de panoramique, juste le volume)
                output_block *= self.volume

        # Mettre à jour la position de lecture de la piste
        self.playback_position += num_frames_to_generate
        
        return output_block

    #----------------------------------------
    '''

    def _convert_channels(self, data, source_channels, target_channels, num_frames):
        """
        Convertit un bloc audio d'un nombre de canaux à un autre.
        `num_frames` est la longueur du bloc audio en frames (non en samples).
        """
        if source_channels == target_channels:
            # S'assurer que le padding est appliqué si data est plus court que prévu
            expected_size = num_frames * target_channels
            if data.size < expected_size:
                return np.pad(data, (0, expected_size - data.size), 'constant')
            return data
        
        if source_channels == 1 and target_channels == 2:
            # Mono vers Stéréo
            processed_data = np.empty(num_frames * 2, dtype=np.float32)
            
            # Assurez-vous d'avoir assez de données mono pour les frames demandées
            data_mono_padded = np.pad(data, (0, num_frames - (data.size // source_channels)), 'constant')
            
            processed_data[0::2] = data_mono_padded # Canal gauche
            processed_data[1::2] = data_mono_padded # Canal droit
            return processed_data
            
        elif source_channels == 2 and target_channels == 1:
            # Stéréo vers Mono (moyenne)
            # Assurez-vous d'avoir assez de données stéréo pour les frames demandées
            data_stereo_padded = np.pad(data, (0, num_frames * 2 - data.size), 'constant')
            return np.mean(data_stereo_padded.reshape(-1, 2), axis=1)
        
        else:
            print(f"Avertissement: Conversion de canaux non gérée: {source_channels} -> {target_channels}.")
            # Fallback: retourner un bloc de zéros ou les données originales (peut causer des erreurs de taille)
            return np.zeros(num_frames * target_channels, dtype=np.float32)

    #----------------------------------------
    def arrange_take(self, new_take_audio_data: np.ndarray, take_start_frame: int, take_end_frame: int, recording_mode: int):
        """
        Arrange une nouvelle prise sur le son existant de la piste, en fonction du mode d'enregistrement.
        ... (commentaires existants) ...
        """
        if self.audio_sound is None:
            self.set_audio_sound(AdikSound(
                name=f"{self.name}_take",
                audio_data=new_take_audio_data,
                sample_rate=self.sample_rate,
                num_channels=self.num_channels
            ), offset_frames=take_start_frame)
            print(f"Piste '{self.name}': Nouvelle prise ajoutée à une piste vide à l'offset {take_start_frame}.")
            return

        old_sound_data = self.audio_sound.audio_data
        old_sound_length = self.audio_sound.get_length_frames()
        old_sound_end = self.offset_frames + old_sound_length
        
        take_length = len(new_take_audio_data) // self.audio_sound.num_channels
        
        new_total_length = max(old_sound_end, take_end_frame) - min(self.offset_frames, take_start_frame)
        new_buffer = AdikSound.new_audio_data(new_total_length * self.num_channels)

        old_sound_start = self.offset_frames - min(self.offset_frames, take_start_frame)
        take_start = take_start_frame - min(self.offset_frames, take_start_frame)

        # 1. Copier le début de l'ancien son
        frames_before_take = min(old_sound_length, take_start_frame - self.offset_frames)
        if frames_before_take > 0:
            segment_start_old = 0
            segment_end_old = int(frames_before_take * self.audio_sound.num_channels)
            old_data_before = self._convert_channels(old_sound_data[segment_start_old:segment_end_old], self.audio_sound.num_channels, self.num_channels, frames_before_take)
            dest_start_idx = int(old_sound_start * self.num_channels)
            dest_end_idx = dest_start_idx + old_data_before.size
            new_buffer[dest_start_idx:dest_end_idx] = old_data_before
            print(f"Copie ancien son (début): {frames_before_take} frames.")
        
        # 2. Gérer la zone de chevauchement et insérer la nouvelle prise
        overlap_start = max(take_start_frame, self.offset_frames)
        overlap_end = min(take_end_frame, old_sound_end)
        
        # Convertir la prise aux bons canaux pour l'opération
        processed_new_take = self._convert_channels(new_take_audio_data, self.audio_sound.num_channels, self.num_channels, take_length)

        if recording_mode == AdikTrack.RECORDING_MODE_REPLACE:
            print("Mode de remplacement activé.")
            dest_start_idx = int(take_start * self.num_channels)
            dest_end_idx = dest_start_idx + processed_new_take.size
            new_buffer[dest_start_idx : min(dest_end_idx, new_buffer.size)] = processed_new_take[:min(processed_new_take.size, new_buffer.size - dest_start_idx)]
        
        elif recording_mode == AdikTrack.RECORDING_MODE_MIX:
            print("Mode de mixage activé.")
            
            # Copier le reste de la prise (après le chevauchement)
            if take_end_frame > overlap_end:
                take_after_overlap_start = overlap_end - take_start_frame
                take_after_overlap_data = processed_new_take[int(take_after_overlap_start * self.num_channels):].copy()
                
                dest_start_idx = int((overlap_end - min(self.offset_frames, take_start_frame)) * self.num_channels)
                new_buffer[dest_start_idx : dest_start_idx + take_after_overlap_data.size] = take_after_overlap_data

            # Gérer le chevauchement s'il existe
            if overlap_end > overlap_start:
                overlap_length = overlap_end - overlap_start
                
                # Partie de l'ancien son qui chevauche
                old_overlap_start_in_sound = overlap_start - self.offset_frames
                old_overlap_data = old_sound_data[int(old_overlap_start_in_sound * self.audio_sound.num_channels) : int((old_overlap_start_in_sound + overlap_length) * self.audio_sound.num_channels)].copy()
                old_overlap_data = self._convert_channels(old_overlap_data, self.audio_sound.num_channels, self.num_channels, overlap_length)
                
                # Partie de la nouvelle prise qui chevauche
                new_overlap_start_in_take = overlap_start - take_start_frame
                new_overlap_data = processed_new_take[int(new_overlap_start_in_take * self.num_channels) : int((new_overlap_start_in_take + overlap_length) * self.num_channels)].copy()
                
                # Mixer les deux buffers de chevauchement
                mixed_overlap = AdikSound.merge_audio_data(old_overlap_data, new_overlap_data)
                
                # Coller le mix dans le nouveau buffer
                dest_start_idx = int((overlap_start - min(self.offset_frames, take_start_frame)) * self.num_channels)
                new_buffer[dest_start_idx : dest_start_idx + mixed_overlap.size] = mixed_overlap
            
            # Copier le début de la prise (avant le chevauchement)
            if overlap_start > take_start_frame:
                take_before_overlap_length = overlap_start - take_start_frame
                take_before_overlap_data = processed_new_take[0 : int(take_before_overlap_length * self.num_channels)].copy()
                
                dest_start_idx = int(take_start * self.num_channels)
                new_buffer[dest_start_idx : dest_start_idx + take_before_overlap_data.size] = take_before_overlap_data

        # 3. Copier la fin de l'ancien son
        if take_end_frame < old_sound_end:
            frames_after_take = old_sound_end - take_end_frame
            if frames_after_take > 0:
                segment_start_old = take_end_frame - self.offset_frames
                segment_end_old = old_sound_length
                old_data_after = self._convert_channels(old_sound_data[int(segment_start_old * self.audio_sound.num_channels):int(segment_end_old * self.audio_sound.num_channels)], self.audio_sound.num_channels, self.num_channels, frames_after_take)
                dest_start_idx = int((take_end_frame - min(self.offset_frames, take_start_frame)) * self.num_channels)
                dest_end_idx = dest_start_idx + old_data_after.size
                new_buffer[dest_start_idx : min(dest_end_idx, new_buffer.size)] = old_data_after[:min(old_data_after.size, new_buffer.size - dest_start_idx)]
                print(f"Copie ancien son (fin): {frames_after_take} frames.")

        # Mettre à jour le AdikSound de la piste avec le nouveau buffer
        self.set_audio_sound(AdikSound(
            name=f"{self.name}_arranged_take",
            audio_data=new_buffer,
            sample_rate=self.sample_rate,
            num_channels=self.num_channels
        ), offset_frames=min(self.offset_frames, take_start_frame))
        print(f"Piste '{self.name}': Take arrangée. Nouvelle longueur: {self.audio_sound.get_length_frames()} frames, nouvel offset: {self.offset_frames}.")

    #----------------------------------------



    '''
    def arrange_take_old1(self, new_take_audio_data: np.ndarray, take_start_frame: int, take_end_frame: int, recording_mode: int):
        """
        Arrange une nouvelle prise sur le son existant de la piste, en fonction du mode d'enregistrement.
        :param new_take_audio_data: Le buffer NumPy de la nouvelle prise.
        :param take_start_frame: La position (en frames) où la prise a commencé.
        :param take_end_frame: La position (en frames) où la prise s'est terminée.
        :param recording_mode: Le mode d'enregistrement (REPLACE ou MIX).
        """
        if self.audio_sound is None:
            # Cas simple : la piste est vide, la prise devient le son de la piste.
            self.set_audio_sound(AdikSound(
                name=f"{self.name}_take",
                audio_data=new_take_audio_data,
                sample_rate=self.sample_rate,
                num_channels=self.num_channels
            ), offset_frames=take_start_frame)
            print(f"Piste '{self.name}': Nouvelle prise ({len(new_take_audio_data)//self.num_channels} frames) ajoutée à une piste vide à l'offset {take_start_frame}.")
            return

        old_sound_data = self.audio_sound.audio_data
        old_sound_length_frames = self.audio_sound.get_length_frames()
        old_sound_end_frame_global = self.offset_frames + old_sound_length_frames
        
        take_length_frames = len(new_take_audio_data) // self.audio_sound.num_channels
        
        new_total_length_frames = max(old_sound_end_frame_global, take_end_frame) - min(self.offset_frames, take_start_frame)
        new_buffer = np.zeros(new_total_length_frames * self.num_channels, dtype=np.float32)

        # Les positions de début de l'ancien son et de la prise par rapport au nouveau buffer
        old_sound_relative_start = self.offset_frames - min(self.offset_frames, take_start_frame)
        take_relative_start = take_start_frame - min(self.offset_frames, take_start_frame)

        # 1. Copier l'ancien son dans le nouveau buffer (avant le point d'insertion de la prise)
        frames_before_take = min(old_sound_length_frames, take_start_frame - self.offset_frames)
        if frames_before_take > 0:
            segment_start_old_sound = 0
            segment_end_old_sound = int(frames_before_take * self.audio_sound.num_channels)
            old_data_before_take = self._convert_channels(old_sound_data[segment_start_old_sound:segment_end_old_sound], self.audio_sound.num_channels, self.num_channels, frames_before_take)
            dest_start_idx = int(old_sound_relative_start * self.num_channels)
            dest_end_idx = dest_start_idx + old_data_before_take.size
            new_buffer[dest_start_idx:dest_end_idx] = old_data_before_take
        
        # 2. Gérer la zone de chevauchement et insérer la nouvelle prise
        # Calculer le chevauchement avec l'ancien son
        overlap_start_frame = max(take_start_frame, self.offset_frames)
        overlap_end_frame = min(take_end_frame, old_sound_end_frame_global)
        
        if recording_mode == AdikTrack.RECORDING_MODE_REPLACE:
            print("Mode de remplacement activé.")
            # Insérer la nouvelle prise directement
            processed_new_take = self._convert_channels(new_take_audio_data, self.audio_sound.num_channels, self.num_channels, take_length_frames)
            dest_start_idx = int(take_relative_start * self.num_channels)
            dest_end_idx = dest_start_idx + processed_new_take.size
            new_buffer[dest_start_idx : min(dest_end_idx, new_buffer.size)] = processed_new_take[:min(processed_new_take.size, new_buffer.size - dest_start_idx)]
        
        elif recording_mode == AdikTrack.RECORDING_MODE_MIX:
            print("Mode de mixage activé.")
            # Récupérer la partie de l'ancien son qui chevauche
            if overlap_end_frame > overlap_start_frame:
                overlap_length_frames = overlap_end_frame - overlap_start_frame
                
                # Partie de l'ancien son qui chevauche
                old_overlap_start_frame_in_sound = overlap_start_frame - self.offset_frames
                old_overlap_data = old_sound_data[int(old_overlap_start_frame_in_sound * self.audio_sound.num_channels) : int((old_overlap_start_frame_in_sound + overlap_length_frames) * self.audio_sound.num_channels)].copy()
                old_overlap_data = self._convert_channels(old_overlap_data, self.audio_sound.num_channels, self.num_channels, overlap_length_frames)
                
                # Partie de la nouvelle prise qui chevauche
                new_overlap_start_frame_in_take = overlap_start_frame - take_start_frame
                new_overlap_data = new_take_audio_data[int(new_overlap_start_frame_in_take * self.audio_sound.num_channels) : int((new_overlap_start_frame_in_take + overlap_length_frames) * self.audio_sound.num_channels)].copy()
                new_overlap_data = self._convert_channels(new_overlap_data, self.audio_sound.num_channels, self.num_channels, overlap_length_frames)

                # Mixer les deux buffers de chevauchement
                mixed_overlap = old_overlap_data + new_overlap_data
                
                # Copier l'ancien son avant l'overlap
                # ... (cette partie est déjà gérée au point 1)
                
                # Coller le mix dans le nouveau buffer
                dest_start_idx = int((overlap_start_frame - min(self.offset_frames, take_start_frame)) * self.num_channels)
                new_buffer[dest_start_idx : dest_start_idx + mixed_overlap.size] = mixed_overlap

                # Copier le reste de la prise (après le chevauchement)
                take_after_overlap_start_frame = overlap_end_frame - take_start_frame
                if take_end_frame > overlap_end_frame:
                    take_after_overlap_data = new_take_audio_data[int(take_after_overlap_start_frame * self.audio_sound.num_channels):].copy()
                    take_after_overlap_data = self._convert_channels(take_after_overlap_data, self.audio_sound.num_channels, self.num_channels, (take_end_frame - overlap_end_frame))
                    dest_start_idx = int((overlap_end_frame - min(self.offset_frames, take_start_frame)) * self.num_channels)
                    new_buffer[dest_start_idx : dest_start_idx + take_after_overlap_data.size] = take_after_overlap_data

            else: # Pas de chevauchement, juste insérer la prise
                processed_new_take = self._convert_channels(new_take_audio_data, self.audio_sound.num_channels, self.num_channels, take_length_frames)
                dest_start_idx = int(take_relative_start * self.num_channels)
                dest_end_idx = dest_start_idx + processed_new_take.size
                new_buffer[dest_start_idx : min(dest_end_idx, new_buffer.size)] = processed_new_take[:min(processed_new_take.size, new_buffer.size - dest_start_idx)]


        # 3. Copier la fin de l'ancien son
        if take_end_frame < old_sound_end_frame_global:
            frames_after_take_in_old_sound = old_sound_end_frame_global - take_end_frame
            if frames_after_take_in_old_sound > 0:
                segment_start_old_sound_frames = take_end_frame - self.offset_frames
                segment_start_old_sound = int(segment_start_old_sound_frames * self.audio_sound.num_channels)
                segment_end_old_sound = int(old_sound_length_frames * self.audio_sound.num_channels)
                old_data_after_take = self._convert_channels(old_sound_data[segment_start_old_sound:segment_end_old_sound], self.audio_sound.num_channels, self.num_channels, frames_after_take_in_old_sound)
                dest_start_idx = int((take_end_frame - min(self.offset_frames, take_start_frame)) * self.num_channels)
                dest_end_idx = dest_start_idx + old_data_after_take.size
                new_buffer[dest_start_idx : min(dest_end_idx, new_buffer.size)] = old_data_after_take[:min(old_data_after_take.size, new_buffer.size - dest_start_idx)]

        # Mettre à jour le AdikSound de la piste avec le nouveau buffer
        self.set_audio_sound(AdikSound(
            name=f"{self.name}_arranged_take",
            audio_data=new_buffer,
            sample_rate=self.sample_rate,
            num_channels=self.num_channels
        ), offset_frames=min(self.offset_frames, take_start_frame))
        print(f"Piste '{self.name}': Take arrangée. Nouvelle longueur: {self.audio_sound.get_length_frames()} frames, nouvel offset: {self.offset_frames}.")

    #----------------------------------------
    '''

    '''
    def arrange_take_old(self, new_take_audio_data: np.ndarray, take_start_frame: int, take_end_frame: int):
        """
        Arrange une nouvelle prise (take) sur le son existant de la piste,
        selon les règles de punch-in/out.
        :param new_take_audio_data: Le buffer NumPy de la nouvelle prise.
        :param take_start_frame: La position (en frames) où la prise a commencé sur la timeline globale.
        :param take_end_frame: La position (en frames) où la prise s'est terminée sur la timeline globale.
        """
        if self.audio_sound is None:
            # Cas simple : la piste est vide, la prise devient le son de la piste.
            # L'offset de la piste est le début de la prise.
            self.set_audio_sound(AdikSound(
                name=f"{self.name}_take",
                audio_data=new_take_audio_data,
                sample_rate=self.sample_rate,
                num_channels=self.num_channels # Assumons que la prise est déjà au bon nombre de canaux de la piste
            ), offset_frames=take_start_frame)
            print(f"Piste '{self.name}': Nouvelle prise ({len(new_take_audio_data)//self.num_channels} frames) ajoutée à une piste vide à l'offset {take_start_frame}.")
            return

        # Ancien son de la piste
        old_sound_data = self.audio_sound.audio_data
        old_sound_length_frames = self.audio_sound.get_length_frames()
        old_sound_end_frame_global = self.offset_frames + old_sound_length_frames
        
        # Dimensions du nouveau take
        take_length_frames = len(new_take_audio_data) // self.audio_sound.num_channels # Important: utiliser num_channels du son de la prise si différent, mais ici on suppose que c'est les mêmes que la piste
                                                                                     # (le AdikPlayer.recording_sound est créé avec num_input_channels qui peut être différent de la piste)
                                                                                     # Il faudra gérer la conversion si la prise n'a pas le même nombre de canaux que le son existant.
        # Pour simplifier, on va supposer que new_take_audio_data est déjà formaté pour les self.num_channels de la piste.
        # Sinon, il faudrait l'adapter ici en utilisant _convert_channels()
        
        # Calculer la longueur finale potentielle de la piste après la prise
        new_total_length_frames = max(old_sound_end_frame_global, take_end_frame) - min(self.offset_frames, take_start_frame)
        
        # Le nouveau buffer qui contiendra le son fusionné
        new_buffer = np.zeros(new_total_length_frames * self.num_channels, dtype=np.float32)

        # Décalage de l'ancien son par rapport au début potentiel du nouveau buffer
        old_sound_relative_start = self.offset_frames - min(self.offset_frames, take_start_frame)
        
        # Décalage de la nouvelle prise par rapport au début potentiel du nouveau buffer
        take_relative_start = take_start_frame - min(self.offset_frames, take_start_frame)

        # 1. Copier le début de l'ancien son (avant le point d'insertion de la prise)
        # S'assurer de ne pas dépasser le début de la prise
        frames_before_take = min(old_sound_length_frames, take_start_frame - self.offset_frames)
        if frames_before_take > 0:
            # Assurez-vous de copier seulement la partie pertinente de l'ancien son
            segment_start_old_sound = 0
            segment_end_old_sound = int(frames_before_take * self.audio_sound.num_channels)
            
            # S'assurer que les canaux sont corrects pour le collage
            old_data_before_take = self._convert_channels(
                old_sound_data[segment_start_old_sound:segment_end_old_sound], 
                self.audio_sound.num_channels, self.num_channels, frames_before_take
            )
            
            dest_start_idx = int(old_sound_relative_start * self.num_channels)
            dest_end_idx = dest_start_idx + old_data_before_take.size
            new_buffer[dest_start_idx:dest_end_idx] = old_data_before_take
            print(f"Copie ancien son (début): {frames_before_take} frames de {dest_start_idx} à {dest_end_idx}.")


        # 2. Copier la nouvelle prise
        # Assurez-vous que new_take_audio_data est déjà au bon nombre de canaux pour la piste
        # Si AdikPlayer._finish_recording s'assure que recording_sound.num_channels est bien self.num_input_channels,
        # et que num_input_channels peut être différent de self.num_channels de la piste,
        # alors il faut convertir new_take_audio_data ici.
        processed_new_take = self._convert_channels(new_take_audio_data, 
                                                    self.audio_sound.num_channels, # Supposons que c'est les canaux du son source
                                                    self.num_channels, 
                                                    take_length_frames)

        dest_start_idx = int(take_relative_start * self.num_channels)
        dest_end_idx = dest_start_idx + processed_new_take.size
        # S'assurer de ne pas écrire au-delà de la taille du nouveau buffer
        new_buffer[dest_start_idx : min(dest_end_idx, new_buffer.size)] = processed_new_take[:min(processed_new_take.size, new_buffer.size - dest_start_idx)]
        print(f"Copie nouvelle prise: {take_length_frames} frames de {dest_start_idx} à {dest_end_idx}.")


        # 3. Copier la fin de l'ancien son (après le point de fin de la prise)
        # Condition: take_end_frame doit être avant la fin de l'ancien son
        if take_end_frame < old_sound_end_frame_global:
            frames_after_take_in_old_sound = old_sound_end_frame_global - take_end_frame
            if frames_after_take_in_old_sound > 0:
                # Partir de la fin de la prise dans l'ancien son
                segment_start_old_sound_frames = take_end_frame - self.offset_frames
                
                segment_start_old_sound = int(segment_start_old_sound_frames * self.audio_sound.num_channels)
                segment_end_old_sound = int(old_sound_length_frames * self.audio_sound.num_channels)

                old_data_after_take = self._convert_channels(
                    old_sound_data[segment_start_old_sound:segment_end_old_sound], 
                    self.audio_sound.num_channels, self.num_channels, frames_after_take_in_old_sound
                )

                dest_start_idx = int((take_relative_start + take_length_frames) * self.num_channels)
                dest_end_idx = dest_start_idx + old_data_after_take.size
                
                # S'assurer de ne pas écrire au-delà de la taille du nouveau buffer
                new_buffer[dest_start_idx : min(dest_end_idx, new_buffer.size)] = old_data_after_take[:min(old_data_after_take.size, new_buffer.size - dest_start_idx)]
                print(f"Copie ancien son (fin): {frames_after_take_in_old_sound} frames de {dest_start_idx} à {dest_end_idx}.")

        # Mettre à jour le AdikSound de la piste avec le nouveau buffer
        self.set_audio_sound(AdikSound(
            name=f"{self.name}_arranged_take",
            audio_data=new_buffer,
            sample_rate=self.sample_rate,
            num_channels=self.num_channels
        ), offset_frames=min(self.offset_frames, take_start_frame)) # Le nouvel offset est le min des deux

        print(f"Piste '{self.name}': Take arrangée. Nouvelle longueur: {self.audio_sound.get_length_frames()} frames, nouvel offset: {self.offset_frames}.")


    #----------------------------------------
    '''
    
    def reset_playback_position(self):
        # Réinitialise à l'offset, pas à 0
        self.playback_position = self.offset_frames

    #----------------------------------------

    def set_playback_position(self, global_player_pos_frames):
        """
        Définit la position de lecture de la piste en fonction de la position globale du player.
        """
        self.playback_position = global_player_pos_frames

    #----------------------------------------


    def __str__(self):
        status = []
        if self.is_muted: status.append("M")
        if self.is_solo: status.append("S")
        if self.is_armed: status.append("R")
        status_str = f"[{' '.join(status)}]" if status else ""

        sound_info = f"'{self.audio_sound.name}'" if self.audio_sound else "None"
        return (f"AdikTrack(ID={self.id}, Name='{self.name}', Sound={sound_info}, "
                f"Offset={self.offset_frames}, Pos={self.playback_position}, "
                f"Vol={self.volume:.2f}, Pan={self.pan:.2f}, "
                f"Status={status_str})")

    #----------------------------------------
