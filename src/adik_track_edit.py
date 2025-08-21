#!/usr/bin/env python3
# adik_track_edit.py
"""
    File: adik_track_edit.py
    Manage Track Edit functions
    Date: Thu, 21/08/2025
    Author: Coolbrother

"""

import numpy as np
import time
from adik_sound import AdikSound
from adik_wave_handler import AdikWaveHandler

class AdikTrackEdit:
    """
    Cette classe gère les fonctions d'édition liées aux pistes.
    Elle est conçue pour être utilisée par AdikPlayer pour garder le code organisé.
    """
    def __init__(self, player):
        self.player = player # Référence à l'instance de AdikPlayer

    #----------------------------------------

    def remove_all_tracks(self):
        """
        Supprime toutes les pistes et nettoie les données associées.
        """
        self.player.stop()  # Arrêter la lecture avant de supprimer les pistes
        for track in self.player.track_list:
            # Nettoyer les ressources de chaque piste si nécessaire
            if hasattr(track, 'audio_sound'):
                del track.audio_sound
        self.player.track_list = []
        self.player.selected_track_idx = -1
        # Mettre à jour la durée totale et d'autres paramètres
        self.player._update_params()

    #----------------------------------------

    def delete_audio_from_track(self, track_index: int, start_frame: int, end_frame: int):
        """
        Supprime complètement les données audio d'une piste entre les positions
        start_frame et end_frame. La longueur de la piste est réduite.
        """
        if 0 <= track_index < len(self.player.track_list):
            track = self.player.track_list[track_index]
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
                new_audio_data = AdikSound.concat_audio_data(part_before, part_after)

                # Mettre à jour les données audio de la piste
                track.set_audio_sound(AdikSound(
                    name=f"{track.audio_sound.name}_deleted",
                    audio_data=new_audio_data,
                    sample_rate=track.sample_rate,
                    num_channels=track.num_channels
                ))
                
                # Mettre à jour les paramètres du player (durée, etc.)
                self.player._update_params()
                
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
        if 0 <= track_index < len(self.player.track_list):
            track = self.player.track_list[track_index]
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
                # Créer une copie modifiable du tableau pour éviter les problèmes de vue
                audio_data_copy = audio_data.copy()
                
                # Remplir la section avec des zéros pour créer du silence
                audio_data_copy[start_sample:end_sample] = 0.0
                
                track.set_audio_sound(AdikSound(
                    name=f"{track.audio_sound.name}_erased",
                    audio_data=audio_data_copy,
                    sample_rate=track.sample_rate,
                    num_channels=track.num_channels
                ))
                
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
        return any(track.is_solo() for track in self.player.track_list)

    #----------------------------------------

    def bounce_to_track(self, start_frame=0, end_frame=-1):
        """
        Mixe les pistes sélectionnées ou toutes les pistes vers une nouvelle piste.
        """
        # Déterminer la durée totale du mixage
        if end_frame == -1:
            end_frame = self.player.total_duration_frames_cached
    
        # S'assurer que les trames sont dans les limites
        start_frame = max(0, start_frame)
        end_frame = min(end_frame, self.player.total_duration_frames_cached)
    
        if start_frame >= end_frame:
            print(f"Avertissement: Les trames de mixage sont invalides.: start_frame: {start_frame}, end_frame: {end_frame}")
            return

        mix_length_frames = end_frame - start_frame
    
        # Créer le tampon de mixage vide
        mix_buffer = AdikSound.new_audio_data(mix_length_frames * self.player.num_output_channels)
    
        # Sauvegarder la position de lecture pour la restaurer plus tard
        saved_playback_position = self.player.current_playback_frame
    
        solo_mode = self.has_solo_track()
    
        # Pour chaque piste, la lire et mixer le son dans le tampon
        for track in self.player.track_list:
            # Ne mixer que les pistes non muettes ou solo
            if track.is_muted() or (solo_mode and not track.is_solo()):
                continue
            
            # Définir la position de lecture de la piste au début de la zone de mixage
            track.set_playback_position(start_frame)
            
            # Lire les données de la piste par blocs et les mixer
            num_frames_read = 0
            while num_frames_read < mix_length_frames:
                frames_to_read = min(self.player.block_size, mix_length_frames - num_frames_read)

                # Créer une "vue" sur la partie du tampon de mixage où le mixage aura lieu
                mix_slice = mix_buffer[num_frames_read * self.player.num_output_channels : (num_frames_read + frames_to_read) * self.player.num_output_channels]
                
                # Mixer le bloc de la piste dans la tranche du tampon de mixage
                track.mix_sound_data(mix_slice, frames_to_read)

                num_frames_read += frames_to_read

        # Créer un nouvel objet AdikSound avec le son mixé
        bounced_sound = AdikSound(
            name="Bounced Audio",
            audio_data=mix_buffer,
            sample_rate=self.player.sample_rate,
            num_channels=self.player.num_output_channels
        )

        # Ajouter une nouvelle piste et lui assigner le son mixé
        new_track = self.player.add_track(name="Piste Mixée")
        new_track.set_audio_sound(bounced_sound, offset_frames=start_frame)

        # Restaurer la position de lecture du player
        self.player.set_position(saved_playback_position)
        
        print(f"Mixage (bounce) terminé. Le son a été ajouté à la piste '{new_track.name}'.")

    #----------------------------------------
    
    def save_track(self, start_frame=0, end_frame=-1, filename=None):
        """
        Sauvegarde le contenu de la piste sélectionnée dans un fichier WAV.
        Si aucun paramètre n'est spécifié, le son entier de la piste est sauvegardé.
        """
        selected_track = self.player.get_selected_track()
        if selected_track is None:
            print("Aucune piste n'est sélectionnée pour la sauvegarde.")
            return False

        audio_sound = selected_track.get_audio_sound()
        if audio_sound is None:
            print(f"La piste '{selected_track.name}' est vide. Rien à sauvegarder.")
            return False

        # Déterminer les trames de début et de fin pour la sauvegarde
        if end_frame == -1:
            end_frame = audio_sound.length_frames
    
        start_frame = max(0, start_frame)
        end_frame = min(end_frame, audio_sound.length_frames)

        if start_frame >= end_frame:
            print("Les trames de début et de fin sont invalides pour la sauvegarde.")
            return False
            
        # Extraire les données audio de la portion sélectionnée
        start_sample = int(start_frame * audio_sound.num_channels)
        end_sample = int(end_frame * audio_sound.num_channels)
    
        data_to_save = audio_sound.audio_data[start_sample:end_sample].copy()

        # Créer un objet AdikSound temporaire pour la sauvegarde
        sound_to_save = AdikSound(
            name=audio_sound.name,
            audio_data=data_to_save,
            sample_rate=audio_sound.sample_rate,
            num_channels=audio_sound.num_channels
        )

        if filename is None:
            # Utilise un nom de fichier par défaut basé sur le nom de la piste
            time_val = f"{time.strftime('%Y_%m_%d_%H%M%S')}"
            filename = f"/tmp/adik_track_{selected_track.name.replace(' ', '_').replace(':', '')}_{time_val}.wav"

        if AdikWaveHandler.save_wav(filename, sound_to_save):
            print(f"Piste '{selected_track.name}' sauvegardée dans '{filename}'.")
            return True
        else:
            print(f"Échec de la sauvegarde de la piste '{selected_track.name}' dans '{filename}'.")
            return False

    #----------------------------------------
#========================================

if __name__ == "__main__":
    app = AdikTrackEdit(None)
    input("It's Ok...")
