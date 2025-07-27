"""
    File: main.py
    Test for adiktracks application
    Date: Sun, 27/07/2025
    Author: Coolbrother
"""
import numpy as np
import os
import time # Ajout de time pour la pause
import sys  # Pour sys.exit()
import threading
import curses # Pour l'interface texte


from adik_sound import AdikSound
from adik_wave_handler import AdikWaveHandler
from adik_mixer import AdikMixer
from adik_audio_engine import AdikAudioEngine
from adik_track import AdikTrack
from adik_player import AdikPlayer



# --- Fonction de test existante ---
def run_wav_file_tests():
    # --- Test de chargement WAV ---
    test_file = "/tmp/test_audio.wav" 

    # Créons un fichier WAV de test si il n'existe pas
    if not os.path.exists(test_file):
        print(f"Création d'un fichier de test '{test_file}'...")
        sr = 44100
        duration = 2 # secondes
        frequency = 440 # Hz (La 440)
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        sine_wave = 0.5 * np.sin(2 * np.pi * frequency * t)
        
        test_sound_to_save = AdikSound(name="Sine Wave", sample_rate=sr, num_channels=1)
        test_sound_to_save.audio_data = sine_wave.astype(np.float32)
        AdikWaveHandler.save_wav(test_file, test_sound_to_save)
        print("Fichier de test créé.")
    
    loaded_sound = AdikWaveHandler.load_wav(test_file)

    if loaded_sound:
        print(f"Détails du son chargé: {loaded_sound}")
        
        # --- Test de sauvegarde WAV ---
        output_file = "/tmp/output_test_audio.wav"
        if AdikWaveHandler.save_wav(output_file, loaded_sound):
            print(f"Son sauvegardé dans {output_file}")
            reloaded_sound = AdikWaveHandler.load_wav(output_file)
            if reloaded_sound:
                print(f"Détails du son rechargé: {reloaded_sound}")
                if np.array_equal(loaded_sound.audio_data, reloaded_sound.audio_data):
                    print("Les données audio chargées et rechargées sont identiques.")
                else:
                    print("Attention: Les données audio chargées et rechargées diffèrent (normalisation ou précision).")
            
    else:
        print("Échec du chargement du son.")

    print("\nTentative de chargement d'un fichier inexistant:")
    AdikWaveHandler.load_wav("non_existent_file.wav")

#----------------------------------------


# --- Fonction principale pour l'interface Curses ---
def main_curses(stdscr):
    # Initialisation de Curses
    stdscr.clear()
    # stdscr.nodelay(False) # Non-blocking input
    # stdscr.timeout(100)  # Attendre 100ms pour l'entrée avant de continuer
    curses.curs_set(0)   # Masquer le curseur

    info_window = curses.newwin(5, curses.COLS, 0, 0)
    track_window = curses.newwin(curses.LINES - 5, curses.COLS, 5, 0)

    # Paramètres audio
    sample_rate = 44100
    block_size = 1024
    num_output_channels = 2

    player = AdikPlayer(sample_rate, block_size, num_output_channels)

    # Créer quelques pistes et charger des sons
    track1 = player.add_track("Drums")
    track2 = player.add_track("Bass")
    track3 = player.add_track("Synth")

    # Charger un fichier WAV de test pour les pistes
    # Utilisez un vrai fichier WAV ou le fichier sine_wave généré
    sine_wave_file = "/tmp/test_audio.wav" # Assurez-vous qu'il existe ou qu'il soit créé par run_wav_file_tests

    # Créer un son de test si non existant
    if not os.path.exists(sine_wave_file):
        print(f"Création d'un fichier de test '{sine_wave_file}' pour le player...")
        sr = 44100
        duration = 5 # secondes
        frequency = 440 # Hz (La 440)
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        sine_wave = 0.5 * np.sin(2 * np.pi * frequency * t)
        
        test_sound_to_save = AdikSound(name="Player Sine Wave", sample_rate=sr, num_channels=1)
        test_sound_to_save.audio_data = sine_wave.astype(np.float32)
        AdikWaveHandler.save_wav(sine_wave_file, test_sound_to_save)
        print("Fichier de test pour player créé.")

    
    loaded_sound = AdikWaveHandler.load_wav(sine_wave_file)
    if loaded_sound:
        track1.set_audio_sound(loaded_sound)
        # Créer une version plus calme pour le synthé
        quieter_sine = loaded_sound.audio_data * 0.3
        synth_sound = AdikSound(name="Quieter Sine", sample_rate=loaded_sound.sample_rate, num_channels=loaded_sound.num_channels)
        synth_sound.audio_data = quieter_sine
        track3.set_audio_sound(synth_sound)
    else:
        info_window.addstr(f"Erreur: Impossible de charger '{sine_wave_file}' pour les pistes.")
        info_window.refresh()
        time.sleep(2)
        return # Quitter si on ne peut pas charger de son

    # Boucle principale de l'application
    running = True
    try: # Ajout d'un bloc try...finally
        while running:
            curses.beep()
            """
            # Mettre à jour la fenêtre d'infos
            info_window.clear()
            info_window.addstr(0, 0, "--- AdikTracks Player ---")
            info_window.addstr(1, 0, f"Temps: {player.current_time_seconds:.2f}s / {player.total_duration_seconds:.2f}s")
            info_window.addstr(2, 0, f"Statut: {'PLAYING' if player.is_playing else 'RECORDING' if player.is_recording else 'STOPPED'}")
            
            selected_track = player.get_selected_track()
            info_window.addstr(3, 0, f"Piste sélectionnée: {selected_track.name if selected_track else 'Aucune'}")
            info_window.refresh()
            """


            # Mettre à jour la fenêtre des pistes
            track_window.clear()
            track_window.addstr(0, 0, "Pistes:")
            for i, track in enumerate(player.tracks):
                prefix = "-> " if i == player.selected_track_idx else "   "
                status = []
                if track.is_muted: status.append("M")
                if track.is_solo: status.append("S")
                if track.is_armed_for_recording: status.append("REC")
                status_str = f"[{' '.join(status)}]" if status else ""

                track_window.addstr(i + 1, 0, f"{prefix}{i+1}. {track.name} {status_str} (Vol:{track.volume:.1f} Pan:{track.pan:.1f})")
            
            """
            # Afficher les raccourcis
            track_window.addstr(len(player.tracks) + 2, 0, "Commandes:")
            track_window.addstr(len(player.tracks) + 3, 0, "  Space: Play/Pause | V: Stop | R: Record | M: Mute | S: Solo")
            track_window.addstr(len(player.tracks) + 4, 0, "  B: Fwd | W: Bwd | <: Start | >: End")
            track_window.addstr(len(player.tracks) + 5, 0, "  Up/Down: Select Track | A: Add Track | D: Del Track | Q: Quit")
            track_window.refresh()
            """


            # Gestion des entrées utilisateur
            c = stdscr.getch() # Non-blocking getch
            if c != -1: # Si une touche a été pressée
                if c == ord(' '): # Space: Play/Pause
                    if player.is_playing:
                        player.pause()
                    else:
                        player.play()
                elif c == ord('v') or c == ord('V'): # V: Stop
                    player.stop()
                elif c == ord('r') or c == ord('R'): # R: Record
                    player.record()
                elif c == ord('b') or c == ord('B'): # B: Forward
                    player.forward()
                elif c == ord('w') or c == ord('W'): # W: Backward
                    player.backward()
                elif c == ord('<'): # <: Goto Start
                    player.goto_start()
                elif c == ord('>'): # >: Goto End
                    player.goto_end()
                elif c == curses.KEY_UP: # Up arrow: Select previous track
                    if player.selected_track_idx > 0:
                        player.select_track(player.selected_track_idx - 1)
                elif c == curses.KEY_DOWN: # Down arrow: Select next track
                    if player.selected_track_idx < len(player.tracks) - 1:
                        player.select_track(player.selected_track_idx + 1)
                elif c == ord('a') or c == ord('A'): # A: Add Track
                    player.add_track()
                elif c == ord('d') or c == ord('D'): # D: Delete Track
                    if player.selected_track_idx != -1:
                        player.delete_track(player.selected_track_idx)
                elif c == ord('m') or c == ord('M'): # M: Mute selected track
                    if selected_track:
                        selected_track.is_muted = not selected_track.is_muted
                        print(f"Piste '{selected_track.name}' muette: {selected_track.is_muted}")
                elif c == ord('s') or c == ord('S'): # S: Solo selected track
                    if selected_track:
                        selected_track.is_solo = not selected_track.is_solo
                        # Logique pour désactiver les autres solos si on active un nouveau solo
                        if selected_track.is_solo:
                            for track in player.tracks:
                                if track != selected_track and track.is_solo:
                                    track.is_solo = False
                        print(f"Piste '{selected_track.name}' solo: {selected_track.is_solo}")
                elif c == ord('q') or c == ord('Q'): # Q: Quit
                    running = False

            time.sleep(0.01) # Petite pause pour ne pas surcharger le CPU

    finally: # Ce bloc garantit que le code ici est toujours exécuté
        player.stop() # Assurez-vous que le stream est arrêté à la sortie
        # Ajout d'un court délai pour permettre au stream de se fermer proprement
        time.sleep(0.1) 
        print("Application terminée.")

#----------------------------------------

if __name__ == "__main__":
    print("--- Démarrage des tests de chargement/sauvegarde WAV ---")
    run_wav_file_tests()
    print("--- Tests WAV terminés ---\n")

    print("--- Démarrage de l'application AdikTracks (interface Curses) ---")
    print("Appuyez sur 'Q' pour quitter l'application Curses.")

    try:
        curses.wrapper(main_curses) # Lance l'application Curses
    except curses.error as e:
        print(f"\nErreur Curses: {e}")
        print("Il se peut que votre terminal ne supporte pas Curses ou que 'windows-curses' ne soit pas installé sur Windows.")
        print("Exécutez 'pip install windows-curses' si vous êtes sur Windows.")
    except Exception as e:
        print(f"\nUne erreur inattendue est survenue: {e}")
    finally:
        sys.exit(0)

#----------------------------------------

