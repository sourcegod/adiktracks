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

from adik_sound import AdikSound
from adik_wave_handler import AdikWaveHandler
from adik_mixer import AdikMixer
from adik_audio_engine import AdikAudioEngine


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


if __name__ == "__main__":
    print("--- Démarrage des tests de chargement/sauvegarde WAV ---")
    run_wav_file_tests()
    print("--- Tests WAV terminés ---\n")

    print("--- Démarrage du test de lecture audio ---")

    # Paramètres audio
    sample_rate = 44100
    block_size = 1024 # Taille du buffer audio
    num_output_channels = 2 # Stéréo

    # Créer un engin audio
    audio_engine = AdikAudioEngine(sample_rate, block_size, num_output_channels)

    # Charger un son (celui créé précédemment ou un autre)
    audio_file_to_play = "/tmp/test_audio.wav"
    sound_to_play = AdikWaveHandler.load_wav(audio_file_to_play)

    if sound_to_play:
        # Définir le son à jouer dans l'engin audio
        audio_engine.set_sound_to_play(sound_to_play)

        print(f"Lecture du son : {sound_to_play.name} pendant 5 secondes (Ctrl+C pour arrêter)...")
        audio_engine.start_stream()

        try:
            # Garder le programme en cours d'exécution pendant la lecture
            # sounddevice lance le callback dans un thread séparé.
            # On boucle pendant un certain temps ou jusqu'à Ctrl+C.
            start_time = time.time()
            while audio_engine.stream.active: # Vérifie si le stream est toujours actif
                time.sleep(0.1) # Attendre un peu pour ne pas surcharger le CPU
                if time.time() - start_time > 4: # Joue pendant 5 secondes
                    print("\nArrêt de la lecture après 5 secondes.")
                    break
        except KeyboardInterrupt:
            print("\nLecture interrompue par l'utilisateur.")
        finally:
            audio_engine.stop_stream()
            print("Test de lecture audio terminé.")
    else:
        print("Impossible de charger le son pour la lecture audio.")

    input("\nAppuyez sur Entrée pour quitter...")
    sys.exit(0)

Expl#----------------------------------------
