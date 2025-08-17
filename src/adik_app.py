#!/usr/bin/env python3
"""
    File: adik_app.py
    Bridge Interface between AdikPlayer class and the User Interface class
    Date: Sat, 16/08/2025
    Author: Coolbrother
"""
import os, sys
from adik_sound import AdikSound
from adik_wave_handler import AdikWaveHandler
from adik_player import AdikPlayer

# --- fonctions de déboggage -- 
def beep():
    print("\a")

#----------------------------------------

def debug_msg(msg, bell=False):
    print(msg)
    if bell: beep()

#----------------------------------------


class AdikApp(object):
    """ Application manager for AdikPlayer """
    def __init__(self, ui_app=None):
        self._ui_app = ui_app  if ui_app is not None else None
        self.player = None
        self.mixer = None


    #----------------------------------------
    
    def display_message(self, msg, on_status_bar=False):
        """ Pass message to the User Interface, or display it """
        if self._ui_app is not None:
            self._ui_app.display_message(msg, on_status_bar)
        else:
            print(msg)
    
    #----------------------------------------

    def init_app(self, sample_rate=44100, block_size=256, num_output_channels=2, num_input_channels=1):
        self.player = AdikPlayer(sample_rate, block_size, num_output_channels, num_input_channels)
        self.mixer = self.player.mixer
        self.player._start_engine()
        self.display_message("AdikApp initialisée.")

    #----------------------------------------

    def close_app(self):
        """ Close the Application controller """
        if self.player is not None:
            self.player.stop()
            self.player._stop_engine()

        self.display_message("AdikApp Terminée.")

    #----------------------------------------


    def set_UI_app(self, ui_app):
        """ Attacher une Interface d'Utilisateur à cette classe  controlleur d'Application """
        if ui_app is not None:
            self._ui_app = ui_app
   
    #----------------------------------------


    #----------------------------------------
    # Player Controls (déplacé depuis AdikTUI.key_handler)
    #----------------------------------------

    def toggle_play_pause(self):
        """ Bascule entre lecture et pause. """
        if self.player.is_playing():
            self.player.pause()
            self.display_message("Lecteur en pause.")
        elif self.player.is_recording():
            self.player.stop_recording()
            self.display_message("Enregistrement arrêté (par Espace).")
        else:
            self.player.play()
            self.display_message("Lecteur en lecture.")

    #----------------------------------------

    def toggle_record(self):
        """ Bascule entre le début et l'arrêt de l'enregistrement. """
        if self.player.is_recording():
            self.player.stop_recording()
            self.display_message("Enregistrement arrêté.")
        else:
            self.player.start_recording()
            self.display_message("Enregistrement démarré.")

    #----------------------------------------

    def forward(self):
        """ Avance rapide la position de lecture. """
        self.player.forward()
        self.display_message(f"Avance rapide à {self.player.current_time_seconds:.2f}s.")

    #----------------------------------------

    def backward(self):
        """ Retour rapide la position de lecture. """
        self.player.backward()
        self.display_message(f"Retour rapide à {self.player.current_time_seconds:.2f}s.")

    #----------------------------------------

    def stop_playback(self):
        """ Arrête la lecture. """
        self.player.stop()
        self.display_message("Lecteur arrêté.")

    #----------------------------------------

    def toggle_click(self):
        """ Bascule le métronome. """
        self.player.toggle_click()

    #----------------------------------------

    def toggle_loop(self):
        """ Bascule la boucle de lecture. """
        self.player.toggle_loop()

    #----------------------------------------

    def go_to_start(self):
        """ Va au début du projet. """
        self.player.goto_start()
        self.display_message("Aller au début.")

    #----------------------------------------

    def go_to_end(self):
        """ Va à la fin du projet. """
        self.player.goto_end()
        self.display_message("Aller à la fin.")

    #----------------------------------------
    
    def set_loop_points(self):
        """ Définit les points de début et de fin de la boucle. """
        # Exemple de valeurs, à adapter pour une saisie utilisateur
        self.player.set_loop_points(0, 30)
        self.display_message("Points de boucle définis.")

    #----------------------------------------

    def toggle_recording_mode(self):
        """ Bascule le mode d'enregistrement. """
        self.player.toggle_recording_mode()
        self.display_message("Mode d'enregistrement basculé.")

    #----------------------------------------

    def add_new_track(self):
        """ Ajoute une nouvelle piste. """
        self.player.add_track()
        self.display_message("Nouvelle piste ajoutée.")

    #----------------------------------------
    
    def save_recording(self):
        """ Sauvegarde le dernier enregistrement. """
        if self.player.save_recording():
            self.display_message("Fichier Sauvegardé")
        else:
            self.display_message("Fichier non Sauvegardé")

    #----------------------------------------
     
    def delete_selected_track(self):
        """ Supprime la piste sélectionnée. """
        selected_track = self.player.get_selected_track()
        if selected_track:
            track_name = selected_track.name
            self.player.delete_track(self.player.selected_track_idx)
            self.display_message(f"Piste '{track_name}' supprimée.")
        else:
            self.display_message("Aucune piste sélectionnée à supprimer.")

    #----------------------------------------

    def remove_all_tracks(self):
        """
        Supprime toutes les pistes et nettoie les données associées.
        """
        self.player.remove_all_tracks()
        self.display_message("Toutes les pistes ont été supprimées.")

    #----------------------------------------

    def delete_audio_from_track(self, start_frame=0, end_frame=-1):
        """ Supprime les données audio de la piste sélectionnée. """
        selected_track_idx = self.player.selected_track_idx
        if selected_track_idx != -1:
            if end_frame == -1:
                end_frame = self.player.get_selected_track().get_audio_sound().length_frames
            self.player.delete_audio_from_track(selected_track_idx, start_frame, end_frame)
            self.display_message(f"Audio supprimé de la piste '{self.player.get_selected_track().name}'.")
        else:
            self.display_message("Aucune piste sélectionnée pour supprimer l'audio.")

    #----------------------------------------

    def erase_audio_from_track(self, start_frame=0, end_frame=-1):
        """ Efface les données audio (remplace par du silence) de la piste sélectionnée. """
        selected_track_idx = self.player.selected_track_idx
        if selected_track_idx != -1:
            if end_frame == -1:
                end_frame = self.player.get_selected_track().get_audio_sound().length_frames
                
            self.player.erase_audio_from_track(selected_track_idx, start_frame, end_frame)
            self.display_message(f"Audio effacé (silence) de la piste '{self.player.get_selected_track().name}'.")
        else:
            self.display_message("Aucune piste sélectionnée pour effacer l'audio.")

    #----------------------------------------

 
    #----------------------------------------
    # Track Controls (déplacé depuis AdikTUI.key_handler)
    #----------------------------------------

    def toggle_arm_track(self):
        """ Arme/désarme la piste sélectionnée pour l'enregistrement. """
        selected_track = self.player.get_selected_track()
        if selected_track:
            selected_track._armed = not selected_track._armed
            self.display_message(f"Piste '{selected_track.name}' Armée: {selected_track._armed}")
        else:
            self.display_message("Aucune piste sélectionnée.")

    #----------------------------------------
 
    def toggle_solo_track(self):
        """ Active/désactive le mode solo pour la piste sélectionnée. """
        selected_track = self.player.get_selected_track()
        if selected_track:
            selected_track._solo = not selected_track._solo
            if selected_track._solo:
                for track in self.player.track_list:
                    if track != selected_track and track._solo:
                        track._solo = False
            self.display_message(f"Piste '{selected_track.name}' Solo: {selected_track._solo}")
        else:
            self.display_message("Aucune piste sélectionnée.")

    #----------------------------------------
     
    def toggle_mute_track(self):
        """ Mute/dé-mute la piste sélectionnée. """
        selected_track = self.player.get_selected_track()
        if selected_track:
            selected_track._muted = not selected_track._muted
            self.display_message(f"Piste '{selected_track.name}' Muette: {selected_track._muted}")
        else:
            self.display_message("Aucune piste sélectionnée.")

    #----------------------------------------
 
    def increase_volume(self):
        """ Augmente le volume de la piste sélectionnée. """
        selected_track = self.player.get_selected_track()
        if selected_track:
            selected_track.volume = min(1.0, selected_track.volume + 0.1)
            self.display_message(f"Piste '{selected_track.name}' Volume: {selected_track.volume:.1f}")
        else:
            self.display_message("Aucune piste sélectionnée.")

    #----------------------------------------
 
    def decrease_volume(self):
        """ Diminue le volume de la piste sélectionnée. """
        selected_track = self.player.get_selected_track()
        if selected_track:
            selected_track.volume = max(0.0, selected_track.volume - 0.1)
            self.display_message(f"Piste '{selected_track.name}' Volume: {selected_track.volume:.1f}")
        else:
            self.display_message("Aucune piste sélectionnée.")

    #----------------------------------------
 
    def pan_left(self):
        """ Panoramique vers la gauche pour la piste sélectionnée. """
        selected_track = self.player.get_selected_track()
        if selected_track:
            selected_track.pan = max(-1.0, selected_track.pan - 0.1)
            self.display_message(f"Piste '{selected_track.name}' Panoramique: {selected_track.pan:.1f}")
        else:
            self.display_message("Aucune piste sélectionnée.")

    #----------------------------------------
 
    def pan_right(self):
        """ Panoramique vers la droite pour la piste sélectionnée. """
        selected_track = self.player.get_selected_track()
        if selected_track:
            selected_track.pan = min(1.0, selected_track.pan + 0.1)
            self.display_message(f"Piste '{selected_track.name}' Panoramique: {selected_track.pan:.1f}")
        else:
            self.display_message("Aucune piste sélectionnée.")

    #----------------------------------------
 
    def select_previous_track(self):
        """ Sélectionne la piste précédente. """
        if self.player.selected_track_idx > 0:
            self.player.select_track(self.player.selected_track_idx - 1)
            self.display_message(f"Piste sélectionnée: {self.player.get_selected_track().name}")
        else:
            beep()
            self.display_message("Déjà à la première piste.")

    #----------------------------------------
 
    def select_next_track(self):
        """ Sélectionne la piste suivante. """
        if self.player.selected_track_idx < len(self.player.track_list) - 1:
            self.player.select_track(self.player.selected_track_idx + 1)
            self.display_message(f"Piste sélectionnée: {self.player.get_selected_track().name}")
        else:
            self.display_message("Déjà à la dernière piste.")
            beep()

    #----------------------------------------

    def load_demo(self):
        """ Charger une nouvelle démonstration """
        sample_rate = 44100
        block_size = 1024
        num_output_channels = 2
        num_input_channels = 1

        # Créer quelques pistes et charger des sons
        self.remove_all_tracks()
        player = self.player
        track1 = player.add_track("Drums")
        track2 = player.add_track("Basse")
        track3 = player.add_track("Synthé")
        track4 = player.add_track("Bruit Blanc") # Nouvelle piste

        # --- Utilisation des nouvelles fonctions de génération ---

        # Onde sinusoïdale pour la piste 1
        sine_sound = AdikSound.sine_wave(freq=440, dur=3, amp=0.2, sample_rate=sample_rate, num_channels=num_output_channels)
        track1.set_audio_sound(sine_sound)
        self.display_message(f"Piste 'Batterie' chargée avec une onde sinus de {sine_sound.name}", on_status_bar=True)

        # Onde carrée pour la piste 2 (synthé)
        square_sound = AdikSound.square_wave(freq=220, dur=2, amp=0.1, sample_rate=sample_rate, num_channels=1, duty_cycle=0.6)
        track2.set_audio_sound(square_sound)
        self.display_message(f"Piste 'Synthé' chargée avec une onde carrée de {square_sound.name}", on_status_bar=True)

        # Bruit blanc pour la nouvelle piste 4
        noise_sound = AdikSound.white_noise(dur=5, amp=0.1, sample_rate=sample_rate, num_channels=1)
        track3.set_audio_sound(noise_sound)
        self.display_message(f"Piste 'Bruit Blanc' chargée avec du {noise_sound.name}", on_status_bar=True)
        file_name1 = "/home/com/audiotest/rhodes.wav" 
        if not os.path.exists(file_name1):
            print(f"Erreur: le fichier ({file_name1}, n'existe pas")
            return
        loaded_sound = AdikWaveHandler.load_wav(file_name1)
        if loaded_sound:
            track4.set_audio_sound(loaded_sound)
            track4.volume = 0.2
        else:
            print(f"Erreur: Impossible de charger '{file_name1}' pour les pistes.")
            return # Quitter si le son ne peut pas être chargé

    #----------------------------------------

 
#========================================

if __name__ == "__main__":
    # For testing
    app = AdikApp()
    app.init_app()

    input("It's OK...")
    
#----------------------------------------
