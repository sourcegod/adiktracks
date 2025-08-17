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

        self.volume = 1.0 # Volume linéaire (0.0 à 1.0)
        self.volume_mix = 0.8 # volume global
        self.left_gain =1.0
        self.right_gain =1.0
        self.pan = 0.0     # Panoramique (-1.0 pour gauche, 0.0 pour centre, 1.0 pour droite)

        self._muted = False
        self._solo = False
        self._armed = False # True si la piste est prête à enregistrer

        print(f"AdikTrack '{self.name}' (ID: {self.id}) créé.")

    #----------------------------------------

    def is_muted(self):
        return self._muted

    #----------------------------------------

    def is_solo(self):
        return self._solo

    #----------------------------------------

    def is_armed(self):
        return self._armed

    #----------------------------------------

    def _update_duration(self):
        """
        Met à jour la longueur en frames et en secondes de la piste
        en fonction de la taille de ses données audio.
        Cette fonction est essentielle pour les opérations d'édition.
        """
        if self.audio_sound is not None:
            self.length_frames = self.audio_sound.length_frames
            self.length_seconds = self.audio_sound.length_seconds
        else:
            self.length_frames = 0
            self.length_seconds = 0.0

    #----------------------------------------


    def set_audio_sound(self, sound: AdikSound, offset_frames: int = 0):
        """
        Assigne un objet AdikSound à la piste.
        Si le nombre de canaux du son ne correspond pas à la piste, il est converti.
        """
        # Conversion des canaux si nécessaire
        if sound.num_channels != self.num_channels:
            print(f"Conversion des canaux du son '{sound.name}' de {sound.num_channels} vers {self.num_channels} pour la piste '{self.name}'.")
            
            # Utilisation de la fonction de conversion statique de AdikSound
            converted_data = AdikSound.convert_channels(
                sound.audio_data,
                sound.num_channels,
                self.num_channels,
                sound.length_frames
            )
            
            # Créer un nouvel objet AdikSound avec les données converties
            converted_sound = AdikSound(
                name=f"{sound.name}_converted",
                audio_data=converted_data,
                sample_rate=sound.sample_rate,
                num_channels=self.num_channels
            )
            self.audio_sound = converted_sound
        else:
            self.audio_sound = sound
            
        self.offset_frames = offset_frames
        print(f"Son '{self.audio_sound.name}' assigné à la piste '{self.name}' avec un offset de {self.offset_frames} frames.")

    #----------------------------------------

    def get_audio_data(self):
        if self.audio_sound is not None:
            return self.audio_sound.audio_data

        return

    #----------------------------------------


    def get_audio_block(self, num_frames_to_generate):
        """
        Génère un bloc audio pour la lecture de cette piste, en tenant compte de l'offset.
        Retourne un tableau NumPy de float32 (frames * num_channels).
        Met à jour la position de lecture de la piste.
        """
        output_block = AdikSound.new_audio_data(num_frames_to_generate * self.num_channels)

        if self._muted or self.audio_sound is None or self.audio_sound.length_frames == 0:
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
            
            # processed_sound_part = self._convert_channels(sound_part_raw, self.audio_sound.num_channels, self.num_channels, frames_to_read)
            # Appel à AdikSound.convert_channels
            processed_sound_part = AdikSound.convert_channels(sound_part_raw, self.audio_sound.num_channels, self.num_channels, frames_to_read)


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

            # processed_data = self._convert_channels(data_raw, self.audio_sound.num_channels, self.num_channels, num_frames_to_generate)
            # Appel à AdikSound.convert_channels
            processed_data = AdikSound.convert_channels(data_raw, self.audio_sound.num_channels, self.num_channels, num_frames_to_generate)

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
   
    def arrange_take(self, new_take_audio_data: np.ndarray, take_start_frame: int, take_end_frame: int, recording_mode: int, new_take_channels: int):
        """
        Arrange une nouvelle prise sur le son existant de la piste.
        Ajout du paramètre `new_take_channels` pour la conversion correcte.
        """
        if self.audio_sound is None:
            # Convertir la prise au nombre de canaux de la piste
            if new_take_channels != self.num_channels:
                take_length = len(new_take_audio_data) // new_take_channels
                new_take_audio_data = AdikSound.convert_channels(new_take_audio_data, new_take_channels, self.num_channels, take_length)

            self.set_audio_sound(AdikSound(
                name=f"{self.name}_take",
                audio_data=new_take_audio_data,
                sample_rate=self.sample_rate,
                num_channels=self.num_channels
            ), offset_frames=take_start_frame)
            print(f"Piste '{self.name}': Nouvelle prise ajoutée à une piste vide à l'offset {take_start_frame}.")
            return

        old_sound_data = self.audio_sound.audio_data
        old_sound_length = self.audio_sound.length_frames
        old_sound_end = self.offset_frames + old_sound_length
        
        take_length = len(new_take_audio_data) // new_take_channels
        
        new_total_length = max(old_sound_end, take_end_frame) - min(self.offset_frames, take_start_frame)
        new_buffer = AdikSound.new_audio_data(new_total_length * self.num_channels)

        old_sound_start = self.offset_frames - min(self.offset_frames, take_start_frame)
        take_start = take_start_frame - min(self.offset_frames, take_start_frame)

        # 1. Copier le début de l'ancien son
        frames_before_take = min(old_sound_length, take_start_frame - self.offset_frames)
        if frames_before_take > 0:
            segment_start_old = 0
            segment_end_old = int(frames_before_take * self.audio_sound.num_channels)
            old_data_before = AdikSound.convert_channels(old_sound_data[segment_start_old:segment_end_old], self.audio_sound.num_channels, self.num_channels, frames_before_take)
            dest_start_idx = int(old_sound_start * self.num_channels)
            dest_end_idx = dest_start_idx + old_data_before.size
            new_buffer[dest_start_idx:dest_end_idx] = old_data_before
            print(f"Copie ancien son (début): {frames_before_take} frames.")
        
        # 2. Gérer la zone de chevauchement et insérer la nouvelle prise
        overlap_start = max(take_start_frame, self.offset_frames)
        overlap_end = min(take_end_frame, old_sound_end)
        
        # Convertir la prise aux bons canaux pour l'opération
        processed_new_take = AdikSound.convert_channels(new_take_audio_data, new_take_channels, self.num_channels, take_length)

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
                
                old_overlap_start_in_sound = overlap_start - self.offset_frames
                old_overlap_data = old_sound_data[int(old_overlap_start_in_sound * self.audio_sound.num_channels) : int((old_overlap_start_in_sound + overlap_length) * self.audio_sound.num_channels)].copy()
                old_overlap_data = AdikSound.convert_channels(old_overlap_data, self.audio_sound.num_channels, self.num_channels, overlap_length)
                
                new_overlap_start_in_take = overlap_start - take_start_frame
                new_overlap_data = processed_new_take[int(new_overlap_start_in_take * self.num_channels) : int((new_overlap_start_in_take + overlap_length) * self.num_channels)].copy()
                
                mixed_overlap = AdikSound.merge_audio_data(old_overlap_data, new_overlap_data)
                
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
                old_data_after = AdikSound.convert_channels(old_sound_data[int(segment_start_old * self.audio_sound.num_channels):int(segment_end_old * self.audio_sound.num_channels)], self.audio_sound.num_channels, self.num_channels, frames_after_take)
                dest_start_idx = int((take_end_frame - min(self.offset_frames, take_start_frame)) * self.num_channels)
                dest_end_idx = dest_start_idx + old_data_after.size
                new_buffer[dest_start_idx : min(dest_end_idx, new_buffer.size)] = old_data_after[:min(old_data_after.size, new_buffer.size - dest_start_idx)]
                print(f"Copie ancien son (fin): {frames_after_take} frames.")

        self.set_audio_sound(AdikSound(
            name=f"{self.name}_arranged_take",
            audio_data=new_buffer,
            sample_rate=self.sample_rate,
            num_channels=self.num_channels
        ), offset_frames=min(self.offset_frames, take_start_frame))
        print(f"Piste '{self.name}': Take arrangée. Nouvelle longueur: {self.audio_sound.length_frames} frames, nouvel offset: {self.offset_frames}.")

    #----------------------------------------

    def mix_sound_data(self, output_data, num_frames):
        """
        Copie le bloc audio de la piste dans le tampon de sortie tout en appliquant
        le volume et le panoramique. Cette fonction est conçue pour être extensible
        aux effets plus complexes.
        """

        try:
            # Récupérer le bloc audio de la piste
            input_data = self.get_audio_block(num_frames)
            
            # Paramètres de gain
            vol = self.volume * self.volume_mix
            left_gain = self.left_gain
            right_gain = self.right_gain
            
            # Assurer que les buffers ont la même taille avant de mixer
            if input_data.size != output_data.size:
                print(f"Avertissement: Les buffers de mixage ne sont pas de la même taille ({input_data.size} vs {output_data.size}).")
                return

            # Traitement en fonction du nombre de canaux de la piste
            if self.num_channels == 1:
                # Piste MONO
                # Le son mono est réparti sur les deux canaux de sortie
                for i in range(num_frames):
                    # Chaque échantillon est appliqué sur les canaux gauche et droit
                    mono_sample = input_data[i]
                    # La sortie est en stéréo (deux échantillons par frame)
                    output_data[i*2] += mono_sample * vol * left_gain      # Canal gauche
                    output_data[i*2+1] += mono_sample * vol * right_gain    # Canal droit
            elif self.num_channels == 2:
                # Piste STEREO
                # Le son stéréo est appliqué directement sur les canaux de sortie
                for i in range(0, input_data.size, 2):
                    # Appliquer le gain au canal gauche
                    output_data[i] += input_data[i] * vol * left_gain
                    # Appliquer le gain au canal droit
                    output_data[i+1] += input_data[i+1] * vol * right_gain
            else:
                print(f"Erreur: Le nombre de canaux ({self.num_channels}) n'est pas supporté pour le mixage.")
            
        except Exception as e:
            print(f"Erreur dans mix_sound_data pour la piste {self.name}: {e}")

    #----------------------------------------

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
        if self._muted: status.append("M")
        if self._solo: status.append("S")
        if self._armed: status.append("R")
        status_str = f"[{' '.join(status)}]" if status else ""

        sound_info = f"'{self.audio_sound.name}'" if self.audio_sound else "None"
        return (f"AdikTrack(ID={self.id}, Name='{self.name}', Sound={sound_info}, "
                f"Offset={self.offset_frames}, Pos={self.playback_position}, "
                f"Vol={self.volume:.2f}, Pan={self.pan:.2f}, "
                f"Status={status_str})")

    #----------------------------------------
