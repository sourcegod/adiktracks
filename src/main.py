"""
    File: main.py
    Test for adiktracks application
    Date: Sun, 27/07/2025
    Author: Coolbrother
"""
import numpy as np
import os
from adik_sound import AdikSound
from adik_wave_handler import AdikWaveHandler

def test():
    # --- Test de chargement WAV ---
    test_file = "/tmp/test_audio.wav" # Assurez-vous d'avoir un fichier WAV dans le même répertoire

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
            # Essayons de le recharger pour vérifier
            reloaded_sound = AdikWaveHandler.load_wav(output_file)
            if reloaded_sound:
                print(f"Détails du son rechargé: {reloaded_sound}")
                # Vérification simple de l'égalité (peut être plus robuste)
                if np.array_equal(loaded_sound.audio_data, reloaded_sound.audio_data):
                    print("Les données audio chargées et rechargées sont identiques.")
                else:
                    print("Attention: Les données audio chargées et rechargées diffèrent (normalisation ou précision).")
            
    else:
        print("Échec du chargement du son.")

    # Test avec un fichier inexistant
    print("\nTentative de chargement d'un fichier inexistant:")
    AdikWaveHandler.load_wav("non_existent_file.wav")

#----------------------------------------

if __name__ == "__main__":
    test()
#----------------------------------------
input("...")
