#!/usr/bin/env python3
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
from adik_tui import AdikTUI

# --- fonctions de déboggage -- 
def beep():
    print("\a")

#----------------------------------------

def debug_msg(msg, bell=False):
    print(msg)
    if bell: beep()

#----------------------------------------

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

def main_curses(stdscr):
    # Paramètres pour le lecteur et le moteur audio
    sample_rate = 44100
    block_size = 1024
    num_output_channels = 2
    num_input_channels = 1

    player = AdikPlayer(sample_rate, block_size, num_output_channels, num_input_channels)

     # Initialiser la classe MainWindow pour l'interface utilisateur Curses
    ui = AdikTUI(stdscr, player)
    ui.display_status("Application démarrée. Appuyez sur '?' pour les commandes.") # Message de statut initial

   
    """
    # Créer quelques pistes et charger des sons
    track1 = player.add_track("Batterie")
    track2 = player.add_track("Basse")
    track3 = player.add_track("Synthé")
    """

    # Créer quelques pistes et charger des sons
    track1 = player.add_track("Drums")
    track2 = player.add_track("Basse")
    track3 = player.add_track("Synthé")
    track4 = player.add_track("Bruit Blanc") # Nouvelle piste

    # --- Utilisation des nouvelles fonctions de génération ---

    # Onde sinusoïdale pour la piste 1
    sine_sound = AdikSound.sine_wave(freq=440, dur=3, amp=0.2, sample_rate=sample_rate, num_channels=num_output_channels)
    track1.set_audio_sound(sine_sound)
    ui.display_status(f"Piste 'Batterie' chargée avec une onde sinus de {sine_sound.name}")

    # Onde carrée pour la piste 2 (synthé)
    square_sound = AdikSound.square_wave(freq=220, dur=2, amp=0.1, sample_rate=sample_rate, num_channels=1, duty_cycle=0.6)
    track2.set_audio_sound(square_sound)
    ui.display_status(f"Piste 'Synthé' chargée avec une onde carrée de {square_sound.name}")

    # Bruit blanc pour la nouvelle piste 4
    noise_sound = AdikSound.white_noise(dur=5, amp=0.1, sample_rate=sample_rate, num_channels=1)
    track3.set_audio_sound(noise_sound)
    ui.display_status(f"Piste 'Bruit Blanc' chargée avec du {noise_sound.name}")
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

    
    """
    sine_wave_file = "/tmp/test_audio.wav" 

    if not os.path.exists(sine_wave_file):
        print(f"Création du fichier de test '{sine_wave_file}' pour le lecteur...")
        sr = 44100
        duration = 5 
        frequency = 440 
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        sine_wave = 0.5 * np.sin(2 * np.pi * frequency * t)
        
        test_sound_to_save = AdikSound(name="Onde Sinusoïdale Lecteur", sample_rate=sr, num_channels=1)
        test_sound_to_save.audio_data = sine_wave.astype(np.float32)
        AdikWaveHandler.save_wav(sine_wave_file, test_sound_to_save)
        print("Fichier de test pour le lecteur créé.")

    loaded_sound = AdikWaveHandler.load_wav(sine_wave_file)
    if loaded_sound:
        track1.set_audio_sound(loaded_sound)
        quieter_sine = loaded_sound.audio_data * 0.3
        synth_sound = AdikSound(name="Synthé Moins Fort", sample_rate=loaded_sound.sample_rate, num_channels=loaded_sound.num_channels)
        synth_sound.audio_data = quieter_sine
        track3.set_audio_sound(synth_sound)
    else:
        print(f"Erreur: Impossible de charger '{sine_wave_file}' pour les pistes.")
        return # Quitter si le son ne peut pas être chargé
        """

    # Démarrer le moteur Audio
    player._start_engine()
    # Boucle principale de l'application
    running = True
    # Ici, on ne met pas de block try/catch... car c'est fait autre part, à l'appel de cette fonction, ce qui permet d'afficher les tracebacks.
    # try: 
    while running:
        # Mettre à jour tous les éléments de l'interface utilisateur
        # ui.update_all()
        
        # Obtenir une entrée bloquante (attend l'appui sur une touche)
        key = stdscr.getch() 
        
        # Gérer la touche pressée via le key_handler de l'interface utilisateur
        running = ui.key_handler(key)

        # Pas besoin de time.sleep ici car getch() est bloquant
        # L'interface utilisateur ne se met à jour que lorsqu'une touche est pressée.
        # Pour des mises à jour continues pendant la lecture, il faudrait un getch() non bloquant
        # et un thread de mise à jour de l'interface utilisateur séparé ou un petit timeout dans getch().
    # End of while loop
    beep()
    player.stop() 
    print("Application terminée.")

    """
    except Exception as e:
        print(f"Error: Une erreur est survenue: {e}")
        # Cette ligne est cruciale
        import traceback
        traceback.print_exc()
        # Vous pouvez également imprimer le traceback ici pour le voir

    finally: 
        player.stop() 
        print("Application terminée.")
    """

#----------------------------------------

if __name__ == "__main__":
    print("--- Démarrage des tests de chargement/sauvegarde WAV ---")
    """
    run_wav_file_tests()
    print("--- Tests WAV terminés ---\n")
    """


    print("--- Démarrage de l'application AdikTracks (interface Curses) ---")
    print("Appuyez sur 'Q' pour quitter l'application Curses.")

    try:
        # curses.wrapper assure une initialisation et un nettoyage corrects du terminal
        curses.wrapper(main_curses) # Lance l'application Curses
    except curses.error as e:
        print(f"\nErreur Curses: {e}")
        print("Il se peut que votre terminal ne supporte pas Curses ou que 'windows-curses' ne soit pas installé sur Windows.")
        print("Exécutez 'pip install windows-curses' si vous êtes sur Windows.")
    except Exception as e:
        print(f"\nApp Error: Une erreur inattendue est survenue: {e}")
        # Cette ligne est cruciale
        import traceback
        traceback.print_exc()
    
    finally:
        sys.exit(0)

#----------------------------------------

