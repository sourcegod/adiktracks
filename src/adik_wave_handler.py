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

    #----------------------------------------

    @staticmethod
    def save_wav(file_path, adik_sound):
        if not isinstance(adik_sound, AdikSound) or adik_sound.get_length_frames() == 0:
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

    #----------------------------------------

    '''
    ### Note: utilisation des fichiers audios uniquement avec le module wave, sans utiliser soundfile
    ### Note: Code gardé ici, juste pour l'archivage
    import wave
    @staticmethod
    def load_wav(file_path: str) -> AdikSound | None:
        """
        Charge un fichier .wav et retourne un objet AdikSound.
        Tente de convertir les canaux si nécessaire.
        """
        if not os.path.exists(file_path):
            print(f"Erreur: Fichier introuvable à {file_path}")
            return None

        try:
            with wave.open(file_path, 'rb') as wf:
                sample_rate = wf.getframerate()
                n_channels = wf.getnchannels()
                n_frames = wf.getnframes()
                audio_data_bytes = wf.readframes(n_frames)

            # Convertir les données en tableau NumPy de float32
            # Les fichiers .wav de 16 bits sont courants.
            audio_data = np.frombuffer(audio_data_bytes, dtype=np.int16).astype(np.float32) / 32768.0

            # Retourner le son avec ses canaux d'origine
            print(f"AdikWaveHandler: Fichier '{os.path.basename(file_path)}' chargé avec {n_channels} canaux.")
            return AdikSound(
                name=os.path.basename(file_path),
                audio_data=audio_data,
                sample_rate=sample_rate,
                num_channels=n_channels
            )

        except Exception as e:
            print(f"Erreur lors du chargement du fichier .wav: {e}")
            return None

    @staticmethod
    def save_wav(file_path: str, sound: AdikSound):
        """
        Sauvegarde un objet AdikSound dans un fichier .wav.
        """
        if sound is None or sound.get_length_frames() == 0:
            print("Erreur: Le son à sauvegarder est vide.")
            return

        try:
            with wave.open(file_path, 'wb') as wf:
                wf.setnchannels(sound.num_channels)
                wf.setsampwidth(2) # 16 bits
                wf.setframerate(sound.sample_rate)

                # Convertir les données float32 en int16 pour la sauvegarde
                audio_data_int16 = (sound.audio_data * 32767).astype(np.int16)
                wf.writeframes(audio_data_int16.tobytes())

            print(f"AdikWaveHandler: Fichier '{os.path.basename(file_path)}' sauvegardé avec succès.")
        except Exception as e:
            print(f"Erreur lors de la sauvegarde du fichier .wav: {e}")
    '''


