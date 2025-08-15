# adik_tui.py
import curses
import time

class AdikTUI(object):
    """ Text User Interface manager object, using curses library """
    def __init__(self, stdscr, player):
        self.stdscr = stdscr
        self.player = player
        
        # Initialisation de l'écran Curses
        self.stdscr.clear()
        self.stdscr.nodelay(False) # Entrée bloquante par défaut (attend une touche)
        curses.curs_set(0) # Masquer le curseur
        
        # Définition des fenêtres
        # info_window pour l'état du lecteur (temps, statut, piste sélectionnée)
        self.info_window = curses.newwin(5, curses.COLS, 0, 0)
        # track_window pour la liste des pistes et les commandes
        self.track_window = curses.newwin(curses.LINES, curses.COLS, 0, 0)
        
        # Historique des messages de statut
        self.status_messages = []
        self.max_status_messages = 3 # Pour afficher les quelques derniers messages

        # Afficher les éléments initiaux de l'interface
        self.display_header()
        self.display_commands()


    #----------------------------------------

    def display_header(self):
        """Affiche les informations d'en-tête fixes."""
        self.info_window.clear()
        self.info_window.addstr(0, 0, "--- AdikTracks Player ---")
        self.info_window.refresh()

    #----------------------------------------

    def display_status(self, msg):
        """
        Affiche un message sur la dernière ligne de l'écran (ou dans la zone de statut)
        et gère un historique des messages.
        """
        ypos = curses.LINES -1
        """
        # Ajouter le nouveau message à l'historique, en ne conservant que les plus récents
        self.status_messages.append(msg)
        if len(self.status_messages) > self.max_status_messages:
            self.status_messages.pop(0) # Supprimer le plus ancien message

        # Définir la ligne de début pour les messages de statut dans la track_window
        # Nous allons placer les messages de statut après les commandes.
        status_start_row_in_track_window = len(self.player.tracks) + 7 # Sous les commandes
        
        # Effacer la zone de statut
        for i in range(self.max_status_messages):
            self.track_window.move(status_start_row_in_track_window + i, 0)
            self.track_window.clrtoeol() # Effacer jusqu'à la fin de la ligne
        """
        
        """
        # Afficher les derniers messages
        for i, status_msg in enumerate(self.status_messages):
            self.track_window.addstr(status_start_row_in_track_window + i, 0, f"STATUS: {status_msg}")
        """
        
        self.track_window.move(ypos, 0)
        self.track_window.clrtoeol() # Effacer jusqu'à la fin de la ligne
# raffraîchir pour que le lecteur d'écran voit le changement
        self.track_window.refresh() 
        # Attendre pour le lecteur d'écran
        time.sleep(0.05)
        self.track_window.addstr(ypos, 0, f"{msg}")
        # self.track_window.move(ypos, 0) 
        # Rafraîchir la fenêtre pour que les changements soient visibles
        self.track_window.refresh()
        
        # Facultatif : déplacer le curseur sur la dernière ligne de statut pour l'accessibilité.
        # En général, il est préférable d'afficher des infos sans déplacer le curseur réel,
        # sauf si une entrée utilisateur est attendue à cet endroit.
        # self.stdscr.move(ypos, 0) 
        # curses.doupdate() 

    def display_track_info(self):
        """
        Affiche l'état actuel du lecteur (temps, statut, piste sélectionnée)
        dans la fenêtre d'information (info_window).
        """
        self.info_window.clear()
        self.info_window.addstr(0, 0, "--- AdikTracks Player ---") # Redessiner l'en-tête
        self.info_window.addstr(1, 0, f"Temps: {self.player.current_time_seconds:.2f}s / {self.player.total_duration_seconds:.2f}s")
        # Mettre à jour la ligne de statut pour inclure un état 'RECORDING' potentiel
        player_status_str = 'LECTURE' if self.player.is_playing() else ('ENREGISTREMENT' if getattr(self.player, '_recording', False) else 'ARRÊTÉ')
        self.info_window.addstr(2, 0, f"Statut: {player_status_str}") 
        
        selected_track = self.player.get_selected_track()
        self.info_window.addstr(3, 0, f"Piste sélectionnée: {selected_track.name if selected_track else 'Aucune'}")
        self.info_window.refresh()

    def display_track_list(self):
        """
        Affiche la liste des pistes et leur état (muet, solo, armé pour l'enregistrement)
        à partir du haut de la fenêtre des pistes (track_window).
        """
        # Effacer uniquement la zone de la liste des pistes, pas toute la fenêtre
        for i in range(1, len(self.player.tracks) + 1):
            self.track_window.move(i, 0)
            self.track_window.clrtoeol() # Effacer jusqu'à la fin de la ligne
        
        self.track_window.addstr(0, 0, "Pistes:") # Redessiner l'étiquette "Pistes:"
        for i, track in enumerate(self.player.tracks):
            prefix = "-> " if i == self.player.selected_track_idx else "   "
            status = []
            if track.is_muted(): status.append("M")
            if track._solo: status.append("S")
            # En supposant que AdikTrack aura un attribut is_armed
            if getattr(track, '_armed', False): status.append("REC") 
            status_str = f"[{' '.join(status)}]" if status else ""

            # Assurez-vous que le nom de la piste s'adapte ou est tronqué
            # On calcule la longueur max disponible pour le nom de la piste
            max_name_len = curses.COLS - len(prefix) - len(status_str) - len(f" (Vol:{track.volume:.1f} Pan:{track.pan:.1f})") - 5
            track_name = track.name
            if len(track_name) > max_name_len and max_name_len > 3: # S'assurer qu'il reste de la place pour "..."
                track_name = track_name[:max_name_len-3] + "..." # Tronquer si trop long

            self.track_window.addstr(i + 1, 0, f"{prefix}{i+1}. {track_name} {status_str} (Vol:{track.volume:.1f} Pan:{track.pan:.1f})")
        
        self.track_window.refresh()

    #----------------------------------------
    
    def display_commands(self):
        """Affiche les raccourcis de commande dans la fenêtre des pistes."""
        start_row = len(self.player.tracks) + 2 # Position après la liste des pistes
        
        # Effacer d'abord la zone des commandes
        for i in range(start_row, start_row + 7): # Effacer 7 lignes pour les commandes et le statut
            self.track_window.move(i, 0)
            self.track_window.clrtoeol()
        
        self.track_window.addstr(start_row, 0, "Commandes:")
        self.track_window.addstr(start_row + 1, 0, "  Espace: Lecture/Pause | V: Arrêt | R: Enregistrement | M: Muet | S: Solo")
        self.track_window.addstr(start_row + 2, 0, "  B: Avance rapide | W: Retour rapide | <: Début | >: Fin")
        self.track_window.addstr(start_row + 3, 0, "  Haut/Bas: Sélectionner Piste | A: Ajouter Piste | D: Supprimer Piste | Q: Quitter")
        self.track_window.addstr(start_row + 4, 0, "  +/-: Volume | [/]: Panoramique | C: Effacer Statut")
        self.track_window.refresh()

    #----------------------------------------


    def update_all(self):
        """Rafraîchit toutes les parties de l'interface utilisateur."""
        self.display_track_info()
        self.display_track_list()
        self.display_commands() # Redessiner les commandes, principalement pour effacer les messages de statut précédents

    #----------------------------------------


    def key_handler(self, key):
        """
        Gère les pressions de touches et appelle les méthodes appropriées du lecteur,
        affichant les messages de statut.
        Retourne True si l'application doit continuer, False si elle doit quitter.
        """
        running = True
        selected_track = self.player.get_selected_track()
        if key == ord('Q'): # Q: Quitter
            running = False
            self.display_status("Fermeture de l'application...")

        elif key == ord(' '): # Espace: Lecture/Pause
            if self.player.is_playing():
                self.player.pause()
                self.display_status("Lecteur en pause.")
            elif self.player.is_recording():
                self.player.stop_recording()
                self.display_status("Enregistrement arrêté (par Espace).")
            else:
                self.player.play()
                self.display_status("Lecteur en lecture.")
        elif key == ord('a'): # a: armé piste
            if selected_track:
                selected_track._armed = not selected_track._armed
                self.display_status(f"Piste '{selected_track.name}' Armée: {selected_track._armed}")
            else:
                self.display_status("Aucune piste sélectionnée.")
        elif key == ord('b') or key == ord('B'): # B: Avance rapide
            self.player.forward()
            self.display_status(f"Avance rapide à {self.player.current_time_seconds:.2f}s.")
        elif key == ord('d') or key == ord('D'): # D: Supprimer Piste
            if selected_track:
                track_name = selected_track.name
                self.player.delete_track(self.player.selected_track_idx)
                self.display_status(f"Piste '{track_name}' supprimée.")
            else:
                self.display_status("Aucune piste sélectionnée à supprimer.")
        elif key == ord('k'): # 'k'
            self.player.toggle_click()
        elif key == ord('l'): # 'l'
            self.player.toggle_loop()

        elif key == ord('r') or key == ord('R'): # R: Enregistrement
            if self.player.is_recording():
                self.player.stop_recording()
                self.display_status("Enregistrement arrêté.")
            else:
                self.player.start_recording()
                self.display_status("Enregistrement démarré.")

        elif key == ord('s'): # s: Solo la piste sélectionnée
            if selected_track:
                selected_track._solo = not selected_track._solo
                if selected_track._solo:
                    for track in self.player.tracks:
                        if track != selected_track and track._solo:
                            track._solo = False
                self.display_status(f"Piste '{selected_track.name}' Solo: {selected_track._solo}")
            else:
                self.display_status("Aucune piste sélectionnée.")
        elif key == ord('v') or key == ord('V'): # V: Arrêt
            self.player.stop()
            self.display_status("Lecteur arrêté.")
        elif key == ord('w') or key == ord('W'): # W: Retour rapide
            self.player.backward()
            self.display_status(f"Retour rapide à {self.player.current_time_seconds:.2f}s.")
        elif key == ord('x'): # x: Mute la piste sélectionnée
            if selected_track:
                selected_track._muted = not selected_track._muted
                self.display_status(f"Piste '{selected_track.name}' Muette: {selected_track._muted}")
            else:
                self.display_status("Aucune piste sélectionnée.")
        elif key == ord('<'): # <: Aller au début
            self.player.goto_start()
            self.display_status("Aller au début.")
        elif key == ord('>'): # >: Aller à la fin
            self.player.goto_end()
            self.display_status("Aller à la fin.")
        elif key == 12: # Ctrl+L
            self.player.set_loop_points(0, 30)
        elif key == 18: # Ctrl+R
            self.player.toggle_recording_mode()

        elif key == 20: # Ctrl+T: Ajouter une piste
            self.player.add_track()
            self.display_status("Nouvelle piste ajoutée.")
        elif key == 23: # Ctrl+W: sauvegarder le fichier enregistré
            if self.player.save_recording():
                self.display_status("Fichier Sauvegardé")
            else:
                self.display_status("Fichier non Sauvegardé")

        elif key == ord('+') or key == ord('='): # +: Augmenter Volume
            if selected_track:
                selected_track.volume = min(1.0, selected_track.volume + 0.1)
                self.display_status(f"Piste '{selected_track.name}' Volume: {selected_track.volume:.1f}")
            else:
                self.display_status("Aucune piste sélectionnée.")
        elif key == ord('-') or key == ord('_'): # -: Diminuer Volume
            if selected_track:
                selected_track.volume = max(0.0, selected_track.volume - 0.1)
                self.display_status(f"Piste '{selected_track.name}' Volume: {selected_track.volume:.1f}")
            else:
                self.display_status("Aucune piste sélectionnée.")
        elif key == ord('[') or key == ord('{'): # [: Panoramique Gauche
            if selected_track:
                selected_track.pan = max(-1.0, selected_track.pan - 0.1)
                self.display_status(f"Piste '{selected_track.name}' Panoramique: {selected_track.pan:.1f}")
            else:
                self.display_status("Aucune piste sélectionnée.")
        elif key == ord(']') or key == ord('}'): # ]: Panoramique Droite
            if selected_track:
                selected_track.pan = min(1.0, selected_track.pan + 0.1)
                self.display_status(f"Piste '{selected_track.name}' Panoramique: {selected_track.pan:.1f}")
            else:
                self.display_status("Aucune piste sélectionnée.")
        elif key == curses.KEY_UP: # Flèche haut: Sélectionner piste précédente
            if self.player.selected_track_idx > 0:
                self.player.select_track(self.player.selected_track_idx - 1)
                self.display_status(f"Piste sélectionnée: {self.player.get_selected_track().name}")
            else:
                curses.beep()
                self.display_status("Déjà à la première piste.")
        elif key == curses.KEY_DOWN: # Flèche bas: Sélectionner piste suivante
            if self.player.selected_track_idx < len(self.player.tracks) - 1:
                self.player.select_track(self.player.selected_track_idx + 1)
                self.display_status(f"Piste sélectionnée: {self.player.get_selected_track().name}")
            else:
                self.display_status("Déjà à la dernière piste.")
                curses.beep()
        else:
            self.display_status(f"Touche '{chr(key)}' ({key}) non reconnue.")
            curses.beep()
        
        return running

    #----------------------------------------

