"""
    File: adik_wave_handler.py
    Wave File Handler object
    Date: Sun, 27/07/2025
    Author: Coolbrother
"""
import soundfile as sf
import numpy as np
from adik_sound import AdikSound
import os

class AdikWaveHandler:
    @staticmethod
    def load_wav(file_path):
        if not os.path.exists(file_path):
            print(f"Erreur: Fichier WAV introuvable: {file_path}")
            return None

        try:
            # sf.read retourne les données audio et le sample rate
            # dtype='float32' pour obtenir des données normalisées entre -1.0 et 1.0
            # always_2d=True assure que les données sont toujours un tableau 2D (samples, channels)
            data, samplerate = sf.read(file_path, dtype='float32', always_2d=True)
            
            num_channels = data.shape[1] # Nombre de colonnes est le nombre de canaux

            sound = AdikSound(name=os.path.basename(file_path), 
                              sample_rate=samplerate, 
                              num_channels=num_channels)
            
            # sounddevice attend des données 'flattened' (1D) si on les passe à la callback directement,
            # ou si on les manipule comme un seul buffer linéaire.
            # Convertissons les données 2D (samples, channels) en 1D (interleaved)
            # data.flatten() par défaut est row-major (C-style), ce qui correspond à interleaved si (samples, channels).
            sound.audio_data = data.flatten()

            print(f"Fichier WAV chargé: {sound}")
            return sound
        except Exception as e:
            print(f"Erreur lors du chargement de {file_path}: {e}")
            return None

    @staticmethod
    def save_wav(file_path, adik_sound):
        if not isinstance(adik_sound, AdikSound) or adik_sound.audio_data.size == 0:
            print("Erreur: L'objet AdikSound est invalide ou vide pour la sauvegarde.")
            return False

        try:
            # soundfile s'attend à un tableau 2D pour l'écriture (samples, channels)
            # Nous devons remodeler les données 1D (interleaved) en 2D
            num_frames = len(adik_sound.audio_data) // adik_sound.num_channels
            data_2d = adik_sound.audio_data.reshape((num_frames, adik_sound.num_channels))

            sf.write(file_path, data_2d, adik_sound.sample_rate)
            print(f"Fichier WAV sauvegardé: {file_path}")
            return True
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de {file_path}: {e}")
            return False

