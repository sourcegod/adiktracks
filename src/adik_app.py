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
from adik_clip import AdikClip
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

    def set_loop_points(self):
        """ Définit les points de début et de fin de la boucle en utilisant les locateurs. """
        if not self._check_locators_for_range(): return
        
        start_frame = self.player.get_left_locator()
        end_frame = self.player.get_right_locator()
        self.player.set_loop_points(start_frame, end_frame)
        self.display_message(f"Points de boucle définis de la trame {start_frame} à {end_frame}.")

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

    def select_all_time_to_track(self):
        """
        Définit le locateur gauche à 0 et le locateur droit à la fin du projet.
        Cela sélectionne l'intégralité de la timeline.
        """
        self.player.set_left_locator(0)
        self.player.set_right_locator(self.player.total_duration_frames_cached)
        self.display_message("Sélection temporelle complète (locateurs de 0 à fin du projet).")

    #----------------------------------------
        
    def deselect_all_time_to_track(self):
        """
        Définit les deux locateurs à 0, désélectionnant ainsi toute la plage temporelle.
        """
        self.player.set_left_locator(0)
        self.player.set_right_locator(0)
        self.display_message("Sélection temporelle effacée (locateurs à 0).")

    #----------------------------------------

    def delete_audio_from_track(self):
        """ Supprime les données audio de la piste sélectionnée en utilisant les locateurs. """
        selected_track_idx = self.player.selected_track_idx
        if selected_track_idx != -1:
            if not self._check_locators_for_range(): return
            
            start_frame = self.player.get_left_locator()
            end_frame = self.player.get_right_locator()
            self.player.delete_audio_from_track(selected_track_idx, start_frame, end_frame)
            self.display_message(f"Audio supprimé de la piste '{self.player.get_selected_track().name}'.")
        else:
            self.display_message("Aucune piste sélectionnée pour supprimer l'audio.")

    #----------------------------------------

    def erase_audio_from_track(self):
        """ Efface les données audio (remplace par du silence) de la piste sélectionnée en utilisant les locateurs. """
        selected_track_idx = self.player.selected_track_idx
        if selected_track_idx != -1:
            if not self._check_locators_for_range(): return
            
            start_frame = self.player.get_left_locator()
            end_frame = self.player.get_right_locator()
            self.player.erase_audio_from_track(selected_track_idx, start_frame, end_frame)
            self.display_message(f"Audio effacé (silence) de la piste '{self.player.get_selected_track().name}'.")
        else:
            self.display_message("Aucune piste sélectionnée pour effacer l'audio.")

    #----------------------------------------

    def bounce_to_track(self):
        """
        Appelle la fonction de mixage du lecteur avec les locateurs comme paramètres de trame
        et affiche un message à l'utilisateur.
        """
        if len(self.player.track_list) == 0:
            self.display_message("Il n'y a pas de pistes à mixer.")
            return
            
        if not self._check_locators_for_range(): return
            
        start_frame = self.player.get_left_locator()
        end_frame = self.player.get_right_locator()
        
        self.display_message("Mixage des pistes...")
        self.player.bounce_to_track(start_frame=start_frame, end_frame=end_frame)
        self.display_message("Mixage terminé. Une nouvelle piste a été créée.")

    #----------------------------------------

    def save_track(self):
        """ Sauvegarde dans un fichier Wav la piste sélectionnée en utilisant les locateurs. """
        if not self._check_locators_for_range(): return
            
        start_frame = self.player.get_left_locator()
        end_frame = self.player.get_right_locator()
            
        if self.player.save_track(start_frame, end_frame):
            self.display_message("Fichier Sauvegardé")
        else:
            self.display_message("Fichier non Sauvegardé")

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

    def increase_bpm(self):
        """ Augmente le BPM du métronome. """
        self.player.increase_bpm()
        self.display_message(f"BPM : {self.player.get_bpm()}")

    #----------------------------------------
        
    def decrease_bpm(self):
        """ Diminue le BPM du métronome. """
        self.player.decrease_bpm()
        self.display_message(f"BPM : {self.player.get_bpm()}")

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

    #----------------------------------------
    # Contrôles de mesure
    #----------------------------------------

    def get_bar(self):
        """
        Retourne la mesure actuelle en interrogeant le player.
        """
        bar, beat, tick = self.player.frame_to_bar(self.player.get_position())
        self.display_message(f"Position actuelle: Mesure {bar}, Battement {beat}, Tick {tick}")
        return bar, beat, tick

    #----------------------------------------

    def set_bar(self, num_bars):
        """
        Définit la position de lecture du player sur une mesure spécifique.
        Affiche un message de succès ou d'erreur.
        """
        if self.player.set_bar(num_bars):
            self.display_message(f"Déplacé à la mesure {num_bars}.")
        else:
            self.display_message("Erreur: Impossible de se déplacer à cette mesure.")

    #----------------------------------------

    def prev_bar(self):
        """
        Recule la position de lecture du player d'une mesure.
        """
        self.player.prev_bar()
        current_bar, _, _ = self.get_bar()
        self.display_message(f"Reculé à la mesure {current_bar}.")

    #----------------------------------------

    def next_bar(self):
        """
        Avance la position de lecture du player d'une mesure.
        """
        self.player.next_bar()
        current_bar, _, _ = self.get_bar()
        self.display_message(f"Avancé à la mesure {current_bar}.")

    #----------------------------------------

    #----------------------------------------
    # Gestion des Locateurs
    #----------------------------------------

    def _check_locators_for_range(self):
        """
        Vérifie si les locateurs définissent une plage valide (gauche < droite).
        Affiche un message d'erreur et retourne False si la plage est invalide.
        """
        start_frame = self.player.get_left_locator()
        end_frame = self.player.get_right_locator()
        if start_frame >= end_frame:
            self.display_message("Erreur: Les locateurs doivent définir une plage valide.")
            return False
        return True

    #----------------------------------------

    def set_left_locator(self, frames_pos=-1):
        """
        Définit la position du locateur gauche du player.
        Si frames_pos est -1, utilise la position de lecture actuelle.
        Si frames_pos est -2, utilise la durée totale du projet.
        """
        # Fait appel à des fonctions et propriétés pour rester générique
        if frames_pos == -1:
            target_frame = self.player.get_position()
        elif frames_pos == -2:
            target_frame = self.player.total_duration_frames
        else:
            target_frame = frames_pos

        self.player.set_left_locator(target_frame)
        self.display_message(f"Locateur gauche défini à la trame {self.player.get_left_locator()}.")

    #----------------------------------------

    def set_right_locator(self, frames_pos=-1):
        """
        Définit la position du locateur droit du player.
        Si frames_pos est -1, utilise la position de lecture actuelle.
        Si frames_pos est -2, utilise la durée totale du projet.
        """
        # Fait appel à des fonctions et propriétés pour rester générique
        if frames_pos == -1:
            target_frame = self.player.get_position()
        elif frames_pos == -2:
            target_frame = self.player.total_duration_frames
        else:
            target_frame = frames_pos
        
        self.player.set_right_locator(target_frame)
        self.display_message(f"Locateur droit défini à la trame {self.player.get_right_locator()}.")

    #----------------------------------------

    def set_left_locator_from_start(self):
        """
        Définit le locateur gauche à la trame 0.
        """
        self.player.set_left_locator(0)
        self.display_message("Locateur gauche défini au début du projet (trame 0).")

    #----------------------------------------

    def set_right_locator_to_end(self):
        """
        Définit le locateur droit à la fin du projet.
        """
        self.player.set_right_locator(self.player.total_duration_frames_cached)
        self.display_message(f"Locateur droit défini à la fin du projet (trame {self.player.total_duration_frames_cached}).")

    #----------------------------------------

    def goto_left_locator(self):
        """
        Déplace la position de lecture du player au locateur gauche.
        """
        self.player.set_position(self.player.get_left_locator())
        self.display_message(f"Déplacé au locateur gauche (trame {self.player.get_left_locator()}).")

    #----------------------------------------

    def goto_right_locator(self):
        """
        Déplace la position de lecture du player au locateur droit.
        """
        self.player.set_position(self.player.get_right_locator())
        self.display_message(f"Déplacé au locateur droit (trame {self.player.get_right_locator()}).")

    #----------------------------------------


    # --- Functions diverses ---
    def load_demo(self):
        """ Charger une nouvelle démonstration avec des Patterns et des Pistes. """
        sample_rate = 44100
        num_output_channels = 2
        player = self.player

        # 1. Nettoyage initial : Retire tous les patterns et pistes existants
        # On assume une méthode de nettoyage (à ajouter si elle n'existe pas encore)
        if hasattr(player, 'pattern_list'):
            player.pattern_list = []
            player.current_pattern_idx = -1
        else:
            # Si l'architecture est encore ancienne, utilise la méthode existante
            self.remove_all_tracks() 

        # --- Définition des sons de base ---

        # Sons utilisés dans les clips
        sine_sound = AdikSound.sine_wave(freq=440, dur=4, amp=0.2, sample_rate=sample_rate, num_channels=num_output_channels)
        square_sound = AdikSound.square_wave(freq=220, dur=4, amp=0.1, sample_rate=sample_rate, num_channels=num_output_channels, duty_cycle=0.6)
        noise_sound = AdikSound.white_noise(dur=4, amp=0.1, sample_rate=sample_rate, num_channels=num_output_channels)

        # -----------------------------------------------------------
        # I. Création du Pattern A : La section principale du morceau
        # -----------------------------------------------------------
        pattern_a = player.add_pattern("Pattern A - Groove")
        player.select_pattern(0) # S'assurer qu'il est sélectionné
        
        self.display_message(f"Création de '{pattern_a.name}' et ajout des pistes...", on_status_bar=True)

        # Création des pistes
        track_drums_a = pattern_a.add_track("Drums A")
        track_bass_a = pattern_a.add_track("Basse A")
        track_synth_a = pattern_a.add_track("Synthé A")

        # Clips spécifiques au Pattern A
        # Les clips sont des boucles de 4 secondes pour simuler 4 mesures à 120 BPM
        clip_drums_a = AdikClip("Drums Clip (Sine)", sine_sound)
        clip_bass_a = AdikClip("Bass Clip (Square)", square_sound)
        clip_synth_a = AdikClip("Synth Clip (Noise)", noise_sound)

        track_drums_a.add_clip(clip_drums_a)
        track_bass_a.add_clip(clip_bass_a)
        track_synth_a.add_clip(clip_synth_a)

        # -----------------------------------------------------------
        # II. Création du Pattern B : L'Intro/Break plus simple
        # -----------------------------------------------------------
        pattern_b = player.add_pattern("Pattern B - Intro")
        player.select_pattern(1) # Sélectionne le Pattern B pour y ajouter des pistes
        
        self.display_message(f"Création de '{pattern_b.name}' et ajout des pistes...", on_status_bar=True)
        
        # Le Pattern B a des pistes différentes ou des versions différentes
        track_drums_b = pattern_b.add_track("Drums B")
        track_pad_b = pattern_b.add_track("Pad B") # Nouvelle piste

        # Clips spécifiques au Pattern B (seulement la basse et le synthé)
        clip_drums_b = AdikClip("Drums Clip (Square)", square_sound) # On échange les sons
        clip_pad_b = AdikClip("Pad Clip (Sine)", sine_sound)

        track_drums_b.add_clip(clip_drums_b)
        track_pad_b.add_clip(clip_pad_b)
        track_pad_b.volume = 0.5


        # --- Chargement d'un fichier audio et ajout à un Pattern ---

        file_name1 = "/home/com/audiotest/rhodes.wav" 
        if os.path.exists(file_name1):
            loaded_sound = AdikWaveHandler.load_wav(file_name1)
            if loaded_sound:
                loaded_clip = AdikClip("Rhodes Clip", loaded_sound)
                
                # Ajout de la piste de Rhodes au Pattern A (on revient sur Pattern A)
                player.select_pattern(0) 
                track_rhodes_a = player.add_track("Rhodes A")
                track_rhodes_a.add_clip(loaded_clip)
                track_rhodes_a.volume = 0.2
                self.display_message(f"Piste 'Rhodes' chargée dans Pattern A.", on_status_bar=True)
            else:
                print(f"Erreur: Impossible de charger '{file_name1}'.")
        else:
            print(f"Avertissement: Le fichier '{file_name1}' n'existe pas. Piste Rhodes ignorée.")
            
        # -----------------------------------------------------------
        # III. Finalisation
        # -----------------------------------------------------------

        # Revenir au Pattern A pour que ce soit le Pattern actif au lancement de la démo
        player.select_pattern(0) 
        
        # Mise à jour des caches de durée (utilise maintenant les clips des pistes du Pattern A)
        player._update_params()
        
        # Démarrer le moteur audio
        player._start_engine()
        
        self.display_message("Démonstration chargée. Pattern A (Groove) est actif.", on_status_bar=True)

    #----------------------------------------    

#========================================

if __name__ == "__main__":
    # For testing
    app = AdikApp()
    app.init_app()

    input("It's OK...")
    
#----------------------------------------
