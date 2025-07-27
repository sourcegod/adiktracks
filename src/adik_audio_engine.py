# adik_audio_engine.py
import sounddevice as sd
import numpy as np
import threading
import time

from adik_mixer import AdikMixer
from adik_sound import AdikSound

class AdikAudioEngine:
    def __init__(self, sample_rate=44100, block_size=1024, num_channels=2):
        self.sample_rate = sample_rate
        self.block_size = block_size # Nombre de frames par bloc audio (taille du buffer)
        self.num_channels = num_channels
        self.mixer = AdikMixer(sample_rate, num_channels)
        self.stream = None
        self._current_playback_position = 0 # Position de lecture globale en frames
        self._sound_to_play = None # Le AdikSound que nous allons jouer pour ce test

        self._lock = threading.Lock() # Verrou pour protéger les accès concurrents aux variables d'état

        print(f"AdikAudioEngine initialisé (SR: {self.sample_rate}, Block Size: {self.block_size})")

    def set_sound_to_play(self, adik_sound):
        """Définit le son à jouer pour le test."""
        with self._lock:
            self._sound_to_play = adik_sound
            self._current_playback_position = 0 # Réinitialise la position de lecture

    def _audio_callback(self, outdata, frames, time, status):
        """
        Le callback audio principal appelé par sounddevice.
        """
        if status:
            print(f"Status du callback audio: {status}", flush=True)

        # Assurez-vous d'accéder aux variables partagées de manière thread-safe
        with self._lock:
            if self._sound_to_play is None or self._sound_to_play.audio_data.size == 0:
                # Si pas de son ou son vide, remplir avec des zéros
                outdata.fill(0.0)
                return

            # Calculer la position de début et de fin pour ce bloc
            start_frame = self._current_playback_position
            end_frame = start_frame + frames

            # Assurez-vous que nous ne lisons pas au-delà des données disponibles
            # Note: sounddevice outdata est (frames, num_channels)
            # Notre audio_data est 1D (interleaved).
            # Nous devons convertir la position en samples (non frames)
            start_sample = start_frame * self._sound_to_play.num_channels
            end_sample = end_frame * self._sound_to_play.num_channels
            
            # Gérer la fin du son
            # Si nous atteignons la fin du son, boucler ou arrêter (pour ce test, nous allons boucler)
            if end_sample >= len(self._sound_to_play.audio_data):
                # Calculer les samples restants dans le son
                remaining_samples = len(self._sound_to_play.audio_data) - start_sample
                
                # Copier les samples restants
                current_block_data = self._sound_to_play.audio_data[start_sample : start_sample + remaining_samples]
                
                # Calculer les samples manquants pour remplir le buffer de sortie
                missing_samples = frames * self._sound_to_play.num_channels - len(current_block_data)

                # Si nous devons boucler
                # Pour ce test, nous bouclons simplement au début
                self._current_playback_position = 0 
                # On pourrait ajouter une logique de padding avec des zéros si on ne voulait pas boucler immédiatement
                # ou si le son était plus court que le buffer.
                
                # Padder le reste du buffer avec des zéros ou des données du début du son
                # Pour un simple test de boucle, on peut soit padder avec des zéros le reste du buffer,
                # soit prendre les premiers samples du son si le son est plus court que le buffer.
                # Ici, on remplit le reste avec des zéros si le son s'est terminé
                
                # Pour le test, simplifions en disant que si on a dépassé la fin, on ne joue plus rien pour ce bloc,
                # et la prochaine fois on recommencera au début.
                # Ou si on veut boucler proprement:
                # outdata.fill(0.0) # Reset outdata
                # outdata[:remaining_frames, :] = current_block_data.reshape(-1, self._sound_to_play.num_channels)
                # self._current_playback_position = 0 # Loop back
                # return

                # Repositionnement et gestion du buffer de sortie
                # Pour ce test simple, si la fin est atteinte, on remplit juste le reste avec des zéros
                # ou on s'assure que le son ne dépasse pas le buffer de sortie.
                # Une façon simple de boucler :
                # Calculer les samples pour le début du son pour compléter le buffer
                samples_from_start = missing_samples
                current_block_data = np.concatenate((current_block_data, self._sound_to_play.audio_data[:samples_from_start]))
                
            else:
                current_block_data = self._sound_to_play.audio_data[start_sample:end_sample]

            # Remodeler les données en (frames, channels) pour sounddevice
            # Assurez-vous que le nombre de samples correspond au nombre de frames * num_channels
            if len(current_block_data) == frames * self._sound_to_play.num_channels:
                current_block_data_reshaped = current_block_data.reshape((frames, self._sound_to_play.num_channels))
                outdata[:] = current_block_data_reshaped
            else:
                # Si la taille ne correspond pas, remplir avec des zéros ou gérer l'erreur
                outdata.fill(0.0)
                # print("Avertissement: Taille de bloc audio inattendue.")


            # Mettre à jour la position de lecture pour le prochain bloc
            self._current_playback_position += frames

    def start_stream(self):
        if self.stream:
            self.stop_stream()
            
        try:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                blocksize=self.block_size,
                channels=self.num_channels,
                dtype='float32',
                callback=self._audio_callback
            )
            self.stream.start()
            print("Stream audio démarré.")
        except Exception as e:
            print(f"Erreur lors du démarrage du stream audio: {e}")
            self.stream = None

    def stop_stream(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            print("Stream audio arrêté.")


