#!/usr/bin/env python3
# adik_loop.py
"""
    File: adik_loop.py
    Loop object management
    Date: Thu, 21/08/2025
    Author: Coolbrother
"""

import threading
class AdikLoop:
    """
    Cette classe gère la logique de bouclage pour le lecteur.
    Elle est conçue pour être utilisée par AdikPlayer.
    """
    def __init__(self, player):
        self.player = player
        self._looping = False
        self._loop_start_frame = 0
        self._loop_end_frame = 0
        self._loop_mode = 0  # 0: mode normal, 1: mode personnalisé
        self._lock = threading.Lock()

    def is_looping(self):
        """
        Retourne l'état de la boucle.
        """
        return self._looping

    #----------------------------------------

    def set_loop_points(self, start_frame, end_frame):
        """
        Définit les points de début et de fin de la boucle en frames.
        Les points sont automatiquement bornés entre 0 et la durée totale du projet.
        """
        with self._lock:
            self.player._update_total_duration_cache()
            
            total_duration_frames = self.player.total_duration_frames_cached

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
            self._loop_start_frame = start_frame
            self._loop_end_frame = end_frame
            self._looping = True
            
            print(f"Boucle activée de {self._loop_start_frame} à {self._loop_end_frame} frames.")
            return True
            

    #----------------------------------------

    def toggle_loop(self):
        """
        Active ou désactive le mode boucle.
        """
        with self._lock:
            if self._looping:
                self._looping = False
                print("Boucle désactivée.")
            else:
                # Vérifier si les points de bouclage sont valides avant d'activer la boucle
                self.player._update_params()
                if self._loop_end_frame > self._loop_start_frame:
                    self._looping = True
                    print("Boucle activée.")
                else:
                    print("Erreur: Les points de bouclage ne sont pas valides. Utilisez set_loop_points d'abord.")

    #----------------------------------------

#========================================

if __name__ == "__main__":
    app = AdikLoop(None)
    input("It's Ok...")

#----------------------------------------
